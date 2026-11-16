Here is the revised plan with **concrete, runnable test scripts** assigned to each checkpoint. You can run each script directly (via `go.bat cmd`) to verify and confirm functionality before proceeding to the next phase.

---

### Test Script Directory Structure
We will place all verification scripts in `backend/scripts/tests/`:
```text
backend/scripts/tests/
├── test_phase1_schemas.py      # Tests serialization of reactive & bridge nodes
├── test_phase2_dispatcher.py   # Tests intent evaluation, open topics stack & bridge prompt
├── test_phase4_validation.py   # Tests graph validation (enforcing bridge node connection)
└── test_phase5_e2e_bnb.py      # End-to-end multi-turn simulation of the BnB host
```

---

## Updated Implementation Plan & Test Scripts

### Phase 1: Data Schemas & State Models
- [x] **1.1. Update `ChatSession` Model (`backend/scripts/core/session_manager.py`)**
  - Add `active_flow_id: Optional[str] = "main"`
  - Add `open_topics: List[Dict[str, Any]] = []`
- [x] **1.2. Update Node Schemas (`backend/scripts/api/character.py`)**
  - Support `reactive` nodes (`mode: "flow" | "standalone"`, `trigger_intent`, `flow_label`).
  - Support `bridge-node` (`type: "bridge-node"`, `goal`).

---

#### 🛑 TEST CHECKPOINT 1
**Run command:**
```bash
python backend/scripts/tests/test_phase1_schemas.py
```

**Script Implementation: `backend/scripts/tests/test_phase1_schemas.py`**
```python
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
```

---

### Phase 2: Intent Dispatcher & Routing Engine
- [ ] **2.1. Implement Intent Dispatcher (`backend/scripts/core/intent_dispatcher.py`)**
  - Function `evaluate_intent()` with actions: `resume_current_flow`, `resume_open_topic`, and `trigger_reactive_<id>`.
- [ ] **2.2. Integrate Dispatcher into Pipeline (`backend/scripts/core/orchestrator.py`)**
  - Manage pushing/popping of `open_topics` on sub-flow entry.
  - Keep standalone reactive nodes one-shot without touching topic memory.
- [ ] **2.3. Implement Bridge Context Injection (`backend/scripts/core/orchestrator.py`)**
  - Inject conversational bridge directive when current node is `bridge-node`.

---

#### 🛑 TEST CHECKPOINT 2
**Run command:**
```bash
python backend/scripts/tests/test_phase2_dispatcher.py
```

**Script Implementation: `backend/scripts/tests/test_phase2_dispatcher.py`**
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.core.session_manager import ChatSession
from scripts.core.intent_dispatcher import evaluate_intent

def test_intent_dispatcher():
    print("[1/3] Testing Intent Dispatcher matching...")
    reactive_nodes = [
        {
            "id": "reactive_restaurants",
            "mode": "flow",
            "trigger_intent": "Guest asks about places to eat, restaurants, or dining."
        },
        {
            "id": "reactive_deflect",
            "mode": "standalone",
            "trigger_intent": "Guest asks about smartphones, wifi, computers, or modern tech."
        }
    ]

    # 1. Test normal flow continuation
    intent = evaluate_intent(
        user_input="Sounds great, tell me more about this place.",
        active_flow="main",
        reactive_nodes=reactive_nodes,
        open_topics=[]
    )
    assert intent == "resume_current_flow", f"Expected resume_current_flow, got {intent}"
    print("  ✓ Matched 'resume_current_flow'")

    # 2. Test reactive flow trigger
    intent = evaluate_intent(
        user_input="Where can we get good Italian pasta tonight?",
        active_flow="main",
        reactive_nodes=reactive_nodes,
        open_topics=[]
    )
    assert intent == "trigger_reactive_restaurants", f"Expected trigger_reactive_restaurants, got {intent}"
    print("  ✓ Matched 'trigger_reactive_restaurants'")

    # 3. Test standalone trigger
    intent = evaluate_intent(
        user_input="Can you give me the wifi password for my smartphone?",
        active_flow="main",
        reactive_nodes=reactive_nodes,
        open_topics=[]
    )
    assert intent == "trigger_reactive_deflect", f"Expected trigger_reactive_deflect, got {intent}"
    print("  ✓ Matched 'trigger_reactive_deflect'")

