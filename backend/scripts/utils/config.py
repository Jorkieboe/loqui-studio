import os
import json
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BACKEND_DIR, "config.json")
ASSETS_DIR = os.path.join(BACKEND_DIR, "assets")
CHARACTERS_DIR = os.path.join(ASSETS_DIR, "characters")
RAG_SCHEMES_DIR = os.path.join(ASSETS_DIR, "rag_schemes")

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_project_env() -> None:
    load_dotenv()
    load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))

def is_dev_mode() -> bool:
    env_val = os.environ.get("DEV_MODE")
    if env_val is not None:
        return env_val.strip().lower() in ("1", "true", "yes", "on")
    if os.path.exists(CONFIG_PATH):
        try:
            cfg = load_config()
            if "dev_mode" in cfg:
                return bool(cfg["dev_mode"])
        except Exception:
            pass
    return False

def format_error_for_client(detailed_message: str, generic_message: str) -> str:
    if is_dev_mode():
        return detailed_message
    return generic_message