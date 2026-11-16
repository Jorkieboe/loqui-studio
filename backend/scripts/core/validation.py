from typing import Dict, Any, List

def validate_character_graph(character_config: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    var_prompt = character_config.get("var_prompt")
    if var_prompt is None:
        prompts = character_config.get("prompts", {})
        var_prompt = prompts.get("var_prompt", [])

    if not isinstance(var_prompt, list):
        return ["var_prompt must be a list of nodes."]

    node_map = {n.get("id"): n for n in var_prompt if isinstance(n, dict) and n.get("id")}

    reactive_flow_nodes = [
        n for n in var_prompt
        if isinstance(n, dict)
        and n.get("node_class") == "reactive"
        and n.get("mode") == "flow"
    ]

    for reactive_node in reactive_flow_nodes:
        root_id = reactive_node.get("id")
        display_name = reactive_node.get("displayName") or root_id

        visited = set()
        queue = [root_id]
        has_bridge = False

        while queue:
            curr_id = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)

            curr_node = node_map.get(curr_id)
            if not curr_node:
                continue

            if curr_node.get("type") == "bridge-node" or (
                curr_node.get("node_class") == "flow" and curr_node.get("type") == "bridge-node"
            ):
                has_bridge = True
                break

            next_list = curr_node.get("next", [])
            if isinstance(next_list, dict):
                next_list = [next_list]
            elif not isinstance(next_list, list):
                next_list = []

            for item in next_list:
                target = item.get("target") if isinstance(item, dict) else item
                if target and target not in visited:
                    queue.append(target)

        if not has_bridge:
            errors.append(
                f"Reactive flow '{display_name}' must end with a connected Bridge node."
            )

    return errors