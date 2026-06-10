import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
import tiktoken
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BACKEND_DIR, "config.json")

def load_preset_config(preset_name: str = "default") -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("llm_presets", {}).get(preset_name, {})
        except Exception as e:
            logger.error(f"Failed to load llm_presets config: {e}")
    return {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 150,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "stop": None
    }

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            return len(text) // 4
    return len(encoding.encode(text))

def api_request(
    messages: List[Dict[str, str]],
    preset_name: str = "default",
    stream: bool = True
) -> Any:
    preset = load_preset_config(preset_name)
    api_key = os.environ.get("OPENAI_API_KEY")

    input_text = "".join([m.get("content", "") for m in messages])
    input_tokens = count_tokens(input_text, preset.get("model", "gpt-4o-mini"))
    logger.info(f"[LLM] Input tokens: {input_tokens}")

    if not api_key:
        logger.warning("[LLM] OPENAI_API_KEY not found in environment. Using fallback simulator.")
        def mock_generator():
            fallback_response = (
                "[SIMULATION MODE] This is a simulated character response because no OPENAI_API_KEY was found in the environment. "
                "Ensure your API keys are configured for full generative features."
            )
            for word in fallback_response.split(" "):
                yield word + " "
        return mock_generator() if stream else "Simulated response: OpenAI API Key not configured."

    client = OpenAI(api_key=api_key)

    kwargs = {
        "model": preset.get("model", "gpt-4o-mini"),
        "messages": messages,
        "temperature": preset.get("temperature", 0.7),
        "max_tokens": preset.get("max_tokens", 150),
        "presence_penalty": preset.get("presence_penalty", 0.0),
        "frequency_penalty": preset.get("frequency_penalty", 0.0),
        "stream": stream
    }

    if preset.get("stop"):
        kwargs["stop"] = preset["stop"]

    try:
        if stream:
            response = client.chat.completions.create(**kwargs)
            def response_generator():
                for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            yield delta
            return response_generator()
        else:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
    except Exception as e:
        logger.error(f"[LLM] OpenAI API Request failed: {e}")
        raise e