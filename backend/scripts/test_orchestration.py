import os
import sys
import asyncio
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Load environment variables from standard locations
load_dotenv()
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from scripts.api.character import get_character
from scripts.core.orchestrator import run_dialogue_pipeline

async def test_run():
    print("=========================================")
    print("   LOQUI STUDIO ORCHESTRATION TEST RUNNER   ")
    print("=========================================\n")

    char_id = "example"
    print(f"[TEST] Loading character '{char_id}'...")
    try:
        char_data = await get_character(char_id)
        print("[TEST] Character config loaded successfully.\n")
    except Exception as e:
        print(f"[ERROR] Failed to load character config: {e}")
        return

    print("[TEST] Step 1: Traversing from 'start' node with user input...")
    user_msg = "Hello! Tell me who you are."
    active_node = "node_start_idx"
    history = []

    print(f"User query: '{user_msg}'")
    print(f"Current node: '{active_node}'")

    pipeline_result = run_dialogue_pipeline(
        user_input=user_msg,
        active_node_id=active_node,
        history=history,
        character_config=char_data
    )

    next_node_id = pipeline_result["next_node_id"]
    print(f"\n[TEST] Traversed successfully to Node ID: '{next_node_id}'")

    print("\n[TEST] Streaming model output response:")
    print("-----------------------------------------")
    for chunk in pipeline_result["response_stream"]:
        sys.stdout.write(chunk)
        sys.stdout.flush()
    print("\n-----------------------------------------")

    print("\n[TEST] Step 2: Simulating RAG retrieval on wagon fort tactics...")
    hussite_config = {
        "info": {
            "id": "hussite_test",
            "rag": {
                "ragScheme": "hussite_wars",
                "pov": "hussite_commander",
                "chunksize": 2
            }
        },
        "prompts": {
            "base_prompt": "You are a Hussite veteran campaign commander.",
            "do": ["Speak with pride."],
            "don't": ["Mention modern times."],
            "context": {
                "setting": "Bohemia, 1420"
            },
            "var_prompt": [
                {
                    "id": "discuss_tactics",
                    "ext_info": "fetch",
                    "goal": "Explain how you use standard carts as wagon forts.",
                    "tone": "Proud"
                }
            ]
        },
        "layout": {
            "nodes": [
                {"id": "node_tactics_idx", "label": "discuss_tactics", "type": "advanced"}
            ],
            "connections": []
        }
    }

    rag_query = "How do we build wagon forts?"
    print(f"RAG query: '{rag_query}'")

    pipeline_result_rag = run_dialogue_pipeline(
        user_input=rag_query,
        active_node_id="node_tactics_idx",
        history=history,
        character_config=hussite_config
    )

    print("\n[TEST] Retrieved Grounded RAG Chunks:")
    chunks = pipeline_result_rag["retrieved_chunks"]
    if chunks:
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}: {chunk['text']} [POV: {chunk.get('pov')}]")
        print(f"  Metadata Categories parsed: {pipeline_result_rag['metadata_categories']}")
    else:
        print("  (No chunks found.)")

    print("\n[TEST] Streaming grounded model output response:")
    print("-----------------------------------------")
    for chunk in pipeline_result_rag["response_stream"]:
        sys.stdout.write(chunk)
        sys.stdout.flush()
    print("\n-----------------------------------------")
    print("\n[TEST] Orchestration verification complete.")

if __name__ == "__main__":
    asyncio.run(test_run())