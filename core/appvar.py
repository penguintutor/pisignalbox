## App var used for special global user defined variables
# that can be used across the application. 
# This allows for example a rule to set a value, 
# which can be displayed in the track view, 
# then used in the automation
# Therefore this is created as a pythonic singleton like instance

# make this threadsafe
import threading
from .eventbus import event_bus
from events import VarEvent

# Always use getters and setters as they can update model and/or trigger events if required
class AppVar():
    #def __init__ (self, varsignal):
    def __init__ (self):
        # Variables in a dict with the variable name as the key
        self._variables={}
        self._lock = threading.Lock()

    def add_variable (self, variable_name, initial_value="", send_event=True):
        # send_event is whether to trigger an event, eg. during initialisation
        # Don't want an event as we add each individual entry
        #print ("Do not use - add through mainwindow instead")
        # print (f"Variables {self.variables}")
        # print (f"Adding variable {variable_name} with initial value '{initial_value}'")
        with self._lock:
            if variable_name not in self._variables:
                self._variables[variable_name] = initial_value
        
        if send_event:
            var_event = VarEvent ({"name":variable_name, "value":initial_value, "event_type": "new"})
            event_bus.broadcast(var_event)
        # print (f"New variables list: {self.variables}")

    def is_variable (self, variable_name):
        return variable_name in self._variables

    def get_variable (self, variable_name):
        # threads-safe read
        with self._lock:
            return self._variables.get(variable_name, None)

    def get_variable_names (self) -> list[str]:
        """ Returns variable names as a List """
        with self._lock:
            return list(self._variables)
        
    def set_variable (self, variable_name, new_value, send_event=True):
        # Update within a mutex block
        with self._lock:
            # Does variable already exist - if so need to trigger new event (if not then change event)
            # If event=false then don't send a broadcast event
            if variable_name in self._variables:    
                event_type = "change"
            else:
                event_type = "new"
            self._variables[variable_name] = new_value
        var_event = VarEvent ({"name":variable_name, "value":new_value, "event_type": event_type})

        # Released mutex send event
        if send_event:
            event_bus.broadcast(var_event)
        # Return value - to be consistant with inc_variable
        return new_value
        
    # Increase variable - if variable does not exist or is not a number then replace with 1
    # Returns new variable
    def inc_variable (self, variable_name, inc_amount=1):
        with self._lock:
            if variable_name in self._variables:    
                event_type = "change"
            else:
                event_type = "new"
            # Use try and if unable to increase value (new or not number) then set to 1
            try:
                #print (f"Updating {variable_name} adding {inc_amount} to {self.variables[variable_name]}")
                # If inc_amount is not already a number (most likely a string from dialog) then convert to float
                if isinstance (inc_amount, str):
                    inc_amount = float(inc_amount)
                self._variables[variable_name] += inc_amount
            except:
                #print ("Exception")
                self._variables[variable_name] = 1
        # Mutex released - send event
        var_event = VarEvent ({"name":variable_name, "value":self._variables[variable_name], "event_type": event_type})
        event_bus.broadcast(var_event)
        return self._variables[variable_name]
    
global_app_vars = AppVar()