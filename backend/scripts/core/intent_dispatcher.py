import os
import json
import logging
from typing import List, Dict, Any, Optional

from scripts.utils.logger import PipelineLogger
from scripts.services.llm_service import load_preset_config

logger = logging.getLogger(__name__)

def build_intent_tools(
    reactive_nodes: List[Dict[str, Any]],
    active_flow: str = "main",
    open_topics: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    tools = []
    shelved_flow_ids = {}
    if open_topics:
        for topic in open_topics:
            flow_id = topic.get("flow_id")
            flow_label = topic.get("flow_label") or flow_id
            if flow_id:
                shelved_flow_ids[flow_id] = flow_label

    for node in reactive_nodes:
        node_id = node.get("id")
        if not node_id:
            continue

        if active_flow and active_flow != "main" and node_id == active_flow:
            continue

        trigger_intent = node.get("trigger_intent", f"User intent for {node_id}")
        flow_label = node.get("flow_label", node_id)

        if node_id in shelved_flow_ids:
            shelved_label = shelved_flow_ids[node_id]
            description = (
            f"{trigger_intent}. "
            f"Select ONLY when the user's latest message clearly expresses this intent. "
            f"Do not select based on incidental keyword mentions."
            )     
        else:
            description = trigger_intent

        tools.append({
            "type": "function",
            "function": {
                "name": node_id,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        })

    resume_desc = (
        f"Select this to continue the current conversation (currently in flow '{active_flow}'). "
        "Do NOT select this if the user is agreeing to return to or asking about a previously shelved open topic."
        if active_flow and active_flow != "main"
        else "Select this if the user is continuing the current conversation or answering the assistant's previous question."
    )

    tools.append({
        "type": "function",
        "function": {
            "name": "resume_current_flow",
            "description": resume_desc,
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    })

    return tools

def _fallback_intent_match(user_input: str, reactive_nodes: List[Dict[str, Any]], active_flow: str = "main", open_topics: Optional[List[Dict[str, Any]]] = None) -> str:
    input_lower = user_input.lower()

    if open_topics:
        for topic in reversed(open_topics):
            flow_id = topic.get("flow_id")
            flow_label = (topic.get("flow_label") or "").lower()
            label_words = [w for w in flow_label.replace("&", " ").replace(",", " ").split() if len(w) > 3]
            resumption_terms = ["yes", "sure", "return", "back", "previous", "that", "tell me about", "restaurant", "food", "dinner"]
            wants_resume = any(t in input_lower for t in resumption_terms)
            matches_label = any(w in input_lower or w.rstrip("s") in input_lower for w in label_words) if label_words else False

            if wants_resume and (matches_label or len(open_topics) == 1):
                matched = next((n for n in reactive_nodes if n.get("id") == flow_id), None)
                if matched:
                    return flow_id

    best_match = None
    best_score = 0

    for node in reactive_nodes:
        node_id = node.get("id")
        if node_id == active_flow:
            continue

        trigger = (node.get("trigger_intent") or "").lower()
        label = (node.get("flow_label") or "").lower()

        keywords = set(w for w in (trigger + " " + label).replace(".", " ").replace(",", " ").split() if len(w) > 3)
        score = sum(1 for kw in keywords if kw in input_lower)

        if score > best_score:
            best_score = score
            best_match = node_id

    if best_score > 0 and best_match:
        return best_match

    return "resume_current_flow"

def evaluate_intent(
    user_input: str,
    history: List[Dict[str, Any]],
    reactive_nodes: List[Dict[str, Any]],
    active_flow: str = "main",
    open_topics: Optional[List[Dict[str, Any]]] = None
) -> str:
    if not reactive_nodes:
        return "resume_current_flow"

    tools = build_intent_tools(reactive_nodes, active_flow=active_flow, open_topics=open_topics)

    last_assistant_msg = None
    if history:
        for turn in reversed(history):
            if isinstance(turn, dict):
                role = turn.get("role", "")
                if role in ["assistant", "character", "ai"]:
                    last_assistant_msg = turn.get("content") or turn.get("text", "")
                    break

    shelved_info = ""
    if open_topics:
        topic_summaries = [f"'{t.get('flow_id')}' (topic: {t.get('flow_label')})" for t in open_topics]
        shelved_info = (
            f"\nShelved open topics awaiting return: {', '.join(topic_summaries)}.\n"
            "IMPORTANT: If the user accepts, agrees, or refers to returning to a shelved topic "
            "(e.g., saying 'yes', 'sure', or mentioning the topic name), you MUST call that topic's tool to resume it."
        )

    system_prompt = f"""
        You are an intent classification and conversation routing coordinator.

        Your ONLY responsibility is to classify the user's latest message
        and select the appropriate flow.

        CURRENT STATE:
        - Active flow: {active_flow}
        - Shelved topics: {shelved_info}

        CLASSIFICATION RULES:

        1. PRIORITIZE THE LATEST USER MESSAGE.
        Classify what the user actually wants now, not what they
        previously discussed.

        2. REACTIVE TOPICS:
        Select a reactive topic ONLY when the user's message clearly
        expresses an intent that matches that topic's description.

        3. RESUMING SHELVED TOPICS:
        A shelved topic should ONLY be resumed when:
        - The user explicitly asks to return to that topic.
        - The user refers to that topic unambiguously.
        - The previous assistant message explicitly offered to return
            to that topic and the user accepts that offer.

        4. CONTINUING CURRENT FLOW:
        If the user is asking something unrelated to reactive topics,
        continue the current flow.

        5. AMBIGUOUS MESSAGES:
        Messages such as "yes", "okay", "sure", "thanks", and "alright"
        must NOT automatically trigger a shelved topic.
        Interpret them using the previous assistant message.
        If there is insufficient context, continue the current flow.

        6. NEGATION:
        Never select a topic simply because its name appears in a
        sentence that rejects, denies, or discusses avoiding that topic.

        7. DO NOT GUESS:
        If no reactive topic clearly matches the user's intent,
        select resume_current_flow.

        IMPORTANT:
        - A keyword match is not sufficient.
        - Do not favor any particular topic.
        - Select exactly one tool.
        - The default is resume_current_flow.
        """

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]
    messages.append({"role": "assistent", "content": last_assistant_msg})
    messages.append({"role": "user", "content": user_input})

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            preset = load_preset_config("default")
            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model=preset.get("model", "gpt-4o-mini"),
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0
            )

            msg = response.choices[0].message
            available_tool_names = [t["function"]["name"] for t in tools]
            if msg.tool_calls:
                selected_tool = msg.tool_calls[0].function.name
                if selected_tool in available_tool_names:
                    PipelineLogger.llm_status(f"Intent Dispatcher tool selected: '{selected_tool}' | Available tools: {available_tool_names}")
                    return selected_tool

            PipelineLogger.llm_status(f"Intent Dispatcher defaulted to 'resume_current_flow' | Available tools: {available_tool_names}")
            return "resume_current_flow"
        except Exception as e:
            logger.warning(f"Intent classification API call failed: {e}. Using fallback classifier.")

    available_tool_names = [t["function"]["name"] for t in tools]
    fallback_intent = _fallback_intent_match(user_input, reactive_nodes, active_flow=active_flow, open_topics=open_topics)
    PipelineLogger.llm_status(f"Intent Dispatcher fallback evaluated: '{fallback_intent}' | Available tools: {available_tool_names}")
    return fallback_intent