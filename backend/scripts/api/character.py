import os
import json
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from ruamel.yaml import YAML

# Define assets directories relative to backend root
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BACKEND_DIR, "assets")
CHARACTERS_DIR = os.path.join(ASSETS_DIR, "characters")
RAG_SCHEMES_DIR = os.path.join(ASSETS_DIR, "rag_schemes")

router = APIRouter()

def get_yaml_parser():
    yaml = YAML(typ='rt')  # Round-trip preserves comments and ordering
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # High width to avoid line wrapping

    # Custom representer for block-style strings
    def represent_literal_string(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    yaml.Representer.add_representer(str, represent_literal_string)
    return yaml

def init_assets():
    os.makedirs(CHARACTERS_DIR, exist_ok=True)
    os.makedirs(RAG_SCHEMES_DIR, exist_ok=True)

    example_dir = os.path.join(CHARACTERS_DIR, "example")
    if not os.path.exists(example_dir):
        os.makedirs(example_dir, exist_ok=True)

        # Default info.json
        info_data = {
            "id": "example",
            "name": "Example Character",
            "description": "An example blueprint character.",
            "tags": ["RAG", "Historical"],
            "language": "en",
            "color": "#4caf50",
            "avatar": "/api/characters/item/example/avatar",
            "idle_timeout_seconds": 300,
            "rag": {
                "ragScheme": "example_scheme",
                "pov": "example_pov",
                "chunksize": 4
            }
        }
        with open(os.path.join(example_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info_data, f, indent=2)

        # Default prompts.yaml
        prompts_yaml_content = """# Character Prompts Configuration
base_prompt: |
  You are an example character. Speak with clarity. Keep answers short (max 40 words).
do:
  - Speak with clarity.
don't:
  - Break character.
context:
  setting: "An empty room."
  personality: "Helpful and concise."
  background: "Created as an illustrative blueprint."
  role: "Demonstrate character features."
var_prompt:
  - id: start
    displayName: Start Session
    node_class: flow
    type: start-node
    next: [target: welcome]
  - id: welcome
    displayName: Welcome Guest
    node_class: prompt
    type: advanced
    goal: "Greet the stranger warmly."
    tone: "Friendly"
    example: "Hello! I am an example character. How can I help you today?"
    follow_up: "What would you like to discuss?"
    ext_info: "disabled"
    need_answer: true
    next: []
"""
        with open(os.path.join(example_dir, "prompts.yaml"), "w", encoding="utf-8") as f:
            f.write(prompts_yaml_content)

        # Default layout.json
        layout_data = {
            "nodes": [
                {
                    "id": "node_start_idx",
                    "label": "start",
                    "node_class": "flow",
                    "type": "start-node",
                    "position": { "x": 150, "y": 100 },
                    "data": {}
                },
                {
                    "id": "node_welcome_idx",
                    "label": "welcome",
                    "node_class": "prompt",
                    "type": "advanced",
                    "position": { "x": 150, "y": 300 },
                    "data": {}
                }
            ],
            "connections": [
                {
                    "id": "conn_01",
                    "source": "node_start_idx",
                    "sourceOutput": "out",
                    "target": "node_welcome_idx",
                    "targetInput": "in",
                    "data": { "label": "" }
                }
            ]
        }
        with open(os.path.join(example_dir, "layout.json"), "w", encoding="utf-8") as f:
            json.dump(layout_data, f, indent=2)

init_assets()

@router.get("")
async def list_characters():
    characters = []
    if not os.path.exists(CHARACTERS_DIR):
        return characters

    for folder in os.listdir(CHARACTERS_DIR):
        folder_path = os.path.join(CHARACTERS_DIR, folder)
        if os.path.isdir(folder_path):
            info_file = os.path.join(folder_path, "info.json")
            if os.path.exists(info_file):
                try:
                    with open(info_file, "r", encoding="utf-8") as f:
                        characters.append(json.load(f))
                except Exception:
                    pass
    return characters

@router.get("/item/{char_id}")
async def get_character(char_id: str):
    char_dir = os.path.join(CHARACTERS_DIR, char_id)
    if not os.path.exists(char_dir):
        raise HTTPException(status_code=404, detail="Character not found")

    info_file = os.path.join(char_dir, "info.json")
    prompts_file = os.path.join(char_dir, "prompts.yaml")
    layout_file = os.path.join(char_dir, "layout.json")

    info_data = {}
    prompts_data = {}
    layout_data = {}

    if os.path.exists(info_file):
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                info_data = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read info.json: {str(e)}")

    if os.path.exists(prompts_file):
        try:
            yaml = get_yaml_parser()
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts_data = yaml.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse prompts.yaml: {str(e)}")

    if os.path.exists(layout_file):
        try:
            with open(layout_file, "r", encoding="utf-8") as f:
                layout_data = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read layout.json: {str(e)}")

    return {
        "info": info_data,
        "prompts": prompts_data,
        "layout": layout_data
    }

@router.post("/item/{char_id}")
async def save_character(char_id: str, payload: dict):
    char_dir = os.path.join(CHARACTERS_DIR, char_id)
    os.makedirs(char_dir, exist_ok=True)

    info_data = payload.get("info", {})
    prompts_data = payload.get("prompts", {})
    layout_data = payload.get("layout", {})

    if "id" not in info_data:
        info_data["id"] = char_id

    info_file = os.path.join(char_dir, "info.json")
    prompts_file = os.path.join(char_dir, "prompts.yaml")
    layout_file = os.path.join(char_dir, "layout.json")

    try:
        temp_info_file = info_file + ".tmp"
        with open(temp_info_file, "w", encoding="utf-8") as f:
            json.dump(info_data, f, indent=2)

        temp_layout_file = layout_file + ".tmp"
        with open(temp_layout_file, "w", encoding="utf-8") as f:
            json.dump(layout_data, f, indent=2)

        temp_prompts_file = prompts_file + ".tmp"
        yaml = get_yaml_parser()
        with open(temp_prompts_file, "w", encoding="utf-8") as f:
            yaml.dump(prompts_data, f)

        os.replace(temp_info_file, info_file)
        os.replace(temp_layout_file, layout_file)
        os.replace(temp_prompts_file, prompts_file)

    except Exception as e:
        for file_path in [info_file + ".tmp", layout_file + ".tmp", prompts_file + ".tmp"]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        raise HTTPException(status_code=500, detail=f"Failed to write configuration files: {str(e)}")

    return {"status": "success", "message": "Character saved successfully"}

@router.get("/item/{char_id}/avatar")
async def get_avatar(char_id: str):
    char_dir = os.path.join(CHARACTERS_DIR, char_id)
    if not os.path.exists(char_dir):
        raise HTTPException(status_code=404, detail="Character not found")

    avatar_file = os.path.join(char_dir, "avatar.png")
    if os.path.exists(avatar_file):
        return FileResponse(avatar_file)

    raise HTTPException(status_code=404, detail="Avatar image not found")

@router.post("/item/{char_id}/avatar")
async def upload_avatar(char_id: str, file: UploadFile = File(...)):
    char_dir = os.path.join(CHARACTERS_DIR, char_id)
    if not os.path.exists(char_dir):
        raise HTTPException(status_code=404, detail="Character not found")

    avatar_file = os.path.join(char_dir, "avatar.png")
    try:
        with open(avatar_file, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save avatar image: {str(e)}")

    return {"status": "success", "url": f"/api/characters/item/{char_id}/avatar"}

@router.get("/test-serialization")
async def test_serialization():
    mock_id = "mock_character"
    mock_dir = os.path.join(CHARACTERS_DIR, mock_id)
    example_dir = os.path.join(CHARACTERS_DIR, "example")

    if os.path.exists(mock_dir):
        shutil.rmtree(mock_dir)

    try:
        shutil.copytree(example_dir, mock_dir)

        yaml = get_yaml_parser()
        prompts_file = os.path.join(mock_dir, "prompts.yaml")

        with open(prompts_file, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        data["base_prompt"] = "Line 1 of updated prompt.\nLine 2 of updated prompt.\n"
        data["do"].append("Follow new instructions.")

        with open(prompts_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        with open(prompts_file, "r", encoding="utf-8") as f:
            updated_content = f.read()

        has_literal_marker = "base_prompt: |" in updated_content

        return {
            "status": "success",
            "has_literal_marker": has_literal_marker,
            "raw_content": updated_content
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": f"Serialization check failed: {str(e)}"}
        )