def test_open_topics_stack():
    print("[2/3] Testing open topics memory stacking...")
    session = ChatSession()
    session.active_flow_id = "restaurants"
    session.current_node_id = "node_pasta"

    # Simulate pivoting to activities: Restaurants gets shelved
    session.open_topics.append({
        "flow_id": session.active_flow_id,
        "flow_label": "dining & restaurants",
        "paused_node_id": session.current_node_id
    })
    session.active_flow_id = "activities"
    session.current_node_id = "node_kayaking"

    assert len(session.open_topics) == 1
    assert session.open_topics[0]["flow_id"] == "restaurants"
    print("  ✓ Interrupted flow shelved into open_topics successfully.")

def test_bridge_directive_assembly():
    print("[3/3] Testing bridge directive generation...")
    from scripts.core.orchestrator import assemble_bridge_directive

    open_topics = [{"flow_label": "dinner & restaurants"}]
    directive = assemble_bridge_directive(open_topics)
    assert "dinner & restaurants" in directive
    assert "ask" in directive.lower()
    print("  ✓ Bridge directive generated correctly with open topic context.")

if __name__ == "__main__":
    print("=== PHASE 2 TEST RUNNER ===")
    test_intent_dispatcher()
    test_open_topics_stack()
    test_bridge_directive_assembly()
    print("=== ALL PHASE 2 CHECKS PASSED ===\n")
```

---

### Phase 3 & 4: Vue Flow Graph & Topology Validation
- [ ] **3.1. Build `ReactiveNode` Component (`frontend/src/components/GraphEditor.vue`)**
- [ ] **3.2. Build `BridgeNode` Component (`frontend/src/components/GraphEditor.vue`)**
- [ ] **3.3. Auto-Spawn Bridge on new Reactive Flow creation (`CharacterEditorView.vue`)**
- [ ] **4.1. Graph Topology Validation (`frontend/src/views/CharacterEditorView.vue` & Backend Validator)**
  - Ensure every `reactive` flow node can reach a connected `bridge-node`.

---

#### 🛑 TEST CHECKPOINT 3 & 4
**Run command:**
```bash
python backend/scripts/tests/test_phase4_validation.py
```

**Script Implementation: `backend/scripts/tests/test_phase4_validation.py`**
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.core.validation import validate_character_graph

def test_graph_validation():
    print("[1/2] Testing graph crawler (missing bridge)...")
    # Invalid: reactive flow has no bridge connected
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
                "next": []  # Dead end! No bridge node!
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
```

---

### Phase 5: Debug Telemetry & Full Multi-Turn Scenario
- [ ] **5.1. Update Debug Drawer (`frontend/src/components/TestChatPanel.vue`)**
- [ ] **5.2. Multi-Turn BnB Host Verification Script**

---

#### 🛑 TEST CHECKPOINT 5: Full Scenario Test
**Run command:**
```bash
python backend/scripts/tests/test_phase5_e2e_bnb.py
```

**Script Implementation: `backend/scripts/tests/test_phase5_e2e_bnb.py`**
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.core.orchestrator import run_dialogue_pipeline
from scripts.core.session_manager import ChatSession

