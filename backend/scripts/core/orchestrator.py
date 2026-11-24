from typing import Dict, Any, List, Optional
from scripts.core.chatsession import traverse_fsm, extract_target, find_node_by_id
from scripts.core.session_manager import ChatSession
from scripts.core.intent_dispatcher import evaluate_intent, build_intent_tools
from scripts.services.rag_service import retrieve_hybrid, extract_metadata_categories, rewrite_query
from scripts.services.llm_service import api_request
from scripts.utils.helpers import is_empty_pov, extract_chunk_id_and_text, iter_history_turns
from scripts.utils.logger import PipelineLogger

def assemble_bridge_directive(open_topics: list) -> str:
    if open_topics:
        last_topic = open_topics[-1]
        label = last_topic.get("flow_label") or last_topic.get("flow_id", "previous topic")
        return f"Wrap up the current topic concisely, then ask the user if they'd like to return to {label}."
    return "Conclude the current topic naturally without forcing a question. Do not ask generic helpdesk questions like 'how else can I help' or invent new questions to keep the chat going."

def assemble_system_prompt(
    base_prompt: str,
    dos: list,
    donts: list,
    context: dict,
    active_node_config: dict,
    rag_context_text: str = "",
    bridge_directive: str = ""
) -> str:
    system_prompt = f"{base_prompt}\n\n"

    if dos:
        system_prompt += "do's:\n"
        for item in dos:
            system_prompt += f"- {item}\n"
        system_prompt += "\n"

    if donts:
        system_prompt += "dont's:\n"
        for item in donts:
            system_prompt += f"- {item}\n"
        system_prompt += "\n"

    if context:
        system_prompt += "Context:\n"
        for k, v in context.items():
            if v:
                system_prompt += f"- {k.capitalize()}: {v}\n"
        system_prompt += "\n"

    if active_node_config:
        system_prompt += "CURRENT GOAL (STRICTLY LEADING):\n"
        system_prompt += "This goal is your primary objective. It takes precedence over general background facts and must always be addressed in your response.\n"
        goal = active_node_config.get("goal")
        tone = active_node_config.get("tone")
        example = active_node_config.get("example")
        follow_up = active_node_config.get("follow_up")

        if goal:
            system_prompt += f"- Goal: {goal}\n"
        if tone:
            system_prompt += f"- Tone of voice: {tone}\n"
        if example:
            system_prompt += f"- Style Example: \"{example}\"\n"
        if follow_up:
            system_prompt += f"- Next follow up point to check: {follow_up}\n"
        system_prompt += "\n"

    if bridge_directive:
        system_prompt += f"BRIDGE DIRECTIVE:\n{bridge_directive}\n\n"

    return system_prompt

def _shelve_active_flow(session_instance: Any, reactive_nodes: list, target_intent: str, active_node_id: str) -> None:
    if session_instance.active_flow_id and session_instance.active_flow_id != "main" and session_instance.active_flow_id != target_intent:
        curr_node = find_node_by_id(reactive_nodes, session_instance.active_flow_id)
        curr_label = curr_node.get("flow_label", session_instance.active_flow_id) if curr_node else session_instance.active_flow_id
        session_instance.open_topics.append({
            "flow_id": session_instance.active_flow_id,
            "flow_label": curr_label,
            "paused_node_id": active_node_id
        })

def _get_first_non_bridge_child(node: dict, var_prompt: list) -> Optional[dict]:
    next_trans = node.get("next", [])
    first_target = extract_target(next_trans[0]) if (isinstance(next_trans, list) and next_trans) else None
    first_child = find_node_by_id(var_prompt, first_target) if first_target else None
    if first_child and first_child.get("type") != "bridge-node":
        return first_child
    return None

