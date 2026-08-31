import pytest

import os, sys
# Setup PySide6 environment for testing
from PySide6.QtCore import QObject
#from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from pyvlcb import VLCB, VLCBFormat, VLCBOpcode


# Force-initialize layout first to mimic the main program's import order
from layout.layoutdialog import LayoutDialog 
# Now import the class to test
from loco import Loco

from trackview import TrackViewNode
from device import device_manager

from automate import AutomationRule

# A global QApplication instance is required for signal/slot testing
#app = QApplication.instance() or QApplication(sys.argv)

# Import the module to be tested
# We specifically import the module-level singleton instance
#from core import serialize_event, deserialize_event, event_bus
from core import event_bus 


@pytest.mark.parametrize ("rule_name, rule_type, rule_data, expected_string", [
    # Run 1: Point 1 to 1
    ("Set point 1 to 1", "VLCB", {"node_id":301, "event": 1, "value": 1}, "VLCB 301 1 1"),
    # Run 2: Point 1 to "off"
    ("Set point 1 to off", "VLCB", {"node_id":301, "event": 1, "value": "off"}, "VLCB 301 1 off"),
    # Run 3: Point 1 invalid string
    ("Set point 2 to 0", "VLCB", {"node_id":301, "event": 0x000002, "value": "0"}, "VLCB 301 2 0")
])

# Test the basic rule elements
def test_rule_dev_1 (qtbot, rule_name, rule_type, rule_data, expected_string):
  
    # Create the rule using the parameters
    dev_rule = AutomationRule(rule_name, rule_type, {"data": rule_data})
    
    # Wait for the signal and run the rule
    with qtbot.waitSignal(event_bus.device_event_signal) as blocker:
        dev_rule.run()
    
    assert len(blocker.args) == 1
    assert str(blocker.args[0]) == expected_string

    

