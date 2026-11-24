import os
import json
import urllib.request
from typing import Dict, Any, List
from dotenv import load_dotenv
import tiktoken
from openai import OpenAI
from scripts.utils.config import CONFIG_PATH, load_config
from scripts.utils.logger import PipelineLogger

load_dotenv()

def _is_preset_value_set(value: Any) -> bool:
    if value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0):
        return False
    return True

def load_preset_config(preset_name: str = "default") -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            config = load_config()
            return config.get("llm_presets", {}).get(preset_name, {})
        except Exception as e:
            PipelineLogger.error("Failed to load llm_presets config", e)
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
    model_name = preset.get("model") or "gpt-4o-mini"
    input_text = "".join([m.get("content", "") for m in messages])
    input_tokens = count_tokens(input_text, model_name)
    PipelineLogger.llm_status(f"Input token count calculated: {input_tokens}")
    from scripts.services.ollama_service import is_ollama_available, load_ollama_config
    ollama_cfg = load_ollama_config()
    ollama_active = ollama_cfg.get("llm_enabled", True) and is_ollama_available()
    base_url = None
    if ollama_active:
        host = ollama_cfg.get("host", "http://127.0.0.1:11434").rstrip("/")
        model_name = ollama_cfg.get("llm_model", "llama3")
        PipelineLogger.llm_status(f"Routing request to Ollama native chat API: {model_name} at {host}")
        url = f"{host}/api/chat"
        options = {}
        ollama_param_map = {
            "temperature": "temperature",
            "max_tokens": "num_predict",
            "presence_penalty": "presence_penalty",
            "frequency_penalty": "frequency_penalty",
            "stop": "stop",
        }
        for preset_key, ollama_key in ollama_param_map.items():
            val = preset.get(preset_key)
            if _is_preset_value_set(val):
                options[ollama_key] = val
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options
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
                        full_content = ""
                        for line in response:
                            if line:
                                decoded_line = line.decode("utf-8").strip()
                                if decoded_line:
                                    try:
                                        chunk_data = json.loads(decoded_line)
                                        delta = chunk_data.get("message", {}).get("content", "")
                                        chunk_count += 1
                                        if delta:
                                            full_content += delta
                                            yield delta
                                    except Exception as parse_err:
                                        PipelineLogger.error("Ollama Parse Error", parse_err)
                        PipelineLogger.llm_output("", is_end=True)
                        PipelineLogger.llm_status(f"Ollama Stream completed. Total chunks: {chunk_count}")
                    finally:
                        response.close()
                return response_generator()
            else:
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    content = res_data.get("message", {}).get("content", "")
                    PipelineLogger.llm_status(f"Ollama Non-stream response received. Length: {len(content) if content else 0}")
                    PipelineLogger.llm_output("", is_end=True)
                    return content
        except Exception as e:
            PipelineLogger.error("Ollama Request failed", e)
            raise e
    if not api_key:
        PipelineLogger.llm_status("OPENAI_API_KEY not found in environment and Ollama is not available. Using fallback simulator.")
        def mock_generator():
            sys_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
            if "BRIDGE DIRECTIVE:" in sys_msg:
                directive_part = sys_msg.split("BRIDGE DIRECTIVE:")[1].split("\n\n")[0].strip()
                fallback_response = f"[SIMULATION MODE] Bram here! That sounds great. {directive_part}"
            elif "- Goal:" in sys_msg:
                goal_part = sys_msg.split("- Goal:")[1].split("\n")[0].strip()
                fallback_response = f"[SIMULATION MODE] Bram here! {goal_part}"
            else:
                fallback_response = (
                    "[SIMULATION MODE] This is a simulated character response because no OPENAI_API_KEY was found in the environment and Ollama is not active. "
                    "Ensure your API keys or local Ollama instances are configured."
                )
            for word in fallback_response.split(" "):
                yield word + " "
            PipelineLogger.llm_output(fallback_response)
            PipelineLogger.llm_output("", is_end=True)
        return mock_generator() if stream else "Simulated response: OpenAI API Key not configured."
    PipelineLogger.llm_status(f"Routing request to OpenAI/Cloud model: {model_name}")
    client = OpenAI(api_key=api_key, base_url=base_url)
    kwargs = {
        "model": model_name,
        "messages": messages,
        "stream": stream,
    }
    for key, val in preset.items():
        if key in ("model", "messages", "stream"):
            continue
        if _is_preset_value_set(val):
            kwargs[key] = val
    safe_kwargs = {k: v for k, v in kwargs.items() if k != "messages"}
    PipelineLogger.llm_status("Request parameters initialized", safe_kwargs)
    try:
        if stream:
            response = client.chat.completions.create(**kwargs)
            PipelineLogger.llm_status("Stream connection established. Streaming response:")
            def response_generator():
                chunk_count = 0
                full_content = ""
                for chunk in response:
                    chunk_count += 1
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta.content
                        if delta is not None:
                            if delta:
                                full_content += delta
                                yield delta
                PipelineLogger.llm_output(full_content)
                PipelineLogger.llm_output("", is_end=True)
                PipelineLogger.llm_status(f"Stream completed. Total chunks received: {chunk_count}")
            return response_generator()
        else:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            PipelineLogger.llm_status(f"Non-stream response received. Length: {len(content) if content else 0}")
            PipelineLogger.llm_output(content)
            PipelineLogger.llm_output("", is_end=True)
            return content
    except Exception as e:
        PipelineLogger.error("API Request failed", e)
        raise e