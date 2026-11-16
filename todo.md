### Test Script Directory Structure
We will place all verification scripts in `backend/scripts/tests/`:
```text
backend/scripts/tests/
├── test_phase1_schemas.py      # Tests serialization of reactive & bridge nodes
├── test_phase2_dispatcher.py   # Tests tool-call schema generation, intent matching & open topics
├── test_phase4_validation.py   # Tests graph validation (enforcing bridge node connection)
└── test_phase5_e2e_bnb.py      # End-to-end multi-turn simulation of the BnB host
```

---

## Complete Implementation Plan & Todo

### Phase 1: Data Schemas & State Models
- [x] **1.1. Update `ChatSession` Model (`backend/scripts/core/session_manager.py`)**
  - Add `active_flow_id: Optional[str] = "main"` to track the current active flow/subflow context.
  - Add `open_topics: List[Dict[str, Any]] = []` to store shelved conversation threads as a stack/list (`flow_id`, `flow_label`, `paused_node_id`).
- [x] **1.2. Update Node Schemas (`backend/scripts/api/character.py`)**
  - Support `node_class: "reactive"` with attributes:
    - `mode: "flow" | "standalone"`
    - `trigger_intent: str` (the condition/description used for the dynamic tool-calling description)
    - `flow_label: Optional[str]` (human-readable title used when generating bridge prompts)
  - Support `bridge-node` (`node_class: "flow"`, `type: "bridge-node"`, with optional custom `goal`).

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
                "trigger_intent": "User brings up modern tech or AI.",
                "flow_label": "deflect",
                "goal": "Express confusion and stay in character.",
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

### Phase 2: Lightweight Tool-Calling Intent Dispatcher & Routing
- [x] **2.1. Dynamic Tool Generation from Reactive Nodes (`backend/scripts/core/intent_dispatcher.py`)**
  - Implement `build_intent_tools(reactive_nodes, open_topics=None)`:
    - Iterate over all reactive nodes in `var_prompt`.
    - Create a tool for each reactive node where:
      - `name`: Node ID (e.g., `reactive_dining`).
      - `description`: The node's `trigger_intent`. If this flow is currently shelved in `open_topics`, the description is dynamically updated to:
        `f"{trigger_intent} (Also select this if the user wants to resume/return to the previously discussed topic about {flow_label})"`
      - `parameters`: Empty schema object (`{"type": "object", "properties": {}}`).
    - Append exactly one fallback tool:
      - `name`: `resume_current_flow`
      - `description`: `"Select this if the user does not want to switch flow and is continuing the current conversation or answering the assistant's previous question."`
    - No separate `resume_open_topic` tool is needed; resuming a paused flow simply maps to that reactive node's existing tool call.
- [x] **2.2. Intent Evaluation via Lightweight LLM Tool Call (`backend/scripts/core/intent_dispatcher.py`)**
  - Implement `evaluate_intent(user_input, history, reactive_nodes, active_flow, open_topics)`:
    - Format conversational context using the **last 3 turns** from `history` (up to the last 6 messages: 3 user turns + 3 assistant turns) plus the current `user_input`.
    - Build an LLM tool-call request with the dynamically generated tools.
    - Set `tool_choice="auto"` (or explicit tool-calling mode).
    - Parse `tool_calls[0].function.name` from the model response.
    - If the tool call fails or the model selects `resume_current_flow`, return `"resume_current_flow"`.
- [x] **2.3. Integrate Dispatcher into Dialogue Pipeline (`backend/scripts/core/orchestrator.py`)**
  - In `run_dialogue_pipeline`:
    1. Call `evaluate_intent()` using recent history and the dynamic tool definitions.
    2. If intent matches `resume_current_flow`:
       - Continue standard flow progression along current node edges.
    3. If intent matches a reactive node with `mode: "flow"`:
       - **Case A: Resuming an open topic**: If the selected reactive node ID exists in `session.open_topics`:
         - Pop that entry from `session.open_topics`.
         - If the current flow is active and non-main, shelf current flow into `session.open_topics`.
         - Set `session.active_flow_id` to that node ID and resume at its `paused_node_id`.
       - **Case B: Starting a new flow**:
         - If `active_flow_id != "main"`: shelf current flow `{flow_id, flow_label, paused_node_id}` into `session.open_topics`.
         - Set `session.active_flow_id = reactive_node.id` and jump execution to this reactive node.
    4. If intent matches a reactive node with `mode: "standalone"`:
       - Execute standalone prompt node as a one-shot response without modifying `active_flow_id` or pushing to `open_topics`.
