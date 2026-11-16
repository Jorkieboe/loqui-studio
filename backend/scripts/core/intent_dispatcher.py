import os
import json
import logging
from typing import List, Dict, Any, Optional

from scripts.utils.logger import PipelineLogger
from scripts.services.llm_service import load_preset_config

logger = logging.getLogger(__name__)

def build_intent_tools(reactive_nodes: List[Dict[str, Any]], open_topics: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
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

        trigger_intent = node.get("trigger_intent", f"User intent for {node_id}")
        flow_label = node.get("flow_label", node_id)

        if node_id in shelved_flow_ids:
            shelved_label = shelved_flow_ids[node_id]
            description = (
                f"{trigger_intent} (Also select this if the user wants to resume/return to the "
                f"previously discussed topic about {shelved_label})"
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

    tools.append({
        "type": "function",
        "function": {
            "name": "resume_current_flow",
            "description": "Select this if the user does not want to switch flow and is continuing the current conversation or answering the assistant's previous question.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    })

    return tools

def _fallback_intent_match(user_input: str, reactive_nodes: List[Dict[str, Any]], open_topics: Optional[List[Dict[str, Any]]] = None) -> str:
    input_lower = user_input.lower()

    if open_topics:
        for topic in reversed(open_topics):
            flow_id = topic.get("flow_id")
            flow_label = (topic.get("flow_label") or "").lower()
            label_words = [w for w in flow_label.replace("&", " ").replace(",", " ").split() if len(w) > 3]
            resumption_terms = ["yes", "sure", "return", "back", "previous", "that", "tell me about"]
            wants_resume = any(t in input_lower for t in resumption_terms)
            matches_label = any(w in input_lower for w in label_words) if label_words else False

            if wants_resume and (matches_label or len(open_topics) == 1):
                matched = next((n for n in reactive_nodes if n.get("id") == flow_id), None)
                if matched:
                    return flow_id

    best_match = None
    best_score = 0

    for node in reactive_nodes:
        node_id = node.get("id")
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

    tools = build_intent_tools(reactive_nodes, open_topics=open_topics)

    context_turns = history[-6:] if history else []
    messages = [
        {
            "role": "system",
            "content": (
                "You are an intent classification routing coordinator. "
                "Analyze the conversation history and the latest user message. "
                "Determine if the user is triggering a reactive topic, resuming an open topic, "
                "or continuing the current flow. Call the appropriate tool function."
            )
        }
    ]

    for turn in context_turns:
        if isinstance(turn, dict):
            role = turn.get("role", "user")
            content = turn.get("content") or turn.get("text", "")
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})
        elif isinstance(turn, str):
            messages.append({"role": "user", "content": turn})

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
            if msg.tool_calls:
                selected_tool = msg.tool_calls[0].function.name
                valid_names = {t["function"]["name"] for t in tools}
                if selected_tool in valid_names:
                    PipelineLogger.llm_status(f"Intent Dispatcher tool selected: {selected_tool}")
                    return selected_tool

            return "resume_current_flow"
        except Exception as e:
            logger.warning(f"Intent classification API call failed: {e}. Using fallback classifier.")

    fallback_intent = _fallback_intent_match(user_input, reactive_nodes, open_topics)
    PipelineLogger.llm_status(f"Intent Dispatcher fallback evaluated: {fallback_intent}")
    return fallback_intent