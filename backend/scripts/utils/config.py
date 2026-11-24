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