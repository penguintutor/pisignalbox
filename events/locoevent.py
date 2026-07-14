# Tracks events against loco
# When we receive / send an event do we need to update devices and corresponding objects
class LocoEvent:
    
    # List of type of events related to locos.
    # This is not exhaustive - only events that can be requested
    # As a class variable so it can be used for GUI menus prior to creating event
    event_types = [
        "Set Speed",
        "Set Direction",
        "Stop",
        # Function includes sound etc. In the Loco view these are mapped based on the loco, but in
        # automation then the Loco may be changed and function may differ
        "Function",		# In menu this may be remapped to F1 / F2 etc. - perhaps spinbox
        "All Stop"		# Special case if using CBUS controller which has all stop - still need to have a session with a loco first
        ]
    # Alternative "api"           # Request to api - request to be included in event_data
    # eg. event_data['command'] = "share" 
    # not included in event_types list as not user selectable
    # Also event_type could be related to allocate - eg. PLOC
        
    def __init__(self, event_type, event_data):
        self.event_type = event_type
        self.data = event_data # dict

    def type (self):
        return "Loco"
    
    @classmethod
    def get_action_names(cls):
        #print (f"Returning Loco actions {cls.event_types}")
        return cls.event_types
    
    # Action can be from data - but if api then return "api" instead
    def get_action(self):
        if self.event_type == "api":
            return "api"
        # Otherwise return action - or fallback to "Loco"
        return self.data.get("action", "Loco")
    
    def get_value(self):
        return self.data.get("value", 0)

    # Not all events include loco_id / command etc - returns None if not included
    def get_loco_id(self):
        if "loco_id" in self.data:
            return self.data.get("loco_id")
        # If event is created from a VLCB entry then it may be uppercase first letter
        return self.data.get("Loco_id")
    
    # If doesn't include loco_id then would normally provide session id
    def get_session_id(self):
        return self.data.get("session")

    # If type is ID then should include command - returns "" if not included
    def get_command(self):
        return self.data.get("command", "")
    
    # Argument is any value isn self.data - takes key
    def get_arg(self, key):
        return self.data.get(key, "")
    
    def matches (self, event):
        if self.get_type() == event.get_type():
            if self.get_action() == event.get_action() and self.get_value() == event.get_value():
                return True
        return False