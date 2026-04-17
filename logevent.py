""" Used for logging activities 
#Todo
Includes app logs (not yet added but to be saved)
Includes automation events which are shown in the automation console (not saved - perhaps future addition)
"""

"""
# Alert level is based on linux priorities
Numerical CodeSeverity Description
0 Emergency App is unusable. (Highest Priority app crash)
1 Alert Action must be taken immediately. (e.g Connecton failure)
2 Critical Critical conditions (None currently defined).
3 Error Non-critical error conditions (Error communicating with CBUS).
4 Warning Warning conditions.
5 Notice Normal but significant events (Start / end automation sequence).
6 Informational Routine operational messages (automation step).
7 Debug Detailed info for troubleshooting. (Lowest Priority)
"""

from event import Event

class LogEvent (Event):
    def __init__(self, data_dict={}):
        self.data = data_dict
        # log_type eg. Automation or App
        self.log_type = self.data['type']
        # 0 to 7 (see above)
        self.log_level = self.data['level']
        self.data['event_type'] = "Log"
        
    def type (self):
        return "Log"
           
    def get_response(self):
        return self.data.get('response', "")
        
    # Optional methods for safe return of optional values
    def get_description(self):
        return self.data.get('description')