def run_e2e_bnb_test():
    print("=== STARTING FULL BNB HOST INTERACTIVE SIMULATION ===")

    # 1. Setup BnB Host config with Main, Restaurant Flow, Activities Flow & Deflect
    bnb_config = {
        "info": {"name": "Host Bram", "description": "Friendly local BnB owner."},
        "prompts": {
            "base_prompt": "You are Bram, a warm local BnB host in Haarlem. You speak concisely and hospitably.",
            "do": ["Be welcoming", "Recommend local spots", "Speak warmly"],
            "don't": ["Break character", "Give long generic lists", "Ignore guest questions"],
            "var_prompt": [
                {
                    "id": "start",
                    "displayName": "Start",
                    "node_class": "flow",
                    "type": "start-node",
                    "next": [{"target": "welcome"}]
                },
                {
                    "id": "welcome",
                    "displayName": "Welcome",
                    "node_class": "prompt",
                    "goal": "Greet guest and offer help.",
                    "next": []
                },
                # Sub-flow 1: Restaurants
                {
                    "id": "reactive_dining",
                    "displayName": "Dining",
                    "node_class": "reactive",
                    "mode": "flow",
                    "flow_label": "dinner & restaurants",
                    "trigger_intent": "Guest asks for food, restaurants, or dining.",
                    "goal": "Recommend the local Bistro de Vijfhoek.",
                    "next": [{"target": "bridge_dining"}]
                },
                {
                    "id": "bridge_dining",
                    "displayName": "Bridge Dining",
                    "node_class": "flow",
                    "type": "bridge-node",
                    "goal": "Wrap up dining conversation.",
                    "next": []
                },
                # Sub-flow 2: Activities
                {
                    "id": "reactive_activities",
                    "displayName": "Activities",
                    "node_class": "reactive",
                    "mode": "flow",
                    "flow_label": "canal tours & cycling",
                    "trigger_intent": "Guest asks about outdoor activities, boat tours, or cycling.",
                    "goal": "Recommend renting bikes or taking a canal boat.",
                    "next": [{"target": "bridge_activities"}]
                },
                {
                    "id": "bridge_activities",
                    "displayName": "Bridge Activities",
                    "node_class": "flow",
                    "type": "bridge-node",
                    "goal": "Wrap up activities and check on unfinished open topics.",
                    "next": []
                },
                # Standalone: Deflect
                {
                    "id": "reactive_deflect",
                    "displayName": "Deflect Modernity",
                    "node_class": "reactive",
                    "mode": "standalone",
                    "trigger_intent": "Guest mentions AI, internet routing, or coding.",
                    "goal": "Laugh warmly and redirect to holiday relaxation.",
                    "next": []
                }
            ]
        },
        "layout": {"nodes": [], "connections": []}
    }

    session = ChatSession()
    session.current_node_id = "welcome"
    session.active_flow_id = "main"

    # Turn 1: Ask for dinner (Triggers dining flow)
    print("\n[Turn 1] Guest: 'Where should we eat tonight?'")
    res1 = run_dialogue_pipeline(
        user_input="Where should we eat tonight?",
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    print(f"  Host Bram: {''.join(res1['response_stream'])}")
    assert session.active_flow_id == "dining", f"Expected active_flow 'dining', got {session.active_flow_id}"
    print("  ✓ Successfully pivoted to Dining flow.")

    # Turn 2: Interruption with canal tours (Shelves dining into open_topics)
    print("\n[Turn 2] Guest: 'Wait, can we rent bikes or take a canal boat tomorrow?'")
    res2 = run_dialogue_pipeline(
        user_input="Wait, can we rent bikes or take a canal boat tomorrow?",
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    print(f"  Host Bram: {''.join(res2['response_stream'])}")
    assert session.active_flow_id == "activities"
    assert len(session.open_topics) == 1
    assert session.open_topics[0]["flow_id"] == "dining"
    print("  ✓ Dining flow saved to open_topics; Activities flow active.")

    # Turn 3: Bridge node triggers (Host wraps up activities & asks about dining)
    print("\n[Turn 3] Guest: 'Okay, boat tours sound fun.'")
    res3 = run_dialogue_pipeline(
        user_input="Okay, boat tours sound fun.",
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    reply3 = ''.join(res3['response_stream'])
    print(f"  Host Bram: {reply3}")
    assert any(w in reply3.lower() for w in ["dinner", "restaurant", "eat", "food"]), \
        "Host failed to bridge back to the open dining topic!"
    print("  ✓ Host successfully asked about previous open dining topic!")

    # Turn 4: Guest says yes to the bridge (Resumes dining)
    print("\n[Turn 4] Guest: 'Yes please, tell me about that restaurant!'")
    res4 = run_dialogue_pipeline(
        user_input="Yes please, tell me about that restaurant!",
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    print(f"  Host Bram: {''.join(res4['response_stream'])}")
    assert len(session.open_topics) == 0, "Open topic was not popped after resuming!"
    assert session.active_flow_id == "dining"
    print("  ✓ Open topic popped and resumed successfully.")

    print("\n=== ALL E2E BNB HOST CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_e2e_bnb_test()