import json
import urllib.request
import urllib.error
import sys

URL = "http://127.0.0.1:5000/api/characters/test-draft"

def send_request(payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = {"detail": e.reason}
        return e.code, err_body
    except Exception as e:
        return 0, {"detail": str(e)}

def main():
    print("====================================================")
    print("       TESTING EPHEMERAL /test-draft ENDPOINT       ")
    print("====================================================\n")

    # 1. Prepare a valid schema representation of Jan Žižka
    valid_payload = {
        "user_input": "How do we build wagon forts to defeat royalists?",
        "session_state": {
            "active_node_id": "node_welcome_idx",
            "history": [
                {"role": "assistant", "content": "Welcome stranger. I am Žižka. State your allegiance."}
            ]
        },
        "draft_config": {
            "info": {
                "name": "Jan Žižka",
                "description": "Bohemian military commander and Hussite leader."
            },
            "prompts": {
                "base_prompt": "You are Jan Žižka, the Hussite military commander. Speak with 15th-century veteran gravitas.",
                "do": [
                    "Speak with historical authenticity.",
                    "Keep answers short under 40 words."
                ],
                "don't": [
                    "Break character or refer to modern times.",
                    "Answering off-topic requests."
                ],
                "context": {
                    "setting": "Inside an armed military camp near Prague, 1420.",
                    "personality": "Tactical, stern, and uncompromising.",
                    "background": "The Hussite Wars have begun."
                },
                "var_prompt": [
                    {
                        "id": "welcome",
                        "displayName": "Welcome Guest",
                        "node_class": "prompt",
                        "type": "advanced",
                        "goal": "Greet the guest and ask their business.",
                        "tone": "Cautioned",
                        "ext_info": "fetch",  # Triggers RAG search lookup
                        "next": []
                    }
                ]
            },
            "layout": {
                "nodes": [
                    {
                        "id": "node_welcome_idx",
                        "label": "welcome",
                        "node_class": "prompt",
                        "type": "advanced",
                        "position": {"x": 150, "y": 300},
                        "data": {}
                    }
                ],
                "connections": []
            }
        }
    }

    print("[TEST 1] Sending valid payload...")
    status, response = send_request(valid_payload)
    print(f"Status Code: {status}")
    if status == 200:
        print("[SUCCESS] Received generation pipeline result:")
        print(f"  Response: {response.get('text')}")
        print(f"  Next Node ID: '{response.get('next_node_id')}'")
        chunks = response.get("retrieved_chunks", [])
        print(f"  Retrieved Chunks Count: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            print(f"    Chunk {i}: {chunk.get('text')}")
    else:
        print(f"[FAILED] Error response: {response}")
        sys.exit(1)

    print("\n----------------------------------------------------\n")

    # 2. Prepare an invalid payload missing required fields (Do's and Don'ts)
    invalid_payload = {
        "user_input": "Test query",
        "session_state": {},
        "draft_config": {
            "info": {
                "name": "Incomplete Profile",
                "description": "Missing critical parameters."
            },
            "prompts": {
                "base_prompt": "Some guidelines",
                "do": [],     # Empty (Required field)
                "don't": []   # Empty (Required field)
            }
        }
    }

    print("[TEST 2] Sending invalid payload (testing validation constraints)...")
    status, response = send_request(invalid_payload)
    print(f"Status Code: {status}")
    if status == 422:
        print(f"[SUCCESS] Server rejected payload with expected 422 status.")
        print(f"  Validation Error Detail: {response.get('detail')}")
    else:
        print(f"[FAILED] Server returned status {status} instead of 422. Response: {response}")
        sys.exit(1)

    print("\n====================================================")
    print("      ALL DRAFT ENDPOINT TESTS PASSED SUCCESS       ")
    print("====================================================")

if __name__ == "__main__":
    main()