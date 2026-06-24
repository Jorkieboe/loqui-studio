import os
import json
import logging
import urllib.request
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
        "max_tokens": 1000,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "stop": None,
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
    from scripts.services.ollama_service import is_ollama_available, load_ollama_config
    ollama_cfg = load_ollama_config()
    ollama_active = ollama_cfg.get("llm_enabled", True) and is_ollama_available()
    base_url = None
    model_name = preset.get("model", "gpt-4o-mini")
    if ollama_active:
        host = ollama_cfg.get("host", "http://127.0.0.1:11434").rstrip("/")
        model_name = ollama_cfg.get("llm_model", "llama3")
        logger.info(f"[LLM] Routing request to Ollama native chat API: {model_name} at {host}")
        url = f"{host}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": preset.get("temperature", 0.7),
                "num_predict": preset.get("max_tokens", 150),
                "presence_penalty": preset.get("presence_penalty", 0.0),
                "frequency_penalty": preset.get("frequency_penalty", 0.0),
            }
        }
        if preset.get("stop"):
            payload["options"]["stop"] = preset["stop"]
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            if stream:
                response = urllib.request.urlopen(req, timeout=60)
                def response_generator():
                    try:
                        chunk_count = 0
                        for line in response:
                            if line:
                                decoded_line = line.decode("utf-8").strip()
                                if decoded_line:
                                    try:
                                        chunk_data = json.loads(decoded_line)
                                        delta = chunk_data.get("message", {}).get("content", "")
                                        chunk_count += 1
                                        if delta:
                                            yield delta
                                    except Exception as parse_err:
                                        logger.error(f"[LLM Ollama] Parse error: {parse_err}")
                            logger.info(f"[LLM Ollama] Stream completed. Total chunks received: {chunk_count}")
                    finally:
                            response.close()
                    return response_generator()
            else:
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    content = res_data.get("message", {}).get("content", "")
                    logger.info(f"[LLM Ollama] Non-stream response received. Length: {len(content) if content else 0}")
                    return content
        except Exception as e:
            logger.error(f"[LLM Ollama] Request failed: {e}")
            raise e
    if not api_key:
        logger.warning("[LLM] OPENAI_API_KEY not found in environment and Ollama is not available. Using fallback simulator.")
        def mock_generator():
            fallback_response = (
                "[SIMULATION MODE] This is a simulated character response because no OPENAI_API_KEY was found in the environment and Ollama is not active. "
                "Ensure your API keys or local Ollama instances are configured."
            )
            for word in fallback_response.split(" "):
                yield word + " "
        return mock_generator() if stream else "Simulated response: OpenAI API Key not configured."
    logger.info(f"[LLM] Routing request to model: {model_name}")
    logger.info(f"[LLM] Base URL: {base_url}")
    client = OpenAI(api_key=api_key, base_url=base_url)
    kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": preset.get("temperature", 0.7),
        "max_tokens": preset.get("max_tokens", 150),
        "presence_penalty": preset.get("presence_penalty", 0.0),
        "frequency_penalty": preset.get("frequency_penalty", 0.0),
        "stream": stream,
    }
    if preset.get("stop"):
        kwargs["stop"] = preset["stop"]
    safe_kwargs = {k: v for k, v in kwargs.items() if k != "messages"}
    logger.info(f"[LLM] Request kwargs (excluding messages): {safe_kwargs}")
    try:
        if stream:
            response = client.chat.completions.create(**kwargs)
            logger.info("[LLM] Stream connection established. Waiting for chunks...")
            def response_generator():
                chunk_count = 0
                for chunk in response:
                    chunk_count += 1
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta.content
                        if delta is not None:
                            if delta:
                                yield delta
                        else:
                            if chunk_count <= 5:
                                logger.info(f"[LLM] Chunk {chunk_count} has no delta content (None).")
                    else:
                        if chunk_count <= 5:
                            logger.info(f"[LLM] Chunk {chunk_count} has no choices.")
                logger.info(f"[LLM] Stream completed. Total chunks received: {chunk_count}")
            return response_generator()
        else:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            logger.info(f"[LLM] Non-stream response received. Length: {len(content) if content else 0}")
            return content
    except Exception as e:
        logger.error(f"[LLM] API Request failed: {e}")
        raise e