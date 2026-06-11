import logging
from scripts.services.llm_service import api_request

logger = logging.getLogger(__name__)

def traverse_fsm(user_input: str, active_node_id: str, layout: dict, var_prompt: list, base_prompt: str = "", setting: str = "") -> tuple:
    """
    Traverses the FSM using prompt-based structures rather than purely visual nodes.
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

    current_id = active_node.get("id")
    next_list = active_node.get("next", [])

    if isinstance(next_list, dict):
        next_list = [next_list]
    elif not isinstance(next_list, list):
        next_list = []

    next_node_id = None
    if len(next_list) == 1:
        item = next_list[0]
        if isinstance(item, dict):
            next_node_id = item.get("target")
        else:
            next_node_id = item
    elif len(next_list) > 1:
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
                    next_node_id = matched
                else:
                    next_node_id = choices[0][0]
            except Exception as e:
                logger.error(f"Error classifying next node: {e}")
                next_node_id = choices[0][0]

    if not next_node_id:
        next_node_id = current_id

    next_node_config = next((node for node in var_prompt if node.get("id") == next_node_id), None)
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

    return next_node_id, active_node, possible_next_nodes