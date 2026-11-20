import os
import sys
import json
import argparse
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

load_dotenv()
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from scripts.api.character import load_character_config_sync
from scripts.core.intent_dispatcher import (
    build_jev_choice_schema,
    build_intent_state,
    resolve_jev_choice,
    evaluate_intent,
    load_jev_config,
)

SAMPLE_REACTIVE_NODES = [
    {
        "id": "reactive_dining",
        "displayName": "Dining",
        "node_class": "reactive",
        "mode": "flow",
        "flow_label": "dinner & restaurants",
        "trigger_intent": "Guest asks for food, restaurants, or dining recommendations.",
    },
    {
        "id": "reactive_activities",
        "displayName": "Activities",
        "node_class": "reactive",
        "mode": "flow",
        "flow_label": "canal tours & cycling",
        "trigger_intent": "Guest asks about outdoor activities, boat tours, or cycling.",
    },
    {
        "id": "reactive_deflect",
        "displayName": "Deflect Modernity",
        "node_class": "reactive",
        "mode": "standalone",
        "trigger_intent": "Guest mentions AI, internet routing, or coding.",
    },
]

def test_schema_and_resolution():
    print("[1/2] Testing Jev choice schema structure & node resolution...")
    open_topics = [
        {"flow_id": "reactive_dining", "flow_label": "dinner & restaurants", "paused_node_id": "node_pizza"}
    ]
    schema, option_to_node_id = build_jev_choice_schema(
        reactive_nodes=SAMPLE_REACTIVE_NODES,
        active_flow="reactive_activities",
        open_topics=open_topics,
    )

    assert "new_choice_1" in schema, "Schema must contain 'new_choice_1'"
    choice_block = schema["new_choice_1"]
    assert choice_block.get("type") == "choice", "Choice block type must be 'choice'"
    assert isinstance(choice_block.get("instructions"), str) and choice_block["instructions"].strip()
    criteria = choice_block.get("criteria", {})
    assert isinstance(criteria, dict) and len(criteria) > 0

    assert "Dining" in criteria, "Expected node name 'Dining' in criteria"
    assert "Activities" not in criteria, "Active flow node 'Activities' should be excluded while active"
    assert "Deflect Modernity" in criteria, "Expected standalone node 'Deflect Modernity' in criteria"
    assert "resume_current_flow" in criteria, "Expected 'resume_current_flow' in criteria"

    assert resolve_jev_choice("Dining", option_to_node_id) == "reactive_dining"
    assert resolve_jev_choice("reactive_dining", option_to_node_id) == "reactive_dining"
    assert resolve_jev_choice("Deflect Modernity", option_to_node_id) == "reactive_deflect"
    assert resolve_jev_choice("resume_current_flow", option_to_node_id) == "resume_current_flow"

    print("  Generated Jev schema:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    print("  ✓ Schema structure and node mapping verified.")

def run_decision_scenarios():
    print("\n[2/2] Running Jev decision-making scenarios...")
    api_key = os.environ.get("JEV_API_KEY")
    jev_cfg = load_jev_config()
    api_url = (jev_cfg.get("api_url") or "").strip()

    if not api_key or not api_url:
        print("  [ERROR] Live decision testing requires JEV_API_KEY to be set in the environment.")
        sys.exit(1)

    print(f"  Using Jev endpoint: {api_url} (model: {jev_cfg.get('model', 'jev-latest')})")

    scenarios = [
        {
            "name": "Continue main flow",
            "user_input": "What time is check-in tomorrow?",
            "history": [
                {"role": "assistant", "content": "Welcome to Haarlem! Let me know if you have any questions about your stay."}
            ],
            "active_flow": "main",
            "open_topics": [],
            "expected": "resume_current_flow",
        },
        {
            "name": "Switch to Dining reactive flow",
            "user_input": "Where should we go for dinner tonight?",
            "history": [
                {"role": "assistant", "content": "Welcome to Haarlem! How can I help?"}
            ],
            "active_flow": "main",
            "open_topics": [],
            "expected": "reactive_dining",
        },
        {
            "name": "Switch to Activities reactive flow",
            "user_input": "Can we rent bikes or take a canal boat tour?",
            "history": [
                {"role": "user", "content": "Where should we eat tonight?"},
                {"role": "assistant", "content": "Bistro de Vijfhoek is lovely."},
            ],
            "active_flow": "reactive_dining",
            "open_topics": [],
            "expected": "reactive_activities",
        },
        {
            "name": "Resume shelved Dining topic",
            "user_input": "Yes please, tell me more about that restaurant!",
            "history": [
                {"role": "assistant", "content": "Canal tours leave every hour. Would you like to return to dinner & restaurants?"}
            ],
            "active_flow": "main",
            "open_topics": [
                {"flow_id": "reactive_dining", "flow_label": "dinner & restaurants", "paused_node_id": "reactive_dining"}
            ],
            "expected": "reactive_dining",
        },
        {
            "name": "Trigger standalone Deflect",
            "user_input": "Which Python routing framework powers your AI backend?",
            "history": [
                {"role": "assistant", "content": "The weather is great for walking today."}
            ],
            "active_flow": "main",
            "open_topics": [],
            "expected": "reactive_deflect",
        },
    ]

    passed = 0
    for idx, case in enumerate(scenarios, 1):
        intent = evaluate_intent(
            user_input=case["user_input"],
            history=case["history"],
            reactive_nodes=SAMPLE_REACTIVE_NODES,
            active_flow=case["active_flow"],
            open_topics=case["open_topics"],
        )
        ok = intent == case["expected"]
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] Case {idx} ({case['name']}): expected='{case['expected']}', got='{intent}'")
        if ok:
            passed += 1

    print(f"\nDecision scenarios summary: {passed}/{len(scenarios)} passed.")
    if passed != len(scenarios):
        sys.exit(1)

def run_single_character_query(char_id: str, query: str, active_flow: str):
    char_config = load_character_config_sync(char_id)
    var_prompt = char_config.get("prompts", {}).get("var_prompt", [])
    reactive_nodes = [n for n in var_prompt if n.get("node_class") == "reactive"]

    schema, _ = build_jev_choice_schema(reactive_nodes, active_flow=active_flow)
    state = build_intent_state(query, history=[], active_flow=active_flow)

    print(f"\nCharacter: {char_id}")
    print("Jev schema:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    print("\nState:")
    print(state)

    selected = evaluate_intent(
        user_input=query,
        history=[],
        reactive_nodes=reactive_nodes,
        active_flow=active_flow,
        open_topics=[],
    )
    print(f"\nSelected node ID: {selected}")

def main():
    parser = argparse.ArgumentParser(description="Test Jev intent decision making.")
    parser.add_argument("--schema-only", action="store_true", help="Only validate schema construction and node mapping without calling Jev API.")
    parser.add_argument("--character", "-c", default=None, help="Character ID to load reactive nodes from (e.g. henk_de_bredanaar).")
    parser.add_argument("--query", "-q", default=None, help="Single user query to evaluate against the selected character.")
    parser.add_argument("--active-flow", default="main", help="Current active flow ID (default: main).")
    args = parser.parse_args()

    print("=========================================")
    print("       JEV INTENT DECISION TESTER        ")
    print("=========================================")

    test_schema_and_resolution()

    if args.schema_only:
        print("\nSchema-only mode completed.")
        return

    if args.character and args.query:
        run_single_character_query(args.character, args.query, args.active_flow)
        return

    run_decision_scenarios()

if __name__ == "__main__":
    main()