# test_eventbus.py
import pytest
import os
import logging
from pathlib import Path
from unittest.mock import patch

# Setup PySide6 environment for testing
from PySide6.QtCore import QObject
from PySide6.QtTest import QSignalSpy

# Import from application
from events import DeviceEvent, AppEvent, GuiEvent, LocoEvent, TimerEvent

# Import the module to be tested
from core import event_bus

# Get the directory of the current test file
CURRENT_DIR = Path(__file__).parent
# Get the path to your data directory
DATA_DIR = CURRENT_DIR / "data"


@pytest.fixture
def bus():
    """Fixture to reset the singleton event_bus state for each test."""
    event_bus.event_rules = []
    event_bus.automation_enabled = True
    event_bus.automation_count = 0
    event_bus.max_automation_count = 100  # Reset to default
    return event_bus


@pytest.fixture
def test_filename():
    """Fixture to provide a test filename and clean it up after the test."""
    filename = DATA_DIR / "test_rules.json"
    yield filename
    
    # TearDown equivalent: Clean up any created files
    if filename.exists():
        filename.unlink()


def test_singleton_instance(bus, qtbot):
    # Don't call EventBus() constructor again.
    # Instead, import the module 'core' again and check
    # that the 'event_bus' instance from it is the same object
    # as the one we got in the fixture. This proves it's a singleton.
    from core import event_bus as bus_again
    assert bus is bus_again, "Imported event_bus should always be the same instance"
    assert bus is event_bus, "Global event_bus should be the same as bus fixture"


def test_broadcast_signals(bus, qtbot):
    # Test that broadcast emits the correct signal for each event type
    app_event = AppEvent({"action": "showconsole"})
    dev_event = DeviceEvent({"title": "Test dev event"})
    gui_event = GuiEvent({"title": "Test Gui event"})
    loco_event = LocoEvent("ERR", {"title": "Test Loco event"})
    timer_event = TimerEvent("timer", {"title": "Test timer event"})

    # Create QSignalSpy instances for each signal
    app_spy = QSignalSpy(bus.app_event_signal)
    dev_spy = QSignalSpy(bus.device_event_signal)
    gui_spy = QSignalSpy(bus.gui_event_signal)
    loco_spy = QSignalSpy(bus.loco_event_signal)
    timer_spy = QSignalSpy(bus.timer_event_signal)

    # Broadcast one of each event
    bus.broadcast(app_event)
    bus.broadcast(dev_event)
    bus.broadcast(gui_event)
    bus.broadcast(loco_event)
    bus.broadcast(timer_event)
    
    assert app_spy.count() == 1
    assert dev_spy.count() == 1
    assert gui_spy.count() == 1
    assert loco_spy.count() == 1
    assert timer_spy.count() == 1

    assert app_spy.at(0)[0] == app_event
    assert dev_spy.at(0)[0] == dev_event
    assert gui_spy.at(0)[0] == gui_event
    assert loco_spy.at(0)[0] == loco_event
    assert timer_spy.at(0)[0] == timer_event


def test_rule_management(bus, qtbot):
    assert bus.num_rules() == 0

    # Add rule 1
    event1 = DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10})
    action1 = GuiEvent({"title": "Test Gui event"})
    bus.add_rule(event1, action1)
    
    assert bus.num_rules() == 1
    assert bus.event_rules[0][0] == event1
    assert bus.event_rules[0][1] == action1

    # Add rule 2
    event2 = AppEvent({"action": "showconsole", "Title": "App Event"})
    action2 = LocoEvent("ERR", {"title": "Test Loco event"})
    bus.add_rule(event2, action2)
    assert bus.num_rules() == 2

    # Test del_entry (deletes by index)
    bus.del_entry(0)  # Delete the first rule
    assert bus.num_rules() == 1
    assert bus.event_rules[0][0] == event2  # Check remaining rule
    assert bus.event_rules[0][1] == action2


def test_consume_applies_rules(bus, qtbot):
    # 'consume' should apply rules but NOT broadcast the original event
    trigger1 = DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10})
    action = GuiEvent({"title": "Test Gui event"})
    bus.add_rule(trigger1, action)

    gui_spy = QSignalSpy(bus.gui_event_signal)
    dev_spy = QSignalSpy(bus.device_event_signal)

    # Consume the event
    bus.consume(trigger1)

    # Assert: The action event should be broadcast
    assert gui_spy.count() == 1, "Action event should be broadcast"
    assert gui_spy.at(0)[0] == action

    # Assert: The original event should NOT be broadcast
    assert dev_spy.count() == 0, "Original event should not be broadcast by consume"


