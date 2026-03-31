from PySide6.QtCore import QRunnable, Slot, Signal, QObject, QThread, QThreadPool
import time
import json
import threading
from locoevent import LocoEvent
from eventbus import event_bus
from automationrule import AutomationRule
from appvar import AppVar
from workersignals import WorkerSignals


# Each step contains a rule commands or sequences
# These are created from a dict and then extracted for the Automation Rule
class AutomationStep:
    # sequence is the sequence this is part of (needed for loops etc.)
    # type is Rule, Var (plus operation), Label, Jump
    # name is the name passed to the rule
    # all other parameters are included in settings
    # rule is not normally provided - unless loading from json
    # Only used if this has an instance of AutomationRule
    def __init__(self, appvariables, step_type, step_name, data={}, rule=None, check_stop_func=None):
        #print (f"\n\nCreating step type {step_type} with {data} rule {rule}")
        self.step_type = step_type
        self.step_name = step_name
        self.data = data
        self.vars = appvariables
        self.rule = rule # Only used if this has an instance of AutomationRule
        self.check_stop = check_stop_func   # Used if the step takes a long time to run (eg. wait)
        
        # If the step_type is a rule then create an automation rule
        if self.rule == None and self.step_type == "Rule":
            #self.rule = AutomationRule(self.step_name, self.step_type, self.data)
            # If ruletype not in the step then look in step.data['data']
            ruletype = self.data.get('ruletype', '')
            if ruletype == "":
                ruletype = self.data['data'].get('ruletype', '')
            #print (f"Creating Automation Rule: {self.step_name} of type {ruletype}")
            self.rule = AutomationRule(self.step_name, ruletype, self.data)
        #  Variables are not created / updated here - only when run

    def get_variable (self):
        if 'variable' in self.data['data']:
            varname = self.data['data'].get("variable", "")
            #print (f"Variable name found: {varname}")
            return varname
        return ""
            
    def parse_var (self):
        # Copy data dict to run_data - which allows for any variable substitutions
        run_data = {}
        var_data = False # If parse a variable then set to True to indicate updated
        for key, value in self.data.items():           
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                var_data = True
                var_name = value[1:-1]
                if vars == None:
                    print ("Variable detected {var_name} but no AppVar created")
                    continue
                # If the value doesn't exist then it will be None
                run_data[key] = self.vars.get_variable(var_name)
            else:
                run_data[key] = value
        # If a substitution has been made then temporarily add it to the dict
        # so that the calling method knows a substitution has been made
        if var_data:
            run_data["var_data"] = True
        return run_data

    # If any variable tokens are found they are handled in the run        
    def run (self, notify_signal, notify_wait_signal, status_signal, locos):
        run_data = self.parse_var()
        #print (f"Step {self.step_name} of type {self.step_type} running with data {run_data}")
        # Now use run_data - which has any variables parsed
        if self.step_type == "App":
            app_command = run_data['data'].get("command", "")
            if app_command == "Set Variable":
                # check we have an appvar
                if self.vars == None:
                    print ("Warning: Attempt to set a variable with no AppVar configured")
                    return
                var_name = run_data['data'].get("variable", "")
                var_value = run_data['data'].get("value", "")
                self.vars.set_variable(var_name, var_value)
            elif app_command == "Increment Variable":
                # check we have an appvar
                if self.vars == None:
                    print ("Warning: Attempt to increment a variable with no AppVar configured")
                    return
                var_name = run_data['data'].get("variable", "")
                inc_value = run_data['data'].get("value", 1)
                self.vars.inc_variable(var_name, inc_value)
            elif app_command == "Notify User":
                message = run_data['data'].get("message", "")
                blocking = run_data['data'].get("blocking", "True")

                if blocking == "True" or blocking == True:
                    resume_event = threading.Event()
                    notify_wait_signal.emit("User Notification", message, resume_event)
                    # Wait for the user to click OR for the stop flag to be raised
                    while not resume_event.wait(timeout=0.1):
                        if self.check_stop and self.check_stop():
                            print ("User notification interrupted by stop signal")
                            # Optional: You might want to emit a signal here to auto-close 
                            # the user notification dialog since the task is dead.
                            return
                else:
                    notify_signal.emit("User Notification", message)
            elif app_command == "Wait":
                # Need to check every 0.1 sec for stop signal
                total_delay = int(run_data['data'].get("delay", 1))
                elapsed = 0
                while elapsed < total_delay:
                    if self.check_stop and self.check_stop():
                        print ("Wait interrupted by stop signal")
                        break
                    time.sleep(0.1)
                    elapsed += 0.1
            else:
                print (f"Unknown App command: {app_command}")
        elif self.step_type == "Rule":
            #print (f"Running Automation Rule: {self.rule}")
            # check any value fields for variables
            if ("var_data" in run_data and run_data["var_data"]):
                # remove it from the dict
                del run_data['var_data']
                # If new data (ie. variable) then replace data within the rule object
                self.rule.run(run_data)
            else:
                self.rule.run()
        # Variable can be "set" (which create or set value)
        # or "inc" - allows increase without needing to query current value
        elif self.step_type == "Var":
            # check we have an appvar
            if self.vars == None:
                print ("Warning: Attempt to set a variable with no AppVar configured")
                return
            if run_data["action"] == "set":
                self.vars.set_variable(run_data["varname"], run_data["value"])
            elif run_data["action"] == "inc":
                # value is optional for inc - default to 1
                self.vars.inc_variable(run_data["varname"], run_data.get("value",1))
        elif self.step_type == "Wait":
            # default 1 second
            delay_time = self.data.get("time", 1)
            # If this is a basic wait / delay (which is default) then sleep and continue
            waittype = self.data.get("waittype", "delay")
            if waittype == "delay":
                time.sleep(delay_time)
            else:
                loop_num = 0
                # max_loop 0 means no maximum (keep looping)
                # this is not subject to variable substitution 
                max_loop = self.data.get("maxloop", 0)
                # Create a loop until the condition is met
                while self.test_condition():
                    time.sleep(delay_time)
                    loop_num += 1
                    if max_loop > 0 and loop_num > max_loop:
                        break
        elif self.step_type == "Loco":
            # Loco step 
            # Is the Loco connected
            #Todo check loco connected and active
            loco_id = self.get_loco_id()
            print (f"Running Loco Step: {self.step_name} with data {run_data}, locos {locos}")
            loco_command = run_data['data'].get("action", "")
            #Todo Add actions
            if loco_command == "Function":
                print ("Loco function - implement here")
            elif loco_command == "Set Speed":
                print ("Set speed - implement here")
            elif loco_command == "Stop":
                print (f"Stopping loco {loco_id}")
                event_bus.publish(LocoEvent('api', {
                    'command': 'stop',
                    'loco_id': loco_id
                }))
                #self.api.start_request(self.api.vlcb.loco_speeddir(self.control_loco.get_session(), self.control_loco.get_speeddir()))
            else:
                print (f"Unknown Loco command: {loco_command}")

    def get_loco_id (self):
        """ If step uses loco then return loco, else return "" """
        if self.step_type == "Loco":
            return self.data['data'].get("locoid", "")
        return ""


    # Test condition is used for any check operations eg. 
    # "test": "equals" "==" or "lessthan" "<" or "greaterthan" ">", or 
    # "notequal" "!=" or "<=" or ">=" (no long version of those)
    # Returns True / False
    def test_condition (self):
        #Jump can be either variable & value - or value1 & value2
        # if we have variable and value then convert to value1 and value2
        # this will remove any values already in value1 and value2
        if 'data' in self.data and 'variable' in self.data['data'] and 'value' in self.data['data']:
            var_name = self.data['data'].get("variable", "")
            value1 = self.vars.get_variable(var_name)
            value2 = self.data['data'].get("value", "")
            # if both value1 and value2 are valid then put into run_data
            if value1 != None and value2 != None:
                self.data['data']['value1'] = value1
                self.data['data']['value2'] = value2
        # substitute in any variables
        run_data = self.parse_var()
        # Now test the condition
        condition = run_data.get("test")
        value1 = run_data.get("value1")
        value2 = run_data.get("value2")
        
        #print (f"Test {value1} {condition} {value2}")
        
        # if any of the values are not valid then return False
        if (condition == None or value1 == None or value2 == None):
            return False

        try:
            # Now perform the check
            # For equality / no equal then compare as a string - rest convert to float
            # This allows both numeric and text comparisons
            if (condition == "equal" or condition == "=="):
                return (str(value1) == str(value2))
            elif (condition == "notequal" or condition == "!="):
                return (str(value1) != str(value2))
            elif (condition == "lessthan" or condition == "<"):
                return (float(value1) < float(value2))
            elif (condition == "greaterthan" or condition == ">"):
                return (float(value1) > float(value2))
            elif (condition == ">="):
                return (float(value1) >= float(value2))
            elif (condition == "<="):
                return (float(value1) <= float(value2))
            else:
                return False
        except Exception as e:
            return False
        
    def get_type (self):
        return self.step_type
        
    def get_name (self):
        return self.step_name

    def __repr__(self):
        return f"Step: {self.step_type}: {self.step_name}"
    
    

    def to_dict(self) -> dict:
        """Convert the object to a dictionary, excluding 'appvar' from data."""
        #print (f"\nReturning AutomationStep as dict {self.data}")
        #filtered_data = {k: v for k, v in self.data.items() if k != 'appvars'}
        #print ("Converting Step to Dict")
        #print (f"Filtered data {filtered_data}")
        # return_dict = {
        #     "type": self.step_type,
        #     "name": self.step_name,
        #     "data": self.data,
        #     "rule": self.rule.to_dict() if self.rule else None
        # }
        return_dict = self.data.copy()
        return_dict["rule"] = self.rule.to_dict() if self.rule else None

        #print (f"Return automation step {return_dict}")
        return return_dict
        

    # Json created at Sequence
    #def to_json(self) -> str:
    #    """Serialize the object to a JSON string."""
    #    return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def from_dict(cls, d: dict, parent = None):
        """Create an object from a dictionary."""
        return cls(
            parent=parent,
            step_type=d.get("step_type", ""),
            step_name=d.get("step_name", ""),
            data=d.get("data", {}),
            rule=d.get("rule", None)
        )

    @classmethod
    def from_json(cls, json_str: str, parent = None):
        """Deserialize from JSON string to object."""
        d = json.loads(json_str)
        return cls.from_dict(d, parent)
