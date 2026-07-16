import unittest

import os, sys
# Setup PySide6 environment for testing
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from pyvlcb import VLCB
from pyvlcb import VLCBFormat, VLCBOpcode
from loco import Loco
from trackview import TrackViewNode
from device import device_manager

from core.appvar import AppVar
from events import VarEvent
from automate.automationsequence import AutomationSequence, AutomationStep
from automate.automationstepdialog import AutomationStepDialog
from automate.automationrule import AutomationRule

# A global QApplication instance is required for signal/slot testing
app = QApplication.instance() or QApplication(sys.argv)

# Import the module to be tested
# We specifically import the module-level singleton instance
#from core import serialize_event, deserialize_event, event_bus
from core import event_bus

class MockWindow:


    def get_variable (self, var_name):
        if hasattr(self, 'vars'):
            value = self.vars.get_variable (var_name)
            #print (f"MockWindow Get variable {var_name} resulting in {value}")
            return value
        else:
            #print (f"MockWindow No appvariables to get variable {var_name}")
            return 0

    def set_variable (self, var_name, var_value):
        if hasattr(self, 'vars'):
            value = self.vars.set_variable (var_name, var_value)
            #print (f"MockWindow Set variable {var_name} to {var_value} resulting in {value}")
            return value
        else:
            #print (f"MockWindow No appvariables to set variable {var_name} to {var_value}")
            return var_value
        

    def inc_variable (self, var_name, inc_value=1):
        if hasattr(self, 'vars'):
            value = self.vars.inc_variable (var_name, inc_value)
            #print (f"MockWindow Inc variable {var_name} by {inc_value} resulting in {value}")
            return value
        else:
            print (f"MockWindow No appvariables to inc variable {var_name} by {inc_value}")
            return inc_value

