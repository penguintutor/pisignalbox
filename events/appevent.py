# Tracks events for app - open, close, update windows
# Used to update api objects from events
import logging
from .event import Event

logger = logging.getLogger(__name__)

class AppEvent (Event):
    def __init__(self, data_dict=None):
        if data_dict is None:
            data_dict = {}
        self.data = data_dict
        # Allow action within the data or as a separate data object
        # New preferred method is for it to be within self.data['data']['action']
        if "action" in self.data:
            self.action = self.data['action']
        else:
            self.action = self.data['data'].get('action')
        self.data['event_type'] = "App"
        
    def type (self):
        return "App"
           
    def get_response(self):
        return self.data.get('response', "")
        
    # Optional methods for safe return of optional values
    def get_loco_id(self):
        return self.data.get('loco_id')
