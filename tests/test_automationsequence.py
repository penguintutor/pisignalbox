import pytest
from PySide6.QtTest import QSignalSpy

# Import the module to be tested
from pyvlcb import VLCB, VLCBFormat, VLCBOpcode
from loco import Loco
from trackview import TrackViewNode
from device import device_manager
from core.appvar import AppVar
from events import VarEvent
from automate.automationsequence import AutomationSequence, AutomationStep
from automate.automationstepdialog import AutomationStepDialog
from automate.automationrule import AutomationRule
from core import event_bus



def test_sequence_1(qtbot):
    # qtbot fixture automatically handles the QApplication lifecycle
    
    dev_spy = QSignalSpy(event_bus.device_event_signal)
    app_spy = QSignalSpy(event_bus.app_event_signal)
    
    steps = [
        {"type": "Rule", "name": "Set point 1 to A", "data": 
            {"ruletype": "VLCB", "node_id":301, "event": 1, "value": 1}},
        {"type": "Rule", "name": "Set point 1 to B", "data": 
            {"ruletype": "VLCB", "node_id":301, "event": 1, "value": 0}},
        {"type": "Rule", "name": "Show Console", "data": 
            {"ruletype": "App", "action":"showconsole"}}
    ]
    
    sequence_1 = AutomationSequence("Test sequence 1", steps, {}, check_stop_func=lambda: False)
    sequence_1.run()
    
    assert dev_spy.count() == 2
    assert dev_spy.at(0)[0] == sequence_1.steps[0].rule.event


def test_sequence_vars(qtbot):
    dev_spy = QSignalSpy(event_bus.device_event_signal)
    var_spy = QSignalSpy(event_bus.var_event_signal)
    
    steps = [
        {"type": "App", "name": "Create test var", "data": 
            {"command": "Set Variable", "variable": "test", "value": 0}},
        {"type": "Rule", "name": "Set point 1 to A", "data":
            {"ruletype": "VLCB", "node_id":301, "event": 1, "value": "{test}"}},
        {"type": "App", "name": "Increase test variable by 1", "data":
            {"variable": "test", "command": "Increment Variable", "value": 1}},
        {"type": "Rule", "name": "Set point 1 to B", "data": 
            {"ruletype": "VLCB", "node_id":301, "event": 1, "value": "{test}"}}
    ]
    
    sequence_1 = AutomationSequence("Test sequence 1", steps, {}, check_stop_func=lambda: False)
    sequence_1.run()

    assert var_spy.count() == 2
    assert dev_spy.count() == 2
    assert dev_spy.at(0)[0] == sequence_1.steps[1].rule.event
    assert str(dev_spy.at(0)[0]) == "VLCB 301 1 0"
    assert dev_spy.at(1)[0] == sequence_1.steps[3].rule.event
    assert str(dev_spy.at(1)[0]) == "VLCB 301 1 1"


def test_sequence_loop(qtbot):
    dev_spy = QSignalSpy(event_bus.device_event_signal)
    var_spy = QSignalSpy(event_bus.var_event_signal)
    
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
    
    sequence_1 = AutomationSequence("Test sequence Loop", steps, {}, check_stop_func=lambda: False)
    sequence_1.run()

    # # --- DEBUGGING OUTPUT ---
    # print("\n--- Device Signals Emitted ---")
    # for i in range(dev_spy.count()):
    #     # .at(i) gets the emission, [0] gets the first argument (your Event)
    #     event_arg = dev_spy.at(i)[0] 
    #     print(f"Emission {i}: {str(event_arg)}")
        
    # print("\n--- Var Signals Emitted ---")
    # for i in range(var_spy.count()):
    #     event_arg = var_spy.at(i)[0]
    #     print(f"Emission {i}: {str(event_arg)}")
    # print("------------------------------\n")
    
    
    # Runs 10x so now 22
    assert dev_spy.count() == 22
    assert dev_spy.at(0)[0] == sequence_1.steps[2].rule.event
    assert str(dev_spy.at(0)[0]) == "VLCB 301 1 1"
    assert dev_spy.at(1)[0] == sequence_1.steps[4].rule.event
    assert str(dev_spy.at(1)[0]) == "VLCB 301 1 0"

            
def test_sequence_wait(qtbot):
    dev_spy = QSignalSpy(event_bus.device_event_signal)
    var_spy = QSignalSpy(event_bus.var_event_signal)
    
    steps = [
        {"type": "App", "name": "Create test var", "data": 
            {"command": "Set Variable", "variable": "test", "value": 0}},
        {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "data": 
            {"node_id":301, "event": 1, "value": "{test}"}},
        {"type": "App", "name": "Increase test variable by 1", "data":
            {"variable": "test", "command": "Increment Variable", "value": 1}},
        {"type": "Wait", "name": "Wait 0.5 seconds", "data" : 
            {"waittype": "delay", "time": 0.5}},
        {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "data": 
            {"node_id":301, "event": 1, "value": "{test}"}}
    ]
    
    sequence_1 = AutomationSequence("Test sequence 1", steps, {}, check_stop_func=lambda: False)
    sequence_1.run()
    
    assert var_spy.count() == 2
    assert dev_spy.count() == 2
    assert dev_spy.at(0)[0] == sequence_1.steps[1].rule.event
    assert str(dev_spy.at(0)[0]) == "VLCB 301 1 0"
    assert dev_spy.at(1)[0] == sequence_1.steps[4].rule.event
    assert str(dev_spy.at(1)[0]) == "VLCB 301 1 1"


def test_sequence_save(qtbot):
    steps = [
        {"type": "App", "name": "Create test var", "data": 
            {"command": "Set Variable", "variable": "test", "value": 0}},
        {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "data": 
            {"node_id":301, "event": 1, "value": "{test}"}},
        {"type": "App", "name": "Increase test variable by 1", "data":
            {"variable": "test", "command": "Increment Variable", "value": 1}},
        {"type": "Wait", "name": "Wait 0.5 seconds", "data" : 
            {"waittype": "delay", "time": 0.5}},
        {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "data": 
            {"node_id":301, "event": 1, "value": "{test}"}}
    ]
    
    sequence_1 = AutomationSequence("Test save seq", steps, {})
    json_data = sequence_1.to_json()
    #new_sequence = AutomationSequence.from_json(json_data, check_stop_func=lambda: False)
    new_sequence = AutomationSequence.from_json(json_data, check_stop_func=lambda: False)
    
    assert sequence_1.title == "Test save seq"
    assert new_sequence.title == "Test save seq"