## Test creation of rules, including importing and handling recursion
class TestAutomationRules(unittest.TestCase):
    
    def setUp(self):
        pass

    def tearDown(self):
        pass
        
        
    def test_sequence_1 (self):
        # Set Signal spy to watch for signal sent to device
        dev_spy = QSignalSpy(event_bus.device_event_signal)
        app_spy = QSignalSpy(event_bus.app_event_signal)
        
        # Need to have a fake mainwindow for testing
        # For testing AutomationSequence / AutomationStep then this only needs to house a link to
        # appvariable
        mainwindow = MockWindow()
        mainwindow.vars = AppVar()
        
        steps = []
        
        # Create a dict for a rule: 
        rule0 = {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "data": {"node_id":301, "event": 1, "value": 1}}
        rule1 = {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "data": {"node_id":301, "event": 1, "value": 0}}
        # This is an unusual thing for automation, but allows testing of an AppEvent 
        rule2 = {"type": "Rule", "name": "Show Console", "ruletype": "App", "action":"showconsole", "data": {}}
        
        # Combine steps into sequence
        steps.append(rule0)
        steps.append(rule1)
        steps.append(rule2)
        
        # Create a rule - needs values for the Event
        sequence_1 = AutomationSequence ("Test sequence 1", steps, {}, check_stop_func=lambda: False)
        
        # Run the sequence
        sequence_1.run()
        
        # Test that the event_bus count has increased, that it equals the event we created
        # and that the values match the expected string
        self.assertEqual(dev_spy.count(), 2)
        self.assertEqual(dev_spy.at(0)[0], sequence_1.steps[0].rule.event)


    # Test with a variable
    def test_sequence_vars (self):

        # Set Signal spy to watch for signal sent to device
        dev_spy = QSignalSpy(event_bus.device_event_signal)
        var_spy = QSignalSpy(event_bus.var_event_signal)
        
        # Need to have a fake mainwindow for testing
        # For testing AutomationSequence / AutomationStep then this only needs to house a link to
        # appvariable
        mainwindow = MockWindow()
        mainwindow.vars = AppVar()
        
        # Create a dict for a rule:
        steps = [
            {"type": "Var", "name": "Create test var", "varname": "test", "action": "set", "value": 0},
            {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "node_id":301, "event": 1, "value": "{test}"},
            {"type": "Var", "name": "Increase test variable by 1", "varname": "test", "action": "inc", "value": 1},
            {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "node_id":301, "event": 1, "value": "{test}"}
            ]
        
        # Create a rule - needs values for the Event
        sequence_1 = AutomationSequence ("Test sequence 1", steps, {}, check_stop_func=lambda: False)
        
        # Run the sequence
        sequence_1.run()
        
        # Test that the event_bus count has increased, that it equals the event we created
        # and that the values match the expected string
        self.assertEqual(var_spy.count(), 2)
        self.assertEqual(dev_spy.count(), 2)
        self.assertEqual(dev_spy.at(0)[0], sequence_1.steps[1].rule.event)
        self.assertEqual(str(dev_spy.at(0)[0]), "VLCB 301 1 0")
        self.assertEqual(dev_spy.at(1)[0], sequence_1.steps[3].rule.event)
        self.assertEqual(str(dev_spy.at(1)[0]), "VLCB 301 1 1")



    # Test with a simple loop
    def test_sequence_loop (self):
        # Set Signal spy to watch for signal sent to device
        dev_spy = QSignalSpy(event_bus.device_event_signal)
        var_spy = QSignalSpy(event_bus.var_event_signal)
        
        # Need to have a fake mainwindow for testing
        # For testing AutomationSequence / AutomationStep then this only needs to house a link to
        # appvariable
        mainwindow = MockWindow()
        mainwindow.vars = AppVar()
        
        # Create a dict for a rule:
        steps = [
            {"type": "Var", "name": "Create test var", "varname": "test", "action": "set", "value": 0},
            {"type": "Label", "name": "Label: loopstart", "data": {"labelid": "loopstart"}},
            {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "node_id":301, "event": 1, "value": 1},
            {"type": "Var", "name": "Increase test variable by 1", "varname": "test", "action": "inc", "value": 1},
            {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "node_id":301, "event": 1, "value": 0},
            {"type": "Jump", "name": "Until loop end (if value1 <= value2 jump)", "test": "<=", "value1": "{test}", "value2": 10, "label": "loopstart"}
            ]
        
        
        # Create a rule - needs values for the Event
        sequence_1 = AutomationSequence ("Test sequence 1", steps, {}, check_stop_func=lambda: False)
        
        # Run the sequence
        sequence_1.run()
        
        # Test that the event_bus count has increased, that it equals the event we created
        # and that the values match the expected string
        # Runs 10x so now 22
        self.assertEqual(dev_spy.count(), 22)
        self.assertEqual(dev_spy.at(0)[0], sequence_1.steps[2].rule.event)
        self.assertEqual(str(dev_spy.at(0)[0]), "VLCB 301 1 1")
        self.assertEqual(dev_spy.at(1)[0], sequence_1.steps[4].rule.event)
        self.assertEqual(str(dev_spy.at(1)[0]), "VLCB 301 1 0")

                
    # Test with a variable
    def test_sequence_wait (self):

        # Set Signal spy to watch for signal sent to device
        dev_spy = QSignalSpy(event_bus.device_event_signal)
        var_spy = QSignalSpy(event_bus.var_event_signal)
        
        # Need to have a fake mainwindow for testing
        # For testing AutomationSequence / AutomationStep then this only needs to house a link to
        # appvariable
        mainwindow = MockWindow()
        mainwindow.vars = AppVar()
        
        # Create a dict for a rule:
        steps = [
            {"type": "Var", "name": "Create test var", "varname": "test", "action": "set", "value": 0},
            {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "node_id":301, "event": 1, "value": "{test}"},
            {"type": "Var", "name": "Increase test variable by 1", "varname": "test", "action": "inc", "value": 1},
            {"type": "Wait", "name": "Wait 0.5 seconds", "waittype": "delay", "time": 0.5},
            {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "node_id":301, "event": 1, "value": "{test}"}
            ]
        
        # Create a rule - needs values for the Event
        sequence_1 = AutomationSequence ("Test sequence 1", steps, {}, check_stop_func=lambda: False)
        
        # Run the sequence
        sequence_1.run()
        
        # Test that the event_bus count has increased, that it equals the event we created
        # and that the values match the expected string
        self.assertEqual(var_spy.count(), 2)
        self.assertEqual(dev_spy.count(), 2)
        self.assertEqual(dev_spy.at(0)[0], sequence_1.steps[1].rule.event)
        self.assertEqual(str(dev_spy.at(0)[0]), "VLCB 301 1 0")
        self.assertEqual(dev_spy.at(1)[0], sequence_1.steps[4].rule.event)
        self.assertEqual(str(dev_spy.at(1)[0]), "VLCB 301 1 1")


    def test_sequence_save (self):
        # Set Signal spy to watch for signal sent to device
        #dev_spy = QSignalSpy(event_bus.device_event_signal)
        #var_spy = QSignalSpy(event_bus.var_event_signal)
        
        # Need to have a fake mainwindow for testing
        # For testing AutomationSequence / AutomationStep then this only needs to house a link to
        # appvariable
        mainwindow = MockWindow()
        mainwindow.vars = AppVar()
        
        # Create a dict for a rule:
        steps = [
            {"type": "Var", "name": "Create test var", "varname": "test", "action": "set", "value": 0},
            {"type": "Label", "name": ":loopstart"},
            {"type": "Rule", "name": "Set point 1 to A", "ruletype": "VLCB", "node_id":301, "event": 1, "value": 1},
            {"type": "Var", "name": "Increase test variable by 1", "varname": "test", "action": "inc", "value": 1},
            {"type": "Rule", "name": "Set point 1 to B", "ruletype": "VLCB", "node_id":301, "event": 1, "value": 0},
            {"type": "Jump", "name": "Until loop end (if value1 <= value2 jump)", "test": "<=", "value1": "{test}", "value2": 10, "label": ":loopstart"}
            ]
        
        
        # Create a rule - needs values for the Event
        sequence_1 = AutomationSequence ("Test save seq", steps, {})
             
        json_data = sequence_1.to_json()
        new_sequence = AutomationSequence.from_json(json_data, mainwindow, check_stop_func=lambda: False)
        
        
        self.assertEqual(sequence_1.title, "Test save seq")
        self.assertEqual(new_sequence.title, "Test save seq")



                
if __name__ == '__main__':
    unittest.main()