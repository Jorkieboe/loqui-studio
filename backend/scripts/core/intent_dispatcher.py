import os
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from scripts.utils.logger import PipelineLogger

load_dotenv()

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BACKEND_DIR, "config.json")

def load_jev_config() -> Dict[str, Any]:
    cfg = {
        "api_url": "https://api.typesafe.ai/v1/systemone",
        "model": "jev-latest",
        "state_key": "state",
        "schema_key": "questions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "timeout": 15,
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data.get("jev"), dict):
                    cfg.update(data["jev"])
        except Exception as e:
            logger.warning(f"Failed to load jev config from config.json: {e}")

    env_url = os.environ.get("JEV_API_URL")
    if env_url:
        cfg["api_url"] = env_url
    env_model = os.environ.get("JEV_MODEL")
    if env_model:
        cfg["model"] = env_model
    env_state_key = os.environ.get("JEV_STATE_KEY")
    if env_state_key:
        cfg["state_key"] = env_state_key
    env_schema_key = os.environ.get("JEV_SCHEMA_KEY")
    if env_schema_key is not None:
        cfg["schema_key"] = env_schema_key
    return cfg

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

        if node_id in shelved_flow_ids:
            shelved_label = shelved_flow_ids[node_id]
            description = (
                f"{trigger_intent}. "
                f"Also select this if the user wants to resume or return to the previously discussed topic '{shelved_label}'."
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

def build_jev_choice_schema(
    reactive_nodes: List[Dict[str, Any]],
    active_flow: str = "main",
    open_topics: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    shelved_flow_ids = {}
    if open_topics:
        for topic in open_topics:
            flow_id = topic.get("flow_id")
            flow_label = topic.get("flow_label") or flow_id
            if flow_id:
                shelved_flow_ids[flow_id] = flow_label

    criteria: Dict[str, str] = {}
    option_to_node_id: Dict[str, str] = {}

    for node in reactive_nodes:
        node_id = node.get("id")
        if not node_id:
            continue

        if active_flow and active_flow != "main" and node_id == active_flow:
            continue

        base_name = (node.get("displayName") or node.get("label") or node_id).strip()
        option_name = base_name if base_name not in criteria else f"{base_name} ({node_id})"
        trigger_intent = (node.get("trigger_intent") or f"User intent for {base_name}").strip()

        if node_id in shelved_flow_ids:
            shelved_label = shelved_flow_ids[node_id]
            description = (
                f"{trigger_intent} "
                f"(Also select this if the user wants to resume or accepts returning to the previously discussed topic '{shelved_label}'.)"
            )
        else:
            description = trigger_intent

        criteria[option_name] = description
        option_to_node_id[option_name] = node_id

    resume_desc = (
        f"Continue the current conversation flow ('{active_flow}') if the user is not switching to another node or returning to a shelved topic."
        if active_flow and active_flow != "main"
        else "Continue the current conversation flow or answer the assistant's previous question without switching to a reactive node."
    )
    resume_key = "resume_current_flow" if "resume_current_flow" not in criteria else "resume_current_flow (default)"
    criteria[resume_key] = resume_desc
    option_to_node_id[resume_key] = "resume_current_flow"

    schema = {
        "new_choice_1": {
            "type": "choice",
            "instructions": "Which option best fits the state?",
            "criteria": criteria
        }
    }
    return schema, option_to_node_id

def build_intent_state(
    user_input: str,
    history: List[Dict[str, Any]],
    active_flow: str = "main",
    open_topics: Optional[List[Dict[str, Any]]] = None
) -> str:
    parts = [f"Active flow: {active_flow or 'main'}"]

    if open_topics:
        topic_list = ", ".join(
            f"{t.get('flow_label') or t.get('flow_id')} (node: {t.get('flow_id')})"
            for t in open_topics
            if t.get("flow_id")
        )
        if topic_list:
            parts.append(f"Shelved open topics awaiting return: {topic_list}")

    recent_turns = []
    if history:
        for turn in history[-6:]:
            if isinstance(turn, dict):
                role = turn.get("role", "user")
                if role == "character":
                    role = "assistant"
                content = (turn.get("content") or turn.get("text") or "").strip()
                if content:
                    recent_turns.append(f"{role}: {content}")
            elif isinstance(turn, str) and turn.strip():
                recent_turns.append(f"user: {turn.strip()}")

    if recent_turns:
        parts.append("Recent conversation:\n" + "\n".join(recent_turns))

    parts.append(f"Latest user message: {user_input}")
    return "\n\n".join(parts)

def extract_jev_selected_option(response_data: Any, choice_key: str = "new_choice_1") -> Optional[str]:
    if isinstance(response_data, str):
        return response_data.strip()

    if not isinstance(response_data, dict):
        return None

    candidates = [
        response_data.get(choice_key),
        response_data.get("answers", {}).get(choice_key) if isinstance(response_data.get("answers"), dict) else None,
        response_data.get("results", {}).get(choice_key) if isinstance(response_data.get("results"), dict) else None,
        response_data.get("result", {}).get(choice_key) if isinstance(response_data.get("result"), dict) else None,
        response_data.get("output", {}).get(choice_key) if isinstance(response_data.get("output"), dict) else None,
        response_data.get("data", {}).get(choice_key) if isinstance(response_data.get("data"), dict) else None,
        response_data,
    ]

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if isinstance(candidate, dict):
            for key in ("choice", "selected", "selection", "option", "value", "answer", "label", "decision", "output", "result"):
                val = candidate.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()

    return None

def resolve_jev_choice(selected_option: Optional[str], option_to_node_id: Dict[str, str]) -> Optional[str]:
    if not selected_option:
        return None

    cleaned = selected_option.strip().strip("'").strip('"')
    if cleaned in option_to_node_id:
        return option_to_node_id[cleaned]
    if cleaned in option_to_node_id.values():
        return cleaned

    cleaned_lower = cleaned.lower()
    for opt_name, node_id in option_to_node_id.items():
        if opt_name.lower() == cleaned_lower:
            return node_id
    for node_id in option_to_node_id.values():
        if node_id.lower() == cleaned_lower:
            return node_id

    return None

def call_jev_decision(
    state: str,
    jev_schema: Dict[str, Any],
    api_key: str,
    api_url: str,
    model: str = "jev-latest",
    state_key: str = "state",
    schema_key: str = "questions",
    auth_header: str = "Authorization",
    auth_prefix: str = "Bearer ",
    timeout: int = 15
) -> Any:
    if not api_key:
        raise ValueError("JEV_API_KEY is missing")
    if not api_url:
        raise ValueError("JEV_API_URL is not configured")

    if schema_key:
        payload = {"model": model, state_key: state, schema_key: jev_schema}
    else:
        payload = {"model": model, state_key: state, **jev_schema}

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        auth_header: f"{auth_prefix}{api_key}",
    }
    req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            return json.loads(raw_body)
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"Jev API HTTP {e.code}: {err_body or e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"Jev API request failed: {e}") from e

def _fallback_intent_match(
    user_input: str,
    reactive_nodes: List[Dict[str, Any]],
    active_flow: str = "main",
    open_topics: Optional[List[Dict[str, Any]]] = None
) -> str:
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

    jev_schema, option_to_node_id = build_jev_choice_schema(
        reactive_nodes=reactive_nodes,
        active_flow=active_flow,
        open_topics=open_topics,
    )
    available_options = list(option_to_node_id.keys())
    api_key = os.environ.get("JEV_API_KEY")

    if api_key:
        jev_cfg = load_jev_config()
        api_url = (jev_cfg.get("api_url") or "").strip()
        if not api_url:
            msg = "JEV_API_KEY is set, but JEV_API_URL (or config.json jev.api_url) is not configured."
            PipelineLogger.error(msg)
            raise RuntimeError(msg)

        state = build_intent_state(
            user_input=user_input,
            history=history,
            active_flow=active_flow,
            open_topics=open_topics,
        )

        try:
            response_data = call_jev_decision(
                state=state,
                jev_schema=jev_schema,
                api_key=api_key,
                api_url=api_url,
                model=jev_cfg.get("model", "jev-latest"),
                state_key=jev_cfg.get("state_key", "state"),
                schema_key=jev_cfg.get("schema_key", "questions"),
                auth_header=jev_cfg.get("auth_header", "Authorization"),
                auth_prefix=jev_cfg.get("auth_prefix", "Bearer "),
                timeout=int(jev_cfg.get("timeout", 15)),
            )
            selected_option = extract_jev_selected_option(response_data)
            resolved_node = resolve_jev_choice(selected_option, option_to_node_id)

            if resolved_node:
                PipelineLogger.llm_status(
                    f"Jev Intent Dispatcher selected option '{selected_option}' -> '{resolved_node}' | Options: {available_options}"
                )
                return resolved_node

            raise RuntimeError(
                f"Jev returned unrecognized choice '{selected_option}'. Expected one of: {available_options}. Raw response: {response_data}"
            )
        except Exception as e:
            PipelineLogger.error("Jev intent decision failed", e)
            raise

    fallback_intent = _fallback_intent_match(
        user_input,
        reactive_nodes,
        active_flow=active_flow,
        open_topics=open_topics,
    )
    PipelineLogger.llm_status(
        f"JEV_API_KEY not found in environment. Intent Dispatcher fallback evaluated: '{fallback_intent}' | Options: {available_options}"
    )
    return fallback_intent