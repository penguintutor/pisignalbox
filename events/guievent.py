# Tracks events for graphics objects
# If a GUI object (including layout needs to trigger request then use this)
# Used by layout objects and other GUI objects (eg. console window)

# 'name': self.name, 'value': self.state_value

from .event import Event

class GuiEvent(Event):
    def __init__(self, data_dict):
        self.event_type = "Gui"
        self.data = data_dict
        if not 'event_type' in self.data:
            self.data['event_type'] = self.event_type

    def matches(self, other_event):
        #print (f"GuiEvent matches called {other_event}")
        #print (f"Self {self.data} Other {other_event.data}")
        #print (f"Self node {self.get_node()} Other node {other_event.get_node()}")
        if self.get_node() == other_event.get_node():
            #print (f"Self value {self.get_value_int()} Other value {other_event.get_value()}")
            if self.get_value_int() == other_event.get_value():
                return True
        return False
        
    def event_type (self):
        return "Gui"
    
    def get_type (self):
        return "Gui"
    
    def get_node (self):
        if 'node' in self.data:
            return self.data['node']
        return "Gui node"
    
    def get_node_object (self):
        return self.data.get('node_object', None)
    
    def get_event (self):
        if 'event' in self.data:
            return "Gui event"
        else:
            return 0
    
    def get_value (self):
        if "value" in self.data:
            return self.data['value']
        else:
            return "None"
        
    def get_value_int (self):
        if "value" in self.data:
            if isinstance(self.data['value'], int):
                return self.data['value']
            # If not a number then try for "on"
            if self.data['value'] == "on":
                return 2
            elif self.data['value'] == "off":
                return 1
        return 0    
    
    def __str__ (self):
        return (f"{self.get_type()} {self.get_node()} {self.get_event()} {self.get_value()}")