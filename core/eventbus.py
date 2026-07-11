# Event Driven architecture - EDA
# Bus to handle events
# Also handles event forwarding signals based on registered event associations

from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot
import json
from events import Event, DeviceEvent, AppEvent, GuiEvent, LocoEvent, TimerEvent, VarEvent, LogEvent

# The serialize_event function must be defined before it is used.
def serialize_event(obj):
    if isinstance(obj, Event):
        return obj.__dict__()
    print ("Trying to serialize from EventBus")
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def deserialize_event(data):
    return EventBus.event_map[data["event_type"]] (data)



class EventBus(QObject):
    # Generic signals for different event types.
    # The payload of the signal is the event object
    # To register for the event notifications connect to these signals 
    app_event_signal = Signal(AppEvent)
    device_event_signal = Signal(DeviceEvent)
    gui_event_signal = Signal(GuiEvent)
    loco_event_signal = Signal(LocoEvent)
    timer_event_signal = Signal(TimerEvent)
    var_event_signal = Signal(VarEvent)
    log_event_signal = Signal(LogEvent)

    # More specialised 
    # Trigger when add / update an entry - from VLCB (Device)
    node_updated_signal = Signal(DeviceEvent)
    layout_updated_signal = Signal(GuiEvent)

    
    # Map the Event Type to the STRING name of the signal
    _route_map = {
        AppEvent: "app_event_signal",
        DeviceEvent: "device_event_signal",
        GuiEvent: "gui_event_signal",
        LocoEvent: "loco_event_signal",
        TimerEvent: "timer_event_signal",
        VarEvent: "var_event_signal",
        LogEvent: "log_event_signal"
    }

    # Is automation enabled. If not then don't apply rules.
    # If excessive calls (eg. excessive recursion) then stop automatically
    automation_enabled = True
    # Track number of automation events
    automation_count = 0
    max_automation_count = 100
    
    # Store registered event forwarding rules
    # Each entry contains a list consisting of [event, action]
    event_rules = []

    # Map to Classes
    event_map = {
        'VLCB': DeviceEvent,
        'Device': DeviceEvent,
        'Loco': LocoEvent,
        'App': AppEvent,
        'Gui': GuiEvent,
        'Timer': TimerEvent,
        'Var': VarEvent,
        'Log': LogEvent
        }

    # The _instance and __new__ ensure that this is always a singleton
    # Technically not needed as long as always importing as event_bus
    # but provides additional check
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
        return cls._instance

    # Publish is used to send an event notification which originates in the application
    # It can be called by other classes (eg. GUI notification)
    # It is also called from the API (eg. on receive loco acquire)
    # It first calls apply_rules which will trigger an rule events
    # then broadcsts to the appropriate signal
    # To register an event publish with the appropriate event type
    def publish(self, event):
        # Apply automation rules by consuming the input
        self.consume(event)
        #print (f"Broadcasting event: {event}")
        # broadcast the signal
        self.broadcast(event)
        
    
    # Broadcast signal
    def broadcast(self, event):
        # Broadcast the event
        # Look up the string name of the target signal
        signal_name = self._route_map.get(type(event))
        
        if signal_name:
            # Use getattr(self, ...) to grab the BOUND signal, which has .emit()
            target_signal = getattr(self, signal_name)
            target_signal.emit(event)
        else:
            print(f"Warning: Unhandled event type published: {type(event)}")
        
    # Consume is used to handle incoming events
    # It does not publish a new event
    # Called directly from CBUS events, or as part of publish to act as a consumer
    def consume(self, event):
        # Apply automation rules
        # (includes internal mapping - eg. from CBUS to gui)
        if self.automation_enabled:
            self.apply_rules (event)

    def del_entry (self, rule_id):
        del self.event_rules[rule_id]

    # Apply automation rules based on the event
    def apply_rules (self, event):
        # Add number of events
        self.automation_count += 1
        # Have we reached maximum
        if self.automation_count >= self.max_automation_count:
            print ("*** Warning automation events exceeded ***")
            # Todo call a gui event to notify user
            self.automation_enabled = False
            # Allowed to continue for this event, but then stop
        
        # Get the event type to save making multiple calls to type method
        event_type = type(event)
        # Apply across all rules
        #print (f"Event {event}")
        for rule in self.event_rules:
            # rule[0] is the event we are monitoring for
            if isinstance(rule[0], event_type):
                # Matches same type pass to the event to see if this matches
                # This allows each event type to look for certain features
                if rule[0].matches(event):
                    # Broadcast rather than publish
                    # Automation will be received from the incoming deviceevent
                    self.broadcast (rule[1])
        # Decrement once rules applied
        self.automation_count -= 1

    def add_rule (self, event, action):
        #print (f"Event {event.__class__.__name__} : Action {action.__class__.__name__}")
        self.event_rules.append([event, action])
        #print (f"Last rule {self.event_rules[-1]}")
        
    def num_rules (self):
        return len(self.event_rules)
    
    # Load rules file must include a filename
    # which is then stored allowing save_rules to be used without a filename
    # filename should be full path - created in mainwindow
    def load_rules (self, filename):
        self.rules_filename = filename
        try:
            with open(self.rules_filename, 'r') as data_file:
                raw_data = json.load(data_file)
                #print (f"Data {new_data}")
                
                self.event_rules = [
                    [deserialize_event(event_data) for event_data in rule_pair]
                    for rule_pair in raw_data
                ]

        except Exception as e:
            # Could be new file
            print (f"File not found {self.rules_filename} - {e}")
        

    def save_rules (self):
        try:
            with open(self.rules_filename, 'w') as data_file:
                #json.dump(self.event_rules, data_file, indent=4)
                json.dump(self.event_rules, data_file, default=serialize_event, indent=4)
                


        except Exception as e:
            # Could be new file
            print (f"Save failed {self.rules_filename} - {e}")

    def __del__(self):
        print("⚠️ EventBus WAS DESTROYED")


# Access the singleton EventBus
event_bus = EventBus()
