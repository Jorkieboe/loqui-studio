import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.core.session_manager import ChatSession
from scripts.core.intent_dispatcher import build_intent_tools, evaluate_intent

def test_tool_generation():
    print("[1/3] Testing dynamic tool schema construction from reactive nodes...")
    reactive_nodes = [
        {
            "id": "reactive_dining",
            "mode": "flow",
            "flow_label": "dinner & restaurants",
            "trigger_intent": "User asks about local dining, food, or breakfast."
        },
        {
            "id": "reactive_deflect",
            "mode": "standalone",
            "trigger_intent": "User brings up modern tech or AI."
        }
    ]
    # Simulate dining flow being in open_topics
    open_topics = [{"flow_id": "reactive_dining", "flow_label": "dinner & restaurants", "paused_node_id": "node_pizza"}]

    tools = build_intent_tools(reactive_nodes, open_topics=open_topics)
    tool_names = [t["function"]["name"] for t in tools]

    # Only reactive node tools and the single fallback tool should exist
    assert "reactive_dining" in tool_names, "Missing reactive_dining tool"
    assert "reactive_deflect" in tool_names, "Missing reactive_deflect tool"
    assert "resume_current_flow" in tool_names, "Missing resume_current_flow fallback tool"
    assert "resume_open_topic" not in tool_names, "resume_open_topic should not be a separate tool"

    dining_tool = next(t for t in tools if t["function"]["name"] == "reactive_dining")
    # Verify description incorporates resumption when shelved in open_topics
    assert "dinner & restaurants" in dining_tool["function"]["description"]
    print("  ✓ Dynamic tool schemas constructed accurately with unified resumption descriptions.")

def test_intent_dispatcher():
    print("[2/3] Testing intent dispatcher matching with last 3 history responses...")
    reactive_nodes = [
        {
            "id": "reactive_dining",
            "mode": "flow",
            "flow_label": "dinner & restaurants",
            "trigger_intent": "User asks about local dining, food, or breakfast."
        },
        {
            "id": "reactive_deflect",
            "mode": "standalone",
            "trigger_intent": "User brings up modern tech or AI."
        }
    ]

    # Context of last 3 turns
    history = [
        {"role": "user", "content": "Hi there!"},
        {"role": "assistant", "content": "Welcome to our Haarlem BnB!"},
        {"role": "user", "content": "Can we check in early?"},
        {"role": "assistant", "content": "Yes, around 2 PM is fine."},
        {"role": "user", "content": "Great, thanks."},
        {"role": "assistant", "content": "Anything else you need right now?"}
    ]

    # 1. Standard flow continuation -> resume_current_flow
    intent = evaluate_intent(
        user_input="No, that was all for check-in. Tell me about the house rules.",
        history=history,
        reactive_nodes=reactive_nodes,
        active_flow="main",
        open_topics=[]
    )
    assert intent == "resume_current_flow", f"Expected resume_current_flow, got {intent}"
    print("  ✓ Correctly evaluated 'resume_current_flow'")

    # 2. Reactive flow trigger -> reactive node tool name
    intent = evaluate_intent(
        user_input="Where can we get good Italian pasta tonight?",
        history=history,
        reactive_nodes=reactive_nodes,
        active_flow="main",
        open_topics=[]
    )
    assert intent == "reactive_dining", f"Expected reactive_dining, got {intent}"
    print("  ✓ Correctly evaluated 'reactive_dining' tool call")

def test_bridge_directive_assembly():
    print("[3/3] Testing bridge directive generation with open topics...")
    from scripts.core.orchestrator import assemble_bridge_directive

    open_topics = [{"flow_id": "reactive_dining", "flow_label": "dinner & restaurants", "paused_node_id": "node_pizza"}]
    directive = assemble_bridge_directive(open_topics)
    assert "dinner & restaurants" in directive
    assert any(term in directive.lower() for term in ["return", "resume", "ask", "previous"])
    print("  ✓ Bridge directive generated correctly with shelved topic context.")

if __name__ == "__main__":
    print("=== PHASE 2 TEST RUNNER ===")
    test_tool_generation()
    test_intent_dispatcher()
    test_bridge_directive_assembly()
    print("=== ALL PHASE 2 CHECKS PASSED ===\n")