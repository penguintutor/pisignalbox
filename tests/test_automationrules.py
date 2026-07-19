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


@pytest.fixture
def setup_tests():
    """ run each time that a code as for setup_tests"""
    dev_rule1 = AutomationRule ("Set point 1 to A", "VLCB", {"node_id":301, "event": 1, "value": 1})
    dev_rule2 = AutomationRule ("Set point 1 to B", "VLCB", {"node_id":301, "event": 1, "value": "off"})

    yield dev_rule1, dev_rule2

# Test the very basic rule elements
def test_rule_dev_1 (qtbot, setup_tests):
  
    rule_1, _ = setup_tests
    
    # Use qtbot as a context manager to spy on the signal
    with qtbot.waitSignal(event_bus.device_event_signal) as blocker:
        rule_1.run()
    
    assert str(blocker.args[0]) == "VLCB 301 1 1"

def test_rule_dev_2 (qtbot, setup_tests):
  
    _, rule_2 = setup_tests
    
    # Use qtbot as a context manager to spy on the signal
    with qtbot.waitSignal(event_bus.device_event_signal) as blocker:
        rule_2.run()
    
    assert str(blocker.args[0]) == "VLCB 301 1 off"
    

