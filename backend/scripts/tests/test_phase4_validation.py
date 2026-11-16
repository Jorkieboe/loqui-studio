import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.core.validation import validate_character_graph

def test_graph_validation():
    print("[1/2] Testing graph crawler (missing bridge)...")
    invalid_graph = {
        "var_prompt": [
            {
                "id": "reactive_dining",
                "node_class": "reactive",
                "mode": "flow",
                "displayName": "Dining Flow",
                "next": [{"target": "node_pizza"}]
            },
            {
                "id": "node_pizza",
                "node_class": "prompt",
                "displayName": "Pizza Recs",
                "next": []  # Missing bridge node
            }
        ]
    }

    errors = validate_character_graph(invalid_graph)
    assert any("must end with a connected Bridge node" in err for err in errors), \
        f"Validation failed to catch unbridged reactive flow. Errors: {errors}"
    print("  ✓ Correctly rejected unbridged reactive flow.")

    print("[2/2] Testing graph crawler (properly bridged flow)...")
    valid_graph = {
        "var_prompt": [
            {
                "id": "reactive_dining",
                "node_class": "reactive",
                "mode": "flow",
                "displayName": "Dining Flow",
                "next": [{"target": "node_pizza"}]
            },
            {
                "id": "node_pizza",
                "node_class": "prompt",
                "displayName": "Pizza Recs",
                "next": [{"target": "bridge_dining"}]
            },
            {
                "id": "bridge_dining",
                "node_class": "flow",
                "type": "bridge-node",
                "displayName": "Bridge Dining",
                "next": []
            }
        ]
    }
    errors = validate_character_graph(valid_graph)
    flow_errors = [e for e in errors if "Bridge node" in e]
    assert len(flow_errors) == 0, f"Expected valid graph, got errors: {flow_errors}"
    print("  ✓ Successfully approved properly bridged reactive flow.")

if __name__ == "__main__":
    print("=== PHASE 4 TEST RUNNER ===")
    test_graph_validation()
    print("=== ALL PHASE 4 CHECKS PASSED ===\n")