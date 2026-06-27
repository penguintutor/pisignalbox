from PySide6.QtCore import QRunnable, Slot, Signal, QObject, QThread, QThreadPool
import time
import json
from automationstep import AutomationStep
from automationrule import AutomationRule
from core import WorkerSignals
from events import LogEvent
from core import event_bus
# If need global_app_vars (tends to be in the step)
from core import global_app_vars


# Automation routine, composed of multiple steps
# Each step is a rule, command or launch another sequence
# These are provided as a list with each entry as a dict with the AutomationStep created in the init
# Settings is used to pass the locos,
class AutomationSequence (QRunnable):
    def __init__(self, title, steps, settings = None, check_stop_func=None):
        #print (f"\n\nCreating AutomationSequence titled {title} with steps {steps} and settings {settings} and check_stop_func={check_stop_func}")
        super(AutomationSequence, self).__init__()
        # steps are provided as a list so save as list_steps, but then use self.steps when AutomationStep object created
        list_steps = steps
        #self.mainwindow = mainwindow
        #self.vars = appvariables
        self.title = title
        self.steps = []  # List of AutomationStep objects
        self.settings = settings or {}
        #print (f"AutomationSequence {self.vars}")
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
            event_bus.broadcast(LogEvent(
                {'type':"Automation",
                'level':3, # Non critical error
                'sequence': self.title,
                'step': "00 - Init",
                'description': "No stop function provided"
                }
            ))
            self.check_stop = lambda: False
        
        # Each step contains self.step = {"step_type": rule_type, "step_name": step_name, data : data_dict}
        #print ("Loading into Auatomation Sequence")
        for i, step_data in enumerate(list_steps):
            #print (f"Adding {step_data} to sequence")
            #print (f"{step_data}")
            # If it's a label then add to dict of labels
            if step_data['type'] == "Label":
                self.labels[step_data['data'].get('labelid')] = i
            ## Variables need to be added through automationmanager to use the mainwindow and so be included in managers
            self.steps.append(AutomationStep(self.title, step_data['type'], step_data['name'], step_data, check_stop_func=self.check_stop))

    def get_locos (self):
        """ Get a list of all locos in the sequence
        used by MW when starting automation to check what locos need
        to be allocated """
        locos = []
        for step in self.steps:
            # Gets a loco_id from the step
            # Todo - does this need to be changed to a loco object?
            new_loco = step.get_loco_id()
            if new_loco != "" and not new_loco in locos:
                locos.append (new_loco)
        return locos
         
    def get_variables (self):
        vars = []
        for step in self.steps:
            variable = step.get_variable()
            if variable != "":
                vars.append(variable)
        return vars

    @Slot()
    def run (self, seq_num=None, locos={}):
        #print (f"Starting sequence {self.title}, locos {locos}")
        log_description = f"Starting sequence: {self.title}"
        if len(locos) > 0:
            # Get loco IDs and names as strings
            loco_strings = (f"{key}={value.get_display_name()}" for key, value in locos.items())
            # join the locos comma separated
            log_description += ", locos: " + ", ".join(loco_strings)

        event_bus.broadcast(LogEvent(
            {'type':"Automation",
             'level':5, # Normal major event
             'sequence': self.title,
             'step': "00 - Start",
             'description': log_description
             }
        ))
        """ This is handled in the dialog - left here in case 
        want to add additional check in future"""
        # If there are any locos then make sure we can 
        # acquire to them otherwise quit the sequence
        # Doesn't work -loco is str not object
        # Instead updated autolocodialog to acquire before run is called
        # If enable then would need to handle error and provide return point
        # for loco in locos:
        #     # Is this loco already connected
        #     print (f"Checking loco {loco}")
        #     if loco.is_acquired():
        #         print("acquired")
        #         continue
        #     # if not then need to acquire
        #     loco_event = LocoEvent("api", {
        #         "command":"acquire",
        #         "loco_id":loco.loco_id
        #         })
        #     event_bus.broadcast(self.event)

        
        #self.signals.status.emit(f"Starting sequence {self.title}")
        self.active = True
        position = 0
        while position < len(self.steps):
            # Check if we need to stop
            if self.check_stop():
                #print ("AutomationSequence stopping as requested")
                event_bus.broadcast(LogEvent(
                    {'type':"Automation",
                    'level':5, # Normal major event
                    'sequence': self.title,
                    'step': f"{position+1:02d} - Stop",
                    'description': "Stopping sequence"
                    }
                ))
                self.active = False
                break
            # If set to false then stop
            if self.active == False:
                break
            # If it's a label then ignore
            if self.steps[position].step_type == "Label":
                event_bus.broadcast(LogEvent(
                    {'type':"Automation",
                    'level':6, # Information
                    'sequence': self.title,
                    'step': f"{position+1:02d} - Label",
                    'description': f"Label {self.steps[position].get_name()}"
                    }
                ))
                pass
            elif self.steps[position].step_type == "Jump":
                # parse the condition and get the result
                result = self.steps[position].test_condition()
                condition_string = self.steps[position].test_condition_str()
                # If the result is in the labels then jump to that 
                if result != None and result == True:
                    #print ("Test true")
                    label = self.steps[position].get_value("labelid")
                    #print (f"Label {label}")
                    if label != None and label in self.labels:
                        #print ("Jump to label")
                        event_bus.broadcast(LogEvent(
                            {'type':"Automation",
                            'level':5, # Normal major event
                            'sequence': self.title,
                            'step': f"{position+1:02d} - Jump",
                            'description': f"Jump to {label} = {self.labels[label]} - Condition {condition_string}"
                            }
                        ))
                        position = self.labels[label]
                        continue
                    else:
                        print (f"Invalid label {label} - from {self.labels}")
                        # otherwise jump is ignored (eg. if loop then until no longer met)
                        event_bus.broadcast(LogEvent(
                            {'type':"Automation",
                            'level':4,  # Warning
                            'sequence': self.title,
                            'step': f"{position:02d} - Invalid Jump",
                            'description': f"Jump to unknown label {label}"
                            }
                        ))
                #else condition is not met
                else: 
                    event_bus.broadcast(LogEvent(
                        {'type':"Automation",
                        'level':6, # Info
                        'sequence': self.title,
                        'step': f"{position+1:02d} - Jump",
                        'description': f"Condition not met - {condition_string}"
                        }
                    ))
            else:
                # Otherwise run it  
                event_bus.broadcast(LogEvent(
                    {'type':"Automation",
                    'level':6, # Normal routine
                    'sequence': self.title,
                    'step': f"{position+1:02d} - {self.steps[position].get_type()}",
                    'description': f"{self.steps[position].get_name()}"
                    }
                ))
                self.steps[position].run(self.signals.notify, self.signals.notify_wait,self.signals.status, locos)
            position += 1
        # Emit a signal to indicate the thread has finished
        event_bus.broadcast(LogEvent(
            {'type':"Automation",
            'level':5, # Normal major event
            'sequence': self.title,
            'step': f"{position+1:02d} - End",
            'description': f"End of sequence {self.title}"
            }
        ))
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
    def from_dict(cls, d: dict, check_stop_func=None):
        """Create AutomationSequence from dict."""
        #print (f"Loading AutomationSequence from dict {check_stop_func}")
        #steps = [AutomationStep.from_dict(s, self) for s in d.get("steps", [])]
        steps = d.get("steps", [])
        return cls(
            title=d.get("title", ""),
            steps=steps,
            settings=d.get("settings", {}),
            check_stop_func=check_stop_func
        )

    #def __init__(self, mainwindow, title, list_steps, settings = {}):
    # from json also needs mainwindow - pass as optional argument
    @classmethod
    def from_json(cls, json_str: str, check_stop_func=None):
        print (f"Loading AutomationSequence from JSON")
        """Deserialize JSON string to AutomationSequence."""
        d = json.loads(json_str)
        return cls.from_dict(d, check_stop_func=check_stop_func)


    def __repr__(self):
        return f"AutomationSequence (title, steps, settings, check_stop_func=self.check_stop): {self.title}"
    

    def __str__(self):
        return f"{self.title}"
    
    
