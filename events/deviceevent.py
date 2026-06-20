# Tracks events against devices.
# When we receive / send an event do we need to update devices and corresponding objects
from .event import Event

# event_data is a dictionary of key values
class DeviceEvent (Event):
    def __init__(self, event_data):
        """ Create event related to Device (VLCB) 
        event_data is provided as a dict
        Typically it will have either node details "node", "event", "value"
        Or will provide "node_object" which contains those details
        If an action is not provided then treat as a "device" action
        indicating it is directly related to a device hardware trigger
        Other actions include "new_node", "update_node", "new_ev", "update_ev"
        Values set in the dict will typically override ones in the object
        """
        super().__init__()
        # Set type after parent constructor
        self.data = event_data
        self.data["event_type"] = "VLCB"
        if "action" not in self.data:
            self.data["action"] = "device"

    # Uses getters to allow different data (eg. node vs node_id)
    # Node may be friendly name
    # If not node then return node_id instead
    # always return string
    def get_node (self):
        if 'node' in self.data:
            return self.data['node']
        elif 'node_id' in self.data:
            return str(self.data['node_id'])
        elif 'node_object' in self.data:
            return self.data["node_object"].get_name()
        else:
            return "No node defined"
    
    # Always node_id number
    def get_node_id (self):
        if node_id in self.data:
            return self.data['node_id']
        elif 'node_object' in self.data:
            return self.data["node_object"].get_node_id()
        else:
            return "No node id defined"
    
    # Some events include the node or ev object 
    # Eg. New node
    def get_node_object (self):
        return self.data.get("node_object")
    
    def get_ev_object (self):
        return self.data.get("ev_object")
    
    # could be id or friendly name
    def get_event (self):
        if 'event' in self.data:
            return self.data['event']
        elif 'event_id' in self.data:
            return str(self.data['event_id'])
        if 'ev_object' in self.data:
            return self.data["ev_object"].get_name()
        else:
            return ("No event_id defined")
    
    # Always event_id number
    def get_event_id (self):
        return self.data['event_id']
        
    def get_value (self):
        if 'value' in self.data:
            return self.data['value']
        # Todo - this returns node_id rather than actual state / value
        elif 'ev_object' in self.data:
            return self.data["ev_object"].get_name()
        else:
            return None
        
        
    # Does this event match
    def matches (self, event):
        if self.get_node() == event.get_node() or self.get_node_id() == event.get_node_id():
            if self.get_event_id() == event.get_event_id() and self.get_value() == event.get_value():
                return True
        return False
        
    def __str__ (self):
        return (f"{self.get_type()} {self.get_node()} {self.get_event()} {self.get_value()}")