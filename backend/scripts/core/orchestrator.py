from typing import Dict, Any, List
from scripts.core.chatsession import traverse_fsm
from scripts.services.rag_service import retrieve_hybrid, extract_metadata_categories, rewrite_query
from scripts.services.llm_service import api_request
from scripts.utils.logger import PipelineLogger

def assemble_system_prompt(
    base_prompt: str,
    dos: list,
    donts: list,
    context: dict,
    active_node_config: dict,
    rag_context_text: str = ""
) -> str:
    """
    Assemble the system prompt by combining different properties in one string.
    """
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
        system_prompt += "CURRENT GOAL (VAR PROMPT):\n"
        system_prompt += "This represents your immediate objective in the conversation. You must direct your response toward satisfying this goal.\n"
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

    return system_prompt

def run_dialogue_pipeline(user_input: str, active_node_id: str, history: List[Dict[str, str]], character_config: dict, loop_state: dict = None) -> Dict[str, Any]:
    """
        get character data, find current node, retrieve relevant information, generate response
    """
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
    ext_info = active_node_config.get("ext_info", "disabled")
    PipelineLogger.llm_status(f"Pipeline Active Node: {active_node_id}, ext_info: {ext_info}, rag_scheme: {rag_scheme}")

    if rag_scheme and ext_info == "fetch":
        PipelineLogger.rag("Executing Retrieval-Augmented Generation (RAG)")
        search_query = rewrite_query(user_input, history)
        PipelineLogger.rag(f"Rewritten search query: '{search_query}'")

        pov = rag_settings.get("pov", "all")
        chunksize = rag_settings.get("chunksize", 4)
        retrieved_chunks = retrieve_hybrid(search_query, rag_scheme, pov, chunksize)

        if retrieved_chunks:
            rag_context_text = "Retrieved Chunks:\n"
            for chunk in retrieved_chunks:
                if isinstance(chunk, dict):
                    text_val = chunk.get("text", "")
                else:
                    text_val = str(chunk)
                rag_context_text += f"- {text_val}\n"
                PipelineLogger.rag(f"Retrieved chunk [{chunk.get('id', 'N/A')}]: {text_val[:60]}...")

            metadata_categories = extract_metadata_categories(retrieved_chunks)
            PipelineLogger.rag(f"Metadata categories: {metadata_categories}")

    system_prompt = assemble_system_prompt(
        base_prompt=base_prompt,
        dos=dos,
        donts=donts,
        context=context,
        active_node_config=active_node_config
    )

    api_messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        if isinstance(turn, str):
            api_messages.append({"role": "user", "content": turn})
        elif isinstance(turn, dict):
            role = turn.get("role", "user")
            text = turn.get("text", turn.get("content", ""))
            if role in ["user", "assistant"]:
                api_messages.append({"role": role, "content": text})

    user_payload = f"""{
    f"Retrieved historical context info:\n{rag_context_text}\n\n"
        if rag_context_text else ""
    }
    Instructions: Review your previous responses in the dialogue history to ensure you do not repeat facts, phrases, or sentence structures you have already used.
    Avoid repeating yourself. Additionally, think carefully about whether your character would realistically know the retrieved historical information or the details being asked based on their setting and background.
    Do not speak of things outside your character's realistic perspective. If it is beyond their knowledge, deflect or state your ignorance naturally while staying strictly in character.

    User message: {user_input}"""

    api_messages.append({"role": "user", "content": user_payload})

    response_stream = api_request(api_messages, stream=True)

    return {
        "next_node_id": next_node_id,
        "possible_next_nodes": possible_next_nodes,
        "response_stream": response_stream,
        "retrieved_chunks": retrieved_chunks,
        "metadata_categories": metadata_categories
    }