import pytest
import json
import os, sys

from core.appvar import AppVar
from events import VarEvent
from automate.automationsequence import AutomationSequence, AutomationStep
from automate.automationstepdialog import AutomationStepDialog
from automate.automationrule import AutomationRule

# Import the module to be tested
# We specifically import the module-level singleton instance
from core import event_bus



def create_sample_sequence():
    
    steps = [
        {"type": "App", "name": "Create test var", "data": 
            {"command": "Set Variable", "variable": "test", "value": 0}},
        {"type": "Label", "name": "Label: loopstart", "data": 
            {"labelid": "loopstart"}},
        {"type": "Rule", "name": "Set point 1 to A", "data": 
            {"ruletype": "VLCB", "node_id":301, "event": 1, "value": 1}},
        {"type": "App", "name": "Increase test variable by 1", "data":
            {"variable": "test", "command": "Increment Variable", "value": 1}},
        {"type": "Rule", "name": "Set point 1 to B", "data": 
            {"ruletype": "VLCB", "node_id":301, "event": 1, "value": 0}},
        {"type": "Jump", "name": "Until loop end (if value1 <= value2 jump)", "data": 
            {"condition": "<=", "value1": "{test}", "value2": 10, "labelid": "loopstart"}}
    ]

    #return AutomationSequence("Test save seq", {"retry": True}, [step1, step2, step3])
    return AutomationSequence("Test save seq", steps, {})

def test_sequence_serialization_deserialization(qtbot):
    
    sequence = create_sample_sequence()

    # Serialize to JSON
    json_data = sequence.to_json()
    assert isinstance(json_data, str)

    # Validate JSON structure
    parsed = json.loads(json_data)
    #print (f"Parsed: {parsed}")
    assert("title" in parsed)
    assert("steps" in parsed)
    assert(parsed["title"] == "Test save seq")
    assert(len(parsed["steps"]) == 6)

    # Check appvar excluded
    assert("appvar" not in parsed["steps"][0].get("data", {}))

    # Deserialize back
    new_sequence = AutomationSequence.from_json(json_data, check_stop_func=lambda: False)
    assert(new_sequence.title == sequence.title)
    assert(new_sequence.settings == sequence.settings)
    assert(len(new_sequence.steps) == len(sequence.steps))

    # Check step details
    assert(new_sequence.steps[0].step_name == "Create test var")
    assert(new_sequence.steps[2].rule.rule_type == "VLCB")

def test_empty_steps(qtbot):
    
    
    sequence = AutomationSequence("Empty Seq", [], {})
    json_data = sequence.to_json()
    new_sequence = AutomationSequence.from_json(json_data, check_stop_func=lambda: False)
    assert(len(new_sequence.steps) == 0)