- [x] **2.4. Bridge Directive Injection (`backend/scripts/core/orchestrator.py`)**
  - When the orchestrator executes a `bridge-node`:
    - If `open_topics` contains shelved topics:
      - Inject instruction: `"Wrap up the current topic concisely, then ask the user if they'd like to return to <open_topics[-1]['flow_label']>."`
    - If `open_topics` is empty:
      - Inject instruction: `"Conclude the current topic concisely and ask the user how else you can help them."`
    - Upon leaving the bridge node, clear/reset the active subflow back towards the main flow.

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
```

---

### Phase 3 & 4: Vue Flow Graph & Topology Validation
- [x] **3.1. Build `ReactiveNode` Component (`frontend/src/components/GraphEditor.vue`)**
  - Render node class with distinct UI badge (`Reactive Flow` / `Standalone Reactive`).
  - Inputs for `trigger_intent` (used for the tool description) and `flow_label`.
- [x] **3.2. Build `BridgeNode` Component (`frontend/src/components/GraphEditor.vue`)**
  - Distinct badge indicating subflow exit point.
  - Optional custom prompt directive override.
- [x] **3.3. Auto-Spawn Bridge on new Reactive Flow creation (`frontend/src/views/CharacterEditorView.vue`)**
  - When dragging or adding a `reactive` node with `mode: "flow"`, auto-spawn an accompanying `bridge-node` connected downstream.
- [x] **4.1. Graph Topology Validation (`frontend/src/views/CharacterEditorView.vue` & Backend Validator `scripts/core/validation.py`)**
  - Crawler rule: Any `reactive` node set to `mode: "flow"` must contain a reachable path to a `bridge-node`.
  - Block graph saving/deployment if a reactive sub-flow has an unbridged dead end.

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
```

---

### Phase 5: Debug Telemetry & Multi-Turn Scenario Test
- [ ] **5.1. Update Debug Drawer (`frontend/src/components/TestChatPanel.vue`)**
  - Add drawer section displaying:
    - Current `active_flow_id`
    - Evaluated tool call intent (`reactive_<id>` or `resume_current_flow`)
    - Dynamic tools passed to the model during the turn
    - Current `open_topics` stack items
- [ ] **5.2. Multi-Turn BnB Host Verification Script**
  - Run the full interactive simulation script covering: initial flow -> sub-flow interruption -> topic stacking -> bridge trigger -> flow resumption via original reactive node tool call.

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
                # Sub-flow 1: Dining
                {
                    "id": "reactive_dining",
                    "displayName": "Dining",
                    "node_class": "reactive",
                    "mode": "flow",
                    "flow_label": "dinner & restaurants",
                    "trigger_intent": "Guest asks for food, restaurants, or dining recommendations.",
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

    # Turn 1: Ask for dinner (Triggers dining flow tool: 'reactive_dining')
    print("\n[Turn 1] Guest: 'Where should we eat tonight?'")
    res1 = run_dialogue_pipeline(
        user_input="Where should we eat tonight?",
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    print(f"  Host Bram: {''.join(res1['response_stream'])}")
    assert session.active_flow_id == "reactive_dining", f"Expected active_flow 'reactive_dining', got {session.active_flow_id}"
    print("  ✓ Successfully pivoted to Dining flow.")

    # Turn 2: Interruption with canal tours (Shelves dining into open_topics, triggers 'reactive_activities')
    print("\n[Turn 2] Guest: 'Wait, can we rent bikes or take a canal boat tomorrow?'")
    res2 = run_dialogue_pipeline(
        user_input="Wait, can we rent bikes or take a canal boat tomorrow?",
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    print(f"  Host Bram: {''.join(res2['response_stream'])}")
    assert session.active_flow_id == "reactive_activities"
    assert len(session.open_topics) == 1
    assert session.open_topics[0]["flow_id"] == "reactive_dining"
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
    assert any(w in reply3.lower() for w in ["dinner", "restaurant", "eat", "food", "bistro"]), \
        "Host failed to bridge back to the open dining topic!"
    print("  ✓ Host successfully asked about previous open dining topic!")

    # Turn 4: Guest says yes to bridge (Evaluates to 'reactive_dining' tool call, restoring paused dining flow)
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
    assert session.active_flow_id == "reactive_dining"
    print("  ✓ Open topic popped and resumed successfully.")

    print("\n=== ALL E2E BNB HOST CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_e2e_bnb_test()