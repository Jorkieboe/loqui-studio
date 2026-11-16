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
    user_msg_1 = "Where should we eat tonight?"
    res1 = run_dialogue_pipeline(
        user_input=user_msg_1,
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    reply1 = ''.join(res1['response_stream'])
    print(f"  Host Bram: {reply1}")
    session.history.append({"role": "user", "content": user_msg_1})
    session.history.append({"role": "assistant", "content": reply1})
    assert session.active_flow_id == "reactive_dining", f"Expected active_flow 'reactive_dining', got {session.active_flow_id}"
    print("  ✓ Successfully pivoted to Dining flow.")

    # Turn 2: Interruption with canal tours (Shelves dining into open_topics, triggers 'reactive_activities')
    print("\n[Turn 2] Guest: 'Wait, can we rent bikes or take a canal boat tomorrow?'")
    user_msg_2 = "Wait, can we rent bikes or take a canal boat tomorrow?"
    res2 = run_dialogue_pipeline(
        user_input=user_msg_2,
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    reply2 = ''.join(res2['response_stream'])
    print(f"  Host Bram: {reply2}")
    session.history.append({"role": "user", "content": user_msg_2})
    session.history.append({"role": "assistant", "content": reply2})
    assert session.active_flow_id == "reactive_activities"
    assert len(session.open_topics) == 1
    assert session.open_topics[0]["flow_id"] == "reactive_dining"
    print("  ✓ Dining flow saved to open_topics; Activities flow active.")

    # Turn 3: Bridge node triggers (Host wraps up activities & asks about dining)
    print("\n[Turn 3] Guest: 'Okay, boat tours sound fun.'")
    user_msg_3 = "Okay, boat tours sound fun."
    res3 = run_dialogue_pipeline(
        user_input=user_msg_3,
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    reply3 = ''.join(res3['response_stream'])
    print(f"  Host Bram: {reply3}")
    session.history.append({"role": "user", "content": user_msg_3})
    session.history.append({"role": "assistant", "content": reply3})
    assert any(w in reply3.lower() for w in ["dinner", "restaurant", "eat", "food", "bistro"]), \
        "Host failed to bridge back to the open dining topic!"
    print("  ✓ Host successfully asked about previous open dining topic!")

    # Turn 4: Guest says yes to bridge (Evaluates to 'reactive_dining' tool call, restoring paused dining flow)
    print("\n[Turn 4] Guest: 'Yes please, tell me about that restaurant!'")
    user_msg_4 = "Yes please, tell me about that restaurant!"
    res4 = run_dialogue_pipeline(
        user_input=user_msg_4,
        active_node_id=session.current_node_id,
        history=session.history,
        character_config=bnb_config,
        session_instance=session
    )
    reply4 = ''.join(res4['response_stream'])
    print(f"  Host Bram: {reply4}")
    session.history.append({"role": "user", "content": user_msg_4})
    session.history.append({"role": "assistant", "content": reply4})
    assert len(session.open_topics) == 0, "Open topic was not popped after resuming!"
    assert session.active_flow_id == "reactive_dining"
    print("  ✓ Open topic popped and resumed successfully.")

    print("\n=== ALL E2E BNB HOST CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_e2e_bnb_test()