def run_dialogue_pipeline(
    user_input: str,
    active_node_id: str,
    history: List[Dict[str, str]],
    character_config: dict,
    loop_state: dict = None,
    session_instance: Any = None
) -> Dict[str, Any]:
    from scripts.services.ollama_service import manage_models, is_ollama_available, load_ollama_config
    ollama_cfg = load_ollama_config()
    if ollama_cfg.get("enabled", True) and is_ollama_available():
        manage_models()

    info = character_config.get("info", {})
    prompts = character_config.get("prompts", {})
    layout = character_config.get("layout", {})

    base_prompt = prompts.get("base_prompt", "")
    dos = prompts.get("do", [])
    donts = prompts.get("don't", [])
    context = prompts.get("context", {})
    var_prompt = prompts.get("var_prompt", [])

    if session_instance is None:
        session_instance = ChatSession(current_node_id=active_node_id, history=history)

    reactive_nodes = [n for n in var_prompt if n.get("node_class") == "reactive"]

    intent = "resume_current_flow"
    dynamic_tools = build_intent_tools(reactive_nodes, active_flow=session_instance.active_flow_id, open_topics=session_instance.open_topics) if reactive_nodes else []

    if reactive_nodes:
        intent = evaluate_intent(
            user_input=user_input,
            history=history,
            reactive_nodes=reactive_nodes,
            active_flow=session_instance.active_flow_id,
            open_topics=session_instance.open_topics
        )

    available_tool_names = [t.get("function", {}).get("name") for t in dynamic_tools]
    PipelineLogger.flow(f"Intent resolved: '{intent}' | Available tools: {available_tool_names}")
    PipelineLogger.llm_status(f"Pipeline evaluated intent: '{intent}', current active_flow: '{session_instance.active_flow_id}'")

    bridge_directive = ""

    if intent == "resume_current_flow":
        next_node_id, active_node_config, possible_next_nodes = traverse_fsm(
            user_input=user_input,
            active_node_id=active_node_id,
            layout=layout,
            var_prompt=var_prompt,
            base_prompt=base_prompt,
            setting=context.get("setting", ""),
            loop_state=loop_state
        )
        if active_node_config and active_node_config.get("type") == "bridge-node":
            if session_instance.open_topics:
                bridge_directive = assemble_bridge_directive(session_instance.open_topics)
            elif active_node_config.get("goal") and active_node_config.get("goal").strip():
                bridge_directive = active_node_config.get("goal").strip()
            else:
                bridge_directive = assemble_bridge_directive([])
            previous_flow = session_instance.active_flow_id
            session_instance.active_flow_id = "main"
            PipelineLogger.flow(f"Flow transition via bridge '{active_node_config.get('id')}': '{previous_flow}' -> 'main'")
    else:
        matched_node = find_node_by_id(reactive_nodes, intent)
        if matched_node and matched_node.get("mode") == "standalone":
            active_node_config = matched_node
            next_node_id = active_node_id
            possible_next_nodes = []
        elif matched_node:
            shelved_idx = next(
                (i for i, t in enumerate(session_instance.open_topics) if t.get("flow_id") == intent),
                None
            )
            _shelve_active_flow(session_instance, reactive_nodes, intent, active_node_id)
            previous_flow = session_instance.active_flow_id
            session_instance.active_flow_id = intent
            if shelved_idx is not None:
                shelved = session_instance.open_topics.pop(shelved_idx)
                PipelineLogger.flow(f"Flow resumed from open topics: '{previous_flow}' -> '{intent}'")
                resume_target = shelved.get("paused_node_id") or intent
                target_config = find_node_by_id(var_prompt, resume_target) or matched_node
                if target_config and (target_config.get("type") == "bridge-node" or not target_config.get("goal")):
                    target_config = matched_node
                if target_config and not target_config.get("goal"):
                    first_child = _get_first_non_bridge_child(target_config, var_prompt)
                    if first_child:
                        target_config = first_child
                active_node_config = target_config
            else:
                PipelineLogger.flow(f"Flow activated from reactive node '{intent}': '{previous_flow}' -> '{intent}'")
                # If reactive flow node has no direct goal, advance into its first child prompt node
                first_child = _get_first_non_bridge_child(matched_node, var_prompt)
                if not matched_node.get("goal") and first_child:
                    active_node_config = first_child
                else:
                    active_node_config = matched_node

            next_node_id = active_node_config.get("id")
            child_trans = active_node_config.get("next", [])
            possible_next_nodes = [t.get("target") for t in child_trans if isinstance(t, dict) and t.get("target")]
        else:
            next_node_id, active_node_config, possible_next_nodes = traverse_fsm(
                user_input=user_input,
                active_node_id=active_node_id,
                layout=layout,
                var_prompt=var_prompt,
                base_prompt=base_prompt,
                setting=context.get("setting", ""),
                loop_state=loop_state
            )

    retrieved_chunks = []
    metadata_categories = {}
    rag_context_text = ""

    rag_settings = info.get("rag", {})
    rag_scheme = rag_settings.get("ragScheme")
    ext_info = active_node_config.get("ext_info", "disabled") if active_node_config else "disabled"
    executed_node_id = active_node_config.get("id") if active_node_config else active_node_id
    search_query = ""

    flow_filters = {}
    if session_instance.active_flow_id and session_instance.active_flow_id != "main":
        flow_node = find_node_by_id(var_prompt, session_instance.active_flow_id)
        if flow_node and isinstance(flow_node.get("rag_filters"), dict):
            flow_filters = flow_node.get("rag_filters") or {}
    else:
        start_node = next((n for n in var_prompt if n.get("type") == "start-node" or n.get("id") == "start"), None)
        if start_node and isinstance(start_node.get("rag_filters"), dict):
            flow_filters = start_node.get("rag_filters") or {}

    node_filters = active_node_config.get("rag_filters") or {} if active_node_config else {}
    metadata_filters = {}
    for k, v in flow_filters.items():
        if v:
            metadata_filters[k] = v
    if isinstance(node_filters, dict):
        for k, v in node_filters.items():
            if v:
                metadata_filters[k] = v

    is_bridge = active_node_config.get("type") == "bridge-node" if active_node_config else False
    if is_bridge and (not ext_info or ext_info == "disabled"):
        ext_info = "reuse"

    PipelineLogger.llm_status(f"Pipeline Active Node: {executed_node_id}, ext_info: {ext_info}, rag_scheme: {rag_scheme}")

    if rag_scheme and ext_info in ["reuse", "resume", "resum"]:
        retrieved_chunks = getattr(session_instance, "last_retrieved_chunks", []) or []
        if retrieved_chunks:
            PipelineLogger.rag(f"Reusing {len(retrieved_chunks)} cached RAG chunks for node '{executed_node_id}'")
        else:
            PipelineLogger.rag(f"No cached chunks to reuse for node '{executed_node_id}'. Fetching fresh chunks...")
            ext_info = "fetch"

    if rag_scheme and ext_info == "fetch":
        PipelineLogger.rag("Executing Retrieval-Augmented Generation (RAG)")
        node_goal = active_node_config.get("goal", "") if active_node_config else ""
        search_query = rewrite_query(user_input, history, current_goal=node_goal)
        PipelineLogger.rag(f"Combined RAG search query: '{search_query}'")

        pov = rag_settings.get("pov")
        if is_empty_pov(pov):
            pov = "None"
        chunksize = rag_settings.get("chunksize", 4)
        retrieved_chunks = retrieve_hybrid(
            search_query,
            rag_scheme,
            pov,
            chunksize,
            metadata_filters=metadata_filters,
        )
        session_instance.last_retrieved_chunks = retrieved_chunks

    if retrieved_chunks:
        rag_context_text = "Retrieved Chunks:\n"
        for chunk in retrieved_chunks:
            chunk_id, text_val = extract_chunk_id_and_text(chunk, default_id="N/A")
            rag_context_text += f"- [{chunk_id}]: {text_val}\n"
            PipelineLogger.rag(f"Retrieved chunk [{chunk_id}]: {text_val[:60]}...")

        metadata_categories = extract_metadata_categories(retrieved_chunks)
        PipelineLogger.rag(f"Metadata categories: {metadata_categories}")

    system_prompt = assemble_system_prompt(
        base_prompt=base_prompt,
        dos=dos,
        donts=donts,
        context=context,
        active_node_config=active_node_config,
        bridge_directive=bridge_directive
    )

    PipelineLogger.llm_status(system_prompt)

    api_messages = [{"role": "system", "content": system_prompt}]
    for role, text in iter_history_turns(history):
        if role in ["user", "assistant"]:
            api_messages.append({"role": role, "content": text})

    rag_section = ""
    if rag_context_text:
        rag_section = (
            "--- BACKGROUND REFERENCE KNOWLEDGE (SECONDARY) ---\n"
            f"{rag_context_text}\n"
            "CRITICAL INSTRUCTIONS FOR REFERENCE KNOWLEDGE:\n"
            "- Your CURRENT GOAL is strictly leading. Do NOT replace, skip, or derail your goal to recite these facts.\n"
            "- Use these reference facts ONLY as supporting background to enrich your answer while fulfilling your goal.\n"
            "- If any reference detail is not directly relevant to your current goal and character perspective, ignore it.\n"
            "- STRICT FACTUAL GROUNDING: For real-world or historical facts (specific places, venues, names, dates, or events), rely ONLY on the Reference Knowledge above, your character instructions, and the conversation history. Do NOT pull unprovided facts or extra details from your internal training memory.\n"
            "---------------------------------------------------\n\n"
        )
    elif rag_scheme:
        rag_section = (
            "--- BACKGROUND REFERENCE KNOWLEDGE ---\n"
            "(No reference chunks were retrieved or active for this turn.)\n"
            "STRICT FACTUAL GROUNDING:\n"
            "- Do NOT pull real-world facts, specific venues, names, dates, or historical details from your internal training memory.\n"
            "- Rely ONLY on your character instructions and the conversation history. If specific facts are requested that you do not have, stay in character and keep it general or admit you do not know.\n"
            "--------------------------------------\n\n"
        )

    user_payload = f"""{rag_section}Instructions:
- Address the user's message while strictly executing your CURRENT GOAL.
- Avoid repeating yourself, and do not repeat facts, phrases, or sentence structures you have already used.
- Speak naturally from your character's persona and time period. If something is beyond your realistic knowledge, express natural ignorance or deflect in character.
- Natural conversation flow: Do NOT end every turn with a question. Only ask a question if your current goal strictly requires it. Statements, casual reactions, or friendly sign-offs are preferred.
- Do NOT use robotic chatbot filler or customer-service praise (e.g. 'Zeker weten!', 'Goede keuze!', 'Ah, dat klinkt goed!', 'Lekker, toch?'). Respond authentically as a human.

User message: {user_input}"""

    api_messages.append({"role": "user", "content": user_payload})

    response_stream = api_request(api_messages, stream=True)

    active_step_id = active_node_config.get("id") if active_node_config else active_node_id
    active_step_name = (active_node_config.get("displayName") or active_node_config.get("label") or active_step_id) if active_node_config else active_step_id

    if next_node_id:
        session_instance.current_node_id = next_node_id

    return {
        "next_node_id": next_node_id,
        "active_step": active_step_id,
        "active_step_name": active_step_name,
        "possible_next_nodes": possible_next_nodes,
        "response_stream": response_stream,
        "retrieved_chunks": retrieved_chunks,
        "last_retrieved_chunks": getattr(session_instance, "last_retrieved_chunks", []),
        "metadata_categories": metadata_categories,
        "active_flow_id": session_instance.active_flow_id,
        "open_topics": session_instance.open_topics,
        "intent": intent,
        "dynamic_tools": dynamic_tools,
        "rag_scheme": rag_scheme,
        "rag_ext_info": ext_info,
        "rag_filters": metadata_filters,
        "rag_search_query": search_query,
        "system_prompt": system_prompt,
        "user_payload": user_payload
    }