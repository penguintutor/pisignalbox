## Test uses unittest.mock to test logs being sent

import pytest
from unittest.mock import Mock
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




def test_automation_console_sequence_1():
    # qtbot fixture automatically handles the QApplication lifecycle
    
    mock_dev_subscriber = Mock()
    mock_app_subscriber = Mock()
    mock_log_subscriber = Mock()

    event_bus.device_event_signal.connect(mock_dev_subscriber)
    event_bus.app_event_signal.connect(mock_app_subscriber)
    event_bus.log_event_signal.connect(mock_log_subscriber)
    
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

    ## The following shows how debugging can be applied looking
    ## at the events that are triggered
    # # --- DEBUGGING OUTPUT ---
    # print("\n--- Device Events Caught ---")
    # for index, call_args in enumerate(mock_dev_subscriber.call_args_list):
    #     # call_args.args contains positional arguments
    #     # call_args.kwargs contains keyword arguments (if any)
    #     print(f"Call {index}: {call_args.args[0]}")
        
    # print("\n--- App Events Caught ---")
    # for index, call_args in enumerate(mock_app_subscriber.call_args_list):
    #     print(f"Call {index}: {call_args.args[0]}")

    # print("\n--- Log Events Caught ---")
    # for index, call_args in enumerate(mock_log_subscriber.call_args_list):
    #     print(f"Call {index}: {call_args.args[0]}")
    #     #print(f"{call_args.args[0]}")
    # # ------------------------
    
    assert mock_dev_subscriber.call_count == 2
    assert mock_app_subscriber.call_count == 1
    assert mock_log_subscriber.call_count == 8

    first_log_event = mock_log_subscriber.call_args_list[0].args[0]
    # Expected string if output the log event as __str__
    first_log_expected = "Log {'event_type': 'Log', 'level': 5, 'sequence': 'Test sequence 1', 'step': '00 - Start', 'description': 'Starting sequence: Test sequence 1'}"

    assert str(first_log_event) == first_log_expected
