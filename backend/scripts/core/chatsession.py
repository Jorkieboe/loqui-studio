import logging
from scripts.services.llm_service import api_request

logger = logging.getLogger(__name__)

def get_automatic_transition(node: dict, var_prompt: list, loop_state: dict) -> str:
    node_type = node.get("type", "")
    node_id = node.get("id", "")
    node_class = node.get("node_class", "")

    next_list = node.get("next", [])
    if isinstance(next_list, dict):
        next_list = [next_list]
    elif not isinstance(next_list, list):
        next_list = []

    is_loop = (node_type in ["loop-node", "loop"] or "loop" in node_id or "loop" in node_class)
    is_cycle = (node_type in ["cycle-node", "cycle"] or "cycle" in node_id or "cycle" in node_class)

    if is_loop:
        if loop_state is None:
            loop_state = {"counters": {}, "active_loop_id": None}
        loop_state["active_loop_id"] = node_id
        if node_id not in loop_state["counters"]:
            loop_state["counters"][node_id] = 0
        if next_list:
            item = next_list[0]
            return item.get("target") if isinstance(item, dict) else item
        return None

    if is_cycle:
        if loop_state is None:
            loop_state = {"counters": {}, "active_loop_id": None}

        loop_id = loop_state.get("active_loop_id")
        if not loop_id:
            loop_id = node.get("loop_id") or node.get("target_loop") or node.get("loop")

        if not loop_id:
            for next_item in next_list:
                target = next_item.get("target") if isinstance(next_item, dict) else next_item
                if target:
                    target_node = next((n for n in var_prompt if n.get("id") == target), None)
                    if target_node and (target_node.get("type") in ["loop-node", "loop"] or "loop" in target_node.get("id", "")):
                        loop_id = target
                        break

        loop_node = None
        if loop_id:
            loop_node = next((n for n in var_prompt if n.get("id") == loop_id), None)

        if not loop_node:
            if next_list:
                item = next_list[0]
                return item.get("target") if isinstance(item, dict) else item
            return None

        loop_count = int(loop_node.get("loop_count", 2))
        if loop_id not in loop_state["counters"]:
            loop_state["counters"][loop_id] = 0

        loop_state["counters"][loop_id] += 1

        if loop_state["counters"][loop_id] < loop_count:
            if next_list:
                item = next_list[0]
                return item.get("target") if isinstance(item, dict) else item
            return loop_id
        else:
            loop_state["counters"][loop_id] = 0
            loop_state["active_loop_id"] = None
            loop_next_list = loop_node.get("next", [])
            if isinstance(loop_next_list, dict):
                loop_next_list = [loop_next_list]
            elif not isinstance(loop_next_list, list):
                loop_next_list = []

            if len(loop_next_list) >= 2:
                item = loop_next_list[1]
                return item.get("target") if isinstance(item, dict) else item
            return None

    if next_list:
        item = next_list[0]
        return item.get("target") if isinstance(item, dict) else item

    return None

def evaluate_prompt_transition(node: dict, user_input: str, var_prompt: list, base_prompt: str, setting: str) -> str:
    next_list = node.get("next", [])
    if isinstance(next_list, dict):
        next_list = [next_list]
    elif not isinstance(next_list, list):
        next_list = []

    if not next_list:
        return None

    if len(next_list) == 1:
        item = next_list[0]
        return item.get("target") if isinstance(item, dict) else item

    choices = []
    for item in next_list:
        if isinstance(item, dict):
            target = item.get("target")
            reason = item.get("reason", "No reason provided")
            choices.append((target, reason))
        else:
            choices.append((str(item), "Transition to " + str(item)))

    if choices:
        prompt = (
            f"You are a routing state machine coordinator.\n"
            f"Setting: {setting}\n"
            f"Base character info: {base_prompt}\n\n"
            f"The user said: \"{user_input}\"\n\n"
            f"Select the best target node from the options below based on their description:\n"
        )
        for idx, (target, reason) in enumerate(choices):
            prompt += f"{idx + 1}. Node Target: '{target}' - Condition: {reason}\n"

        prompt += (
            f"\nRespond with ONLY the target node ID (e.g., '{choices[0][0]}') and absolutely nothing else. "
            f"If none of them match, respond with '{choices[0][0]}'."
        )

        try:
            response_generator = api_request([{"role": "system", "content": prompt}], stream=False)
            res_text = ""
            if hasattr(response_generator, "__iter__") and not isinstance(response_generator, str):
                for chunk in response_generator:
                    res_text += chunk
            else:
                res_text = str(response_generator)

            cleaned_res = res_text.strip().replace("'", "").replace('"', "")
            matched = None
            for target, _ in choices:
                if target in cleaned_res or cleaned_res in target:
                    matched = target
                    break
            if matched:
                return matched
            return choices[0][0]
        except Exception as e:
            logger.error(f"Error classifying next node: {e}")
            return choices[0][0]

    return None

def traverse_fsm(user_input: str, active_node_id: str, layout: dict, var_prompt: list, base_prompt: str = "", setting: str = "", loop_state: dict = None) -> tuple:
    """
    Traverses the FSM using prompt-based structures rather than purely visual nodes.
    Automatically advances through flow control nodes (start, loop, end).
    """
    active_node = None
    if active_node_id:
        active_node = next((node for node in var_prompt if node.get("id") == active_node_id), None)

    if not active_node:
        active_node = next((node for node in var_prompt if node.get("type") == "start-node" or node.get("id") == "start"), None)
        if not active_node and var_prompt:
            active_node = var_prompt[0]

    if not active_node:
        return None, {}, []

    # Determine transition from current active node
    is_flow_node = (
        active_node.get("node_class") == "flow" or
        active_node.get("type") in ["start-node", "loop-node", "loop", "cycle-node", "cycle", "end-node", "end"] or
        active_node.get("id") in ["start", "end"]
    )

    if is_flow_node:
        next_node_id = get_automatic_transition(active_node, var_prompt, loop_state)
    else:
        next_node_id = evaluate_prompt_transition(active_node, user_input, var_prompt, base_prompt, setting)

    # Automatically advance through subsequent flow nodes
    visited_nodes = set()
    while next_node_id and next_node_id not in visited_nodes:
        visited_nodes.add(next_node_id)
        next_node = next((node for node in var_prompt if node.get("id") == next_node_id), None)
        if not next_node:
            break

        is_next_flow = (
            next_node.get("node_class") == "flow" or
            next_node.get("type") in ["start-node", "loop-node", "loop", "cycle-node", "cycle", "end-node", "end"] or
            next_node.get("id") in ["start", "end"]
        )
        if is_next_flow:
            next_node_id = get_automatic_transition(next_node, var_prompt, loop_state)
        else:
            break

    # Resolve target active node configuration
    next_node_config = next((node for node in var_prompt if node.get("id") == next_node_id), None)
    if not next_node_config:
        next_node_config = active_node

    possible_next_nodes = []
    if next_node_config:
        next_transitions = next_node_config.get("next", [])
        if isinstance(next_transitions, dict):
            next_transitions = [next_transitions]
        elif not isinstance(next_transitions, list):
            next_transitions = []
        for item in next_transitions:
            if isinstance(item, dict):
                target = item.get("target")
                if target:
                    possible_next_nodes.append(target)
            elif item:
                possible_next_nodes.append(str(item))

    return next_node_id, next_node_config, possible_next_nodes