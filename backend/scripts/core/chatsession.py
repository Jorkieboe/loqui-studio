import logging
from scripts.services.llm_service import api_request

logger = logging.getLogger(__name__)

FLOW_NODE_TYPES = ("start-node", "loop-node", "loop", "cycle-node", "cycle", "end-node", "end")

def extract_target(item):
    return item.get("target") if isinstance(item, dict) else item

def find_node_by_id(var_prompt: list, node_id: str) -> dict | None:
    if not node_id:
        return None
    return next((n for n in var_prompt if n.get("id") == node_id), None)

def _normalize_next_list(node: dict) -> list:
    next_list = node.get("next", [])
    if isinstance(next_list, dict):
        return [next_list]
    if isinstance(next_list, list):
        return next_list
    return []

def _is_flow_node(node: dict) -> bool:
    return (
        (node.get("node_class") == "flow" or
        node.get("type") in FLOW_NODE_TYPES or
        node.get("id") in ["start", "end"]) and
        node.get("type") != "bridge-node"
    )

def get_automatic_transition(node: dict, var_prompt: list, loop_state: dict) -> str:
    node_type = node.get("type", "")
    node_id = node.get("id", "")
    node_class = node.get("node_class", "")
    next_list = _normalize_next_list(node)

    is_loop = (node_type in ["loop-node", "loop"] or "loop" in node_id or "loop" in node_class)
    is_cycle = (node_type in ["cycle-node", "cycle"] or "cycle" in node_id or "cycle" in node_class)

    if is_loop:
        if loop_state is None:
            loop_state = {"counters": {}, "active_loop_id": None}
        loop_state["active_loop_id"] = node_id
        if node_id not in loop_state["counters"]:
            loop_state["counters"][node_id] = 0
        return extract_target(next_list[0]) if next_list else None

    if is_cycle:
        if loop_state is None:
            loop_state = {"counters": {}, "active_loop_id": None}

        loop_id = (
            loop_state.get("active_loop_id")
            or node.get("loop_id")
            or node.get("target_loop")
            or node.get("loop")
        )
        if not loop_id:
            for next_item in next_list:
                target = extract_target(next_item)
                if target:
                    target_node = find_node_by_id(var_prompt, target)
                    if target_node and (target_node.get("type") in ["loop-node", "loop"] or "loop" in target_node.get("id", "")):
                        loop_id = target
                        break

        loop_node = find_node_by_id(var_prompt, loop_id)
        if not loop_node:
            return extract_target(next_list[0]) if next_list else None

        loop_count = int(loop_node.get("loop_count", 2))
        if loop_id not in loop_state["counters"]:
            loop_state["counters"][loop_id] = 0

        loop_state["counters"][loop_id] += 1

        if loop_state["counters"][loop_id] < loop_count:
            return extract_target(next_list[0]) if next_list else loop_id
        else:
            loop_state["counters"][loop_id] = 0
            loop_state["active_loop_id"] = None
            loop_next_list = _normalize_next_list(loop_node)
            if len(loop_next_list) >= 2:
                return extract_target(loop_next_list[1])
            return None

    return extract_target(next_list[0]) if next_list else None

def evaluate_prompt_transition(node: dict, user_input: str, var_prompt: list, base_prompt: str, setting: str) -> str:
    next_list = _normalize_next_list(node)

    if not next_list:
        return None

    if len(next_list) == 1:
        return extract_target(next_list[0])

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
    active_node = find_node_by_id(var_prompt, active_node_id)

    if not active_node:
        active_node = next((node for node in var_prompt if node.get("type") == "start-node" or node.get("id") == "start"), None)
        if not active_node and var_prompt:
            active_node = var_prompt[0]

    if not active_node:
        return None, {}, []

    # Determine transition from current active node (bridge-node generates dialogue, not auto-skipped)
    if _is_flow_node(active_node):
        next_node_id = get_automatic_transition(active_node, var_prompt, loop_state)
    else:
        next_node_id = evaluate_prompt_transition(active_node, user_input, var_prompt, base_prompt, setting)

    # Automatically advance through subsequent flow nodes
    visited_nodes = set()
    while next_node_id and next_node_id not in visited_nodes:
        visited_nodes.add(next_node_id)
        next_node = find_node_by_id(var_prompt, next_node_id)
        if not next_node:
            break

        if _is_flow_node(next_node):
            next_node_id = get_automatic_transition(next_node, var_prompt, loop_state)
        else:
            break

    # Resolve target active node configuration
    next_node_config = find_node_by_id(var_prompt, next_node_id)
    if not next_node_config:
        if active_node and active_node.get("type") == "bridge-node":
            main_prompt = next((n for n in var_prompt if n.get("node_class") == "prompt" and n.get("type") != "bridge-node"), None)
            if main_prompt:
                next_node_config = main_prompt
                next_node_id = main_prompt.get("id")
        if not next_node_config:
            next_node_config = active_node
            next_node_id = active_node.get("id") if active_node else next_node_id

    possible_next_nodes = []
    if next_node_config:
        for item in _normalize_next_list(next_node_config):
            if isinstance(item, dict):
                target = item.get("target")
                if target:
                    possible_next_nodes.append(target)
            elif item:
                possible_next_nodes.append(str(item))

    return next_node_id, next_node_config, possible_next_nodes