def test_publish_applies_rules_and_broadcasts(bus, qtbot):
    # 'publish' should BOTH apply rules AND broadcast the original event
    trigger1 = DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10})
    action = GuiEvent({"title": "Test Gui event"})
    bus.add_rule(trigger1, action)

    dev_spy = QSignalSpy(bus.device_event_signal)
    gui_spy = QSignalSpy(bus.gui_event_signal)

    # Publish the trigger1 event
    bus.publish(trigger1)

    # Assert: The original event (trigger1) was broadcast
    assert dev_spy.count() == 1, "Original event should be broadcast by publish"
    assert dev_spy.at(0)[0] == trigger1

    # Assert: The rule's action (action) was ALSO broadcast
    assert gui_spy.count() == 1, "Action event should be broadcast by rule"
    assert gui_spy.at(0)[0] == action


def test_consume_automation_disabled(bus, qtbot):
    bus.automation_enabled = False

    trigger1 = DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10})
    action = GuiEvent({"title": "Test Gui event"})
    bus.add_rule(trigger1, action)

    gui_spy = QSignalSpy(bus.gui_event_signal)

    bus.consume(trigger1)

    # Assert: No signals fired because automation is off
    assert gui_spy.count() == 0


def test_rule_matching_logic(bus, qtbot):
    # Rule: DeviceEvent(value=10) -> GuiEvent(value=20)
    trigger1 = DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10})
    action = GuiEvent({"title": "Test Gui event"})
    bus.add_rule(trigger1, action)

    gui_spy = QSignalSpy(bus.gui_event_signal)

    # Test match
    bus.consume(DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10}))
    assert gui_spy.count() == 1
    assert gui_spy.at(0)[0] == action

    # Test no match (wrong value)
    bus.consume(DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 22}))
    # prev event is on so still only 1
    assert gui_spy.count() == 1

    # Test no match (wrong type)
    bus.consume(AppEvent({"action": "showconsole"}))
    assert gui_spy.count() == 1


def test_automation_limit(bus, qtbot, caplog):
    test_limit = 5
    bus.max_automation_count = test_limit

    # Create a recursive rule: App(1) -> App(1)
    recursive_trigger1 = AppEvent({"action": "another test"})
    bus.add_rule(recursive_trigger1, recursive_trigger1)

    app_spy = QSignalSpy(bus.app_event_signal)

    # Connect the broadcast signal back to 'consume' to create a loop
    bus.app_event_signal.connect(bus.consume)

    assert bus.automation_enabled

    # Use try/finally to ensure disconnect
    try:
        with patch('builtins.print') as mock_print:
            bus.consume(recursive_trigger1)
            # Check that the warning was printed
            expected_log = ("core.eventbus", logging.ERROR, "*** Warning automation events exceeded ***")
            assert expected_log in caplog.record_tuples
            #mock_print.assert_called_with("*** Warning automation events exceeded ***")

        # Check assertions
        assert not bus.automation_enabled, "Automation should be disabled"
        assert app_spy.count() == test_limit, f"Signal should fire {test_limit} times"
        
        # The count increments and decrements, so it should be 0 after stack unwinds
        assert bus.automation_count == 0
    finally:
        # Disconnect the signal here, inside the test that connected it
        bus.app_event_signal.disconnect(bus.consume)


# def test_serialization_helpers(bus, qtbot):
#     # Test serialize_event
#     event = AppEvent({"action": "showconsole"})
#     data = serialize_event(event)
#     assert data == {"event_type": "App", "action": "showconsole"}

#     # Test deserialize_event
#     deserialized = deserialize_event(data)
#     assert isinstance(deserialized, AppEvent)
#     assert deserialized.action == "showconsole"

#     # Test with a different type
#     data_dev = {"event_type": "Device", "node_id": 123}
#     deserialized_dev = deserialize_event(data_dev)
#     assert isinstance(deserialized_dev, DeviceEvent)
#     assert deserialized_dev.data['node_id'] == 123


# def test_serialize_event_error(bus, qtbot):
#     class NotAnEvent:
#         pass
#     with pytest.raises(TypeError):
#         serialize_event(NotAnEvent())


def test_save_and_load_rules(bus, test_filename, qtbot, caplog):
    # Add rules
    rule1_event = DeviceEvent({"title": "Test dev event", 'node_id': 100, 'event_id': 10})
    rule1_action = GuiEvent({"title": "Test Gui event"})
    rule2_event = AppEvent({"action": "showconsole"})
    rule2_action = LocoEvent("ERR", {"title": "Test Loco event"})
    bus.add_rule(rule1_event, rule1_action)
    bus.add_rule(rule2_event, rule2_action)

    # Save rules
    # This first call to load_rules is expected to print "File not found"
    # as it just sets the filename
    with patch('builtins.print') as mock_print:
        bus.load_rules(test_filename)
        #mock_print.assert_called_with(f"File not found {test_filename} - [Errno 2] No such file or directory: '{test_filename}'")
        expected_log = ("core.eventbus", logging.WARNING, f"File not found {test_filename} - [Errno 2] No such file or directory: '{test_filename}'")
        assert expected_log in caplog.record_tuples