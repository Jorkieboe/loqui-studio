import os
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BACKEND_DIR, "config.json")
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def load_ollama_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("ollama", {
                    "enabled": True,
                    "host": "http://127.0.0.1:11434",
                    "llm_model": "llama3",
                    "embedding_model": "nomic-embed-text"
                })
        except Exception as e:
            logger.error(f"Failed to load ollama config: {e}")
    return {
        "enabled": True,
        "host": "http://127.0.0.1:11434",
        "llm_model": "llama3",
        "embedding_model": "nomic-embed-text"
    }

def is_ollama_available() -> bool:
    try:
        config = load_ollama_config()
        host = config.get("host", OLLAMA_BASE_URL)
        req = urllib.request.Request(f"{host}/", method="GET")
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

def get_loaded_models() -> List[str]:
    try:
        config = load_ollama_config()
        host = config.get("host", OLLAMA_BASE_URL)
        req = urllib.request.Request(f"{host}/api/ps", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            models = res_data.get("models", [])
            loaded_names = []
            for m in models:
                name = m.get("name")
                if name:
                    loaded_names.append(name)
                    if name.endswith(":latest"):
                        loaded_names.append(name[:-7])
            return list(set(loaded_names))
    except Exception as e:
        logger.warning(f"[Ollama] Failed to query loaded models: {e}")
        return []

def unload_model(model_name: str) -> bool:
    try:
        config = load_ollama_config()
        host = config.get("host", OLLAMA_BASE_URL)
        url = f"{host}/api/generate"
        payload = {
            "model": model_name,
            "prompt": "",
            "keep_alive": 0
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
            logger.info(f"[Ollama] Unloaded model: {model_name}")
            return True
    except Exception as e:
        logger.warning(f"[Ollama] Failed to unload model {model_name}: {e}")
        return False

def load_model(model_name: str) -> bool:
    try:
        config = load_ollama_config()
        host = config.get("host", OLLAMA_BASE_URL)
        url = f"{host}/api/generate"
        payload = {
            "model": model_name,
            "prompt": "",
            "keep_alive": -1
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            response.read()
            logger.info(f"[Ollama] Preloaded model: {model_name}")
            return True
    except Exception as e:
        logger.warning(f"[Ollama] Failed to preload model {model_name}: {e}")
        return False

def manage_models(target_models: List[str] = None):
    config = load_ollama_config()
    if not config.get("enabled", True):
        return
    if target_models is None:
        models_to_preload = []
        if config.get("llm_enabled", True):
            models_to_preload.append(config.get("llm_model", "llama3"))
        if config.get("embedding_enabled", True):
            models_to_preload.append(config.get("embedding_model", "nomic-embed-text"))
        target_models = models_to_preload
    target_models = list(set([m for m in target_models if m]))
    loaded = get_loaded_models()
    logger.info(f"[Ollama] Currently loaded: {loaded} targets: {target_models}")
    normalized_targets = {t.lower() for t in target_models}
    normalized_targets_no_latest = {t.replace(":latest", "").lower() for t in target_models}
    for model in loaded:
        m_lower = model.lower()
        m_no_latest = m_lower.replace(":latest", "")
        if m_lower not in normalized_targets and m_no_latest not in normalized_targets_no_latest:
            logger.info(f"[Ollama] Target list does not contain '{model}', unloading")
            unload_model(model)
    for target in target_models:
        t_lower = target.lower()
        t_no_latest = t_lower.replace(":latest", "")
        is_loaded = False
        for loaded_model in loaded:
            lm_lower = loaded_model.lower()
            lm_no_latest = lm_lower.replace(":latest", "")
            if t_lower == lm_lower or t_no_latest == lm_no_latest:
                is_loaded = True
                break
        if not is_loaded:
            logger.info(f"[Ollama] Preloading target model '{target}'")
            load_model(target)