import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.core.session_manager import ChatSession, SessionManager
from scripts.api.character import get_yaml_parser

def test_session_state():
    print("[1/2] Testing ChatSession models...")
    session = ChatSession()
    assert hasattr(session, "active_flow_id"), "ChatSession missing active_flow_id"
    assert hasattr(session, "open_topics"), "ChatSession missing open_topics"
    assert session.active_flow_id == "main"
    assert isinstance(session.open_topics, list)
    print("  ✓ ChatSession state attributes verified.")

def test_yaml_serialization():
    print("[2/2] Testing YAML serialization for reactive & bridge nodes...")
    yaml = get_yaml_parser()
    sample_config = {
        "var_prompt": [
            {
                "id": "reactive_dining",
                "node_class": "reactive",
                "mode": "flow",
                "trigger_intent": "User asks about local dining, food, or breakfast.",
                "flow_label": "dining & restaurants",
                "next": [{"target": "bridge_dining"}]
            },
            {
                "id": "reactive_deflect",
                "node_class": "reactive",
                "mode": "standalone",
                "trigger_intent": "User brings up modern tech.",
                "flow_label": "deflect",
                "goal": "Express confusion.",
                "next": []
            },
            {
                "id": "bridge_dining",
                "node_class": "flow",
                "type": "bridge-node",
                "goal": "Wrap up dining advice and check on previous topics.",
                "next": []
            }
        ]
    }

    # Test dump and load
    from io import StringIO
    stream = StringIO()
    yaml.dump(sample_config, stream)
    dumped_str = stream.getvalue()

    assert "node_class: reactive" in dumped_str
    assert "type: bridge-node" in dumped_str
    assert "trigger_intent: User asks about local dining" in dumped_str

    loaded = yaml.load(dumped_str)
    assert len(loaded["var_prompt"]) == 3
    assert loaded["var_prompt"][0]["mode"] == "flow"
    assert loaded["var_prompt"][1]["mode"] == "standalone"
    print("  ✓ Serialization round-trip successful.")

if __name__ == "__main__":
    print("=== PHASE 1 TEST RUNNER ===")
    test_session_state()
    test_yaml_serialization()
    print("=== ALL PHASE 1 CHECKS PASSED ===\n")