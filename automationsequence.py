from PySide6.QtCore import QRunnable, Slot, Signal, QObject, QThread, QThreadPool
import time
import json
from automationstep import AutomationStep
from automationrule import AutomationRule
from appvar import AppVar
from workersignals import WorkerSignals


# Automation routine, composed of multiple steps
# Each step is a rule, command or launch another sequence
# These are provided as a list with each entry as a dict with the AutomationStep created in the init
# Settings is used to pass the locos,
class AutomationSequence (QRunnable):
    def __init__(self, appvariables, title, steps, settings = {}, check_stop_func=None):
        #print (f"\n\nCreating AutomationSequence titled {title} with steps {steps} and settings {settings} and check_stop_func={check_stop_func}")
        super(AutomationSequence, self).__init__()
        # steps are provided as a list so save as list_steps, but then use self.steps when AutomationStep object created
        list_steps = steps
        #self.mainwindow = mainwindow
        self.vars = appvariables
        self.title = title
        self.steps = []  # List of AutomationStep objects
        self.settings = settings
        #self.num_locos = settings.get('num_locos', 0) # 0 to 3 locos required
        #self.vars = settings.get("appvar", {})
        # Store the index of any labels to allow jumps (loops)
        # If order changes then labels needs to be updated
        self.labels = {}
        self.signals = WorkerSignals()
        self.active = False		# Set to true when starting, set back to false to stop
        self.check_stop = check_stop_func
        if self.check_stop is None:
            print ("No stop function provided")
            self.check_stop = lambda: False
        
        # Each step contains self.step = {"step_type": rule_type, "step_name": step_name, data : data_dict}
        #print ("Loading into Auatomation Sequence")
        for i, step_data in enumerate(list_steps):
            #print (f"Adding {step_data} to sequence")
            #print (f"{step_data}")
            # If it's a label then add to dict of labels
            if step_data['type'] == "Label":
                self.labels[step_data['name']] = i
            ## Variables need to be added through automationmanager to use the mainwindow and so be included in device_model
            # if step_data['type'] == "App":
            #     print (f"App Step data: {step_data}, var {self.vars}")
            #     # If it's a set variable command then ensure variable exists
            #     if step_data['data'].get("command", "") == "Set Variable":
            #         var_name = step_data['data'].get("variable", "")
            #         print (f"Variable name {var_name}")
            #         if not self.vars.is_variable(var_name):
            #             self.vars.add_variable(var_name, "")
            #             print (f"Adding variable {var_name} to AppVar from AutomationSequence")
            #print (f"Step data {step_data}")
            #print (f"Name {step_data['name']}")
            #print (f"Variables {self.vars.variables}")
            # Rule is blank (between step_data and check_stop_func)
            self.steps.append(AutomationStep(self.vars, step_data['type'], step_data['name'], step_data, check_stop_func=self.check_stop))
         
    def get_variables (self):
        vars = []
        for step in self.steps:
            variable = step.get_variable()
            if variable != "":
                vars.append(variable)
        return vars

    @Slot()
    def run (self, seq_num=None):
        print (f"Starting sequence {self.title}")
        #self.signals.status.emit(f"Starting sequence {self.title}")
        self.active = True
        position = 0
        while position < len(self.steps):
            # Check if we need to stop
            if self.check_stop():
                print ("AutomationSequence stopping as requested")
                self.active = False
                break
            # If set to false then stop
            if self.active == False:
                break
            #print (f"Step {position}")
            # If it's a label then ignore
            if self.steps[position].step_type == "Label":
                pass
            elif self.steps[position].step_type == "Jump":
                # parse the condition and get the result
                result = self.steps[position].test_condition()
                # If the result is in the labels then jump to that 
                if result != None and result == True:
                    #print ("Test true")
                    label = self.steps[position].data.get("label")
                    #print (f"Label {label}")
                    if label != None and label in self.labels:
                        #print ("Jump to label")
                        position = self.labels[label]
                        continue
                # otherwise jump is ignored (eg. if loop then until no longer met)
            else:
                # Otherwise run it  
                self.steps[position].run(self.signals.notify, self.signals.notify_wait,self.signals.status)
            position += 1
        # Emit a signal to indicate the thread has finished
        self.signals.finished.emit(seq_num)
        
    # return info about the sequence in the form of a dict
    # does not include steps (see get_steps)
    def get_info(self):
        #title, numlocos
        return {"title": self.title} 
        
    # Return the steps from the sequence
    def get_steps(self):
        return self.steps

    def to_dict(self) -> dict:
        """Convert AutomationSequence to dict."""
        #print ("Creating AutomationSequence dict")
        return {
            "title": self.title,
            "settings": self.settings,
            "steps": [step.to_dict() for step in self.steps]
        }

    def to_json(self) -> str:
        """Serialize AutomationSequence to JSON string."""
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def from_dict(cls, d: dict, appvariables=None, check_stop_func=None):
        """Create AutomationSequence from dict."""
        #print (f"Loading AutomationSequence from dict {check_stop_func}")
        #steps = [AutomationStep.from_dict(s, self) for s in d.get("steps", [])]
        steps = d.get("steps", [])
        return cls(
            appvariables=appvariables,
            title=d.get("title", ""),
            steps=steps,
            settings=d.get("settings", {}),
            check_stop_func=check_stop_func
        )

    #def __init__(self, mainwindow, title, list_steps, settings = {}):
    # from json also needs mainwindow - pass as optional argument
    @classmethod
    def from_json(cls, json_str: str, appvariables=None, check_stop_func=None):
        print (f"Loading AutomationSequence from JSON")
        """Deserialize JSON string to AutomationSequence."""
        d = json.loads(json_str)
        return cls.from_dict(d, appvariables, check_stop_func=check_stop_func)


    def __repr__(self):
        return f"AutomationSequence (title, steps, settings, check_stop_func=self.check_stop): {self.title}"
    

    def __str__(self):
        return f"{self.title}"
    
    
