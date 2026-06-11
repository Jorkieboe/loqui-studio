import logging
from typing import Dict, Any, List
from scripts.core.chatsession import traverse_fsm
from scripts.services.rag_service import retrieve_hybrid, extract_metadata_categories, rewrite_query
from scripts.services.llm_service import api_request

logger = logging.getLogger(__name__)

def assemble_system_prompt(
    base_prompt: str,
    dos: list,
    donts: list,
    context: dict,
    active_node_config: dict,
    rag_context_text: str = ""
) -> str:
    """
        Assemble the system prompt by combinting different properties in one string
    """
    system_prompt = f"{base_prompt}\n\n"

    if dos:
        system_prompt += "GUIDELINES (DO):\n"
        for item in dos:
            system_prompt += f"- {item}\n"
        system_prompt += "\n"

    if donts:
        system_prompt += "GUIDELINES (DON'T):\n"
        for item in donts:
            system_prompt += f"- {item}\n"
        system_prompt += "\n"

    if context:
        system_prompt += "HISTORICAL CONTEXT:\n"
        for k, v in context.items():
            if v:
                system_prompt += f"- {k.capitalize()}: {v}\n"
        system_prompt += "\n"

    if active_node_config:
        system_prompt += "ACTIVE DIALOGUE STATE OBJECTIVES:\n"
        goal = active_node_config.get("goal")
        tone = active_node_config.get("tone")
        example = active_node_config.get("example")
        follow_up = active_node_config.get("follow_up")

        if goal:
            system_prompt += f"- Current Goal: {goal}\n"
        if tone:
            system_prompt += f"- Tone of voice: {tone}\n"
        if example:
            system_prompt += f"- Style Example: \"{example}\"\n"
        if follow_up:
            system_prompt += f"- Next follow up point to check: {follow_up}\n"
        system_prompt += "\n"

    if rag_context_text:
        system_prompt += "RETRIEVED FACTUAL HISTORICAL DATA (Grounded Guardrails):\n"
        system_prompt += f"{rag_context_text}\n\n"
        system_prompt += "Strict Instruction: Use the retrieved factual historical data to ground your answer and avoid hallucinations. If the info is not in the data, deflection is preferred rather than inventing modern details.\n\n"

    return system_prompt

def run_dialogue_pipeline(user_input: str, active_node_id: str, history: List[Dict[str, str]], character_config: dict, loop_state: dict = None) -> Dict[str, Any]:
    """
        get character data, find current node, retrieve relevant information, generate response
    """
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
    print(rag_settings)
    rag_scheme = rag_settings.get("ragScheme")
    print(rag_scheme)

    ext_info = active_node_config.get("ext_info", "disabled")
    print(ext_info)

    # if rag_scheme and ext_info == "fetch":
    #     print('do rag')
    #     search_query = rewrite_query(user_input, history)
    #     logger.info(f"[Orchestrator] Rewritten search query: {search_query}")

    #     pov = rag_settings.get("pov", "all")
    #     chunksize = rag_settings.get("chunksize", 4)
    #     retrieved_chunks = retrieve_hybrid(search_query, rag_scheme, pov, chunksize)

    #     if retrieved_chunks:
    #         rag_context_text = "Retrieved Chunks:\n"
    #         for chunk in retrieved_chunks:
    #             rag_context_text += f"- {chunk['text']}\n"

    #         metadata_categories = extract_metadata_categories(retrieved_chunks)

    system_prompt = assemble_system_prompt(
        base_prompt=base_prompt,
        dos=dos,
        donts=donts,
        context=context,
        active_node_config=active_node_config,
        rag_context_text=rag_context_text
    )

    api_messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        role = turn.get("role", "user")
        text = turn.get("text", turn.get("content", ""))
        if role in ["user", "assistant"]:
            api_messages.append({"role": role, "content": text})

    api_messages.append({"role": "user", "content": user_input})

    response_stream = api_request(api_messages, stream=True)

    return {
        "next_node_id": next_node_id,
        "possible_next_nodes": possible_next_nodes,
        "response_stream": response_stream,
        "retrieved_chunks": retrieved_chunks,
        "metadata_categories": metadata_categories
    }