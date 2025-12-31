# AutomationManager is used to store and manage the AutomationSequence objects
import os
import json
from PySide6.QtCore import Qt, QTimer, QObject, QThreadPool, QRunnable, Signal, Slot
from PySide6.QtWidgets import QMessageBox
from worker import Worker
from automationsequence import AutomationSequence
from workersignals import WorkerSignals


class AutomationManager (QObject):
    
    # Map of automation to filenames
    automation_files = {
        "Default": "default.json"
        }
    
    global_status = Signal(str)
    #sequence_finished = Signal()
    
    # Pass the directory to the init as in future may allow different files
    # Automation name is the name of the overall collection of sequences (ie. which file to load)
    
    def __init__ (self, threadpool: QThreadPool, appvariables, directory, automation_name="Default"):
        super().__init__()
        self.threadpool = threadpool
        self.dir = directory
        self.name = automation_name
        self.description = ""	# Description for the automation - loaded from file
        self.vars = appvariables
        self.sequences = []

        
    # Get sequence variables 
    def get_variables(self):
        #print ("Getting variables from all sequences")
        vars = []
        for seq in self.sequences:
            vars.extend(seq.get_variables())
        return vars

    def add_sequence(self, sequence_data):
        #print ("Adding sequence to Automation Manager")

        sequence = AutomationSequence(self.vars, **sequence_data)
        sequence.signals.notify.connect(self.handle_notify)
        sequence.signals.status.connect(self.handle_status)
        sequence.signals.finished.connect(self.sequence_finished)   
        self.sequences.append(sequence)

    def handle_notify(self, title, message):
        QMessageBox.information(None, title, message)

    def handle_status(self, status_message):
        QMessageBox.information(None, "Status", status_message)

    def sequence_finished(self, seq_num):
        #print (f"Automation Manager: Sequence {seq_num} finished")
        self.global_status.emit(f"Sequence {seq_num} finished")

    def update_sequence(self, seq_num, sequence_data):
        if seq_num >= len(self.sequences):
            print ("Error invalid sequence number in update_sequence")
            return
        # Just replace with new sequence
        # Could create before replace if concern about errors
        self.sequences[seq_num] = AutomationSequence(self.vars, **sequence_data)
        
        
    # Return sequence based on sequence number (index in list)
    def get_sequence(self, seq_num):
        return self.sequences[seq_num]


    def get_sequence_strings(self):
        return [str(sequence) for sequence in self.sequences]

    # Save - can override automation_name - but only if already exists
    # Need to add way to create new automation names in future
    def save(self, automation_name=None):
        # If no automation_name provided use the current one
        if automation_name == None:
            automation_name = self.name
        filename = self.automation_files.get(automation_name)
        # Check we have a filename from the automation_files
        if filename == None:
            # This should not happen - based on ability to create as required
            print (f"Unable to save as filename does not exist for {automation_name}")
            return
        file_path = os.path.join(self.dir, filename)
        try:
            # First convert sequences to a list of json-serializable objects
            seq_data = [
                #this_seq.to_json() for this_seq in self.sequences
                this_seq.to_dict() for this_seq in self.sequences
                ]
            # Also add information about this class (description etc)
            save_data = {
                "name": self.name,
                "description": self.description,
                "sequences": seq_data
                }
            
            
            with open (file_path, 'w') as file:
                json.dump(save_data, file, indent=4)
            return ("Save successful")
        except Exception as e:
            print (f"Error Saving file from Automation Manager {e}")
            return (f"Error saving file {e}")
        

    def load(self, automation_name=None):
        # If no automation_name provided use the current one
        if automation_name == None:
            automation_name = self.name
        filename = self.automation_files.get(automation_name)
        # Check we have a filename from the automation_files
        if filename == None:
            # This should not happen if selected from GUI
            print (f"Unable to open as filename does not exist for {automation_name}")
            return
        file_path = os.path.join(self.dir, filename)

        try:
            with open(file_path, 'r') as f:
                data_loaded = json.load(f)
                
            #print (f"Data loaded {data_loaded}")

            self.name = data_loaded.get("name", "")
            self.desription = data_loaded.get("description", "")
            seq_list = data_loaded.get("sequences", [])
            # Check if the loaded data is a list
            if not isinstance(seq_list, list):
                print(f"Error: Data in {file_path} is invalid")
                return

            # Reconstruct as AutomationSequence and store them
            restored_sequences = []
            for item_data in seq_list:
                this_seq = AutomationSequence.from_dict(item_data, self.vars)
                this_seq.signals.notify.connect(self.handle_notify)
                this_seq.signals.status.connect(self.handle_status)
                this_seq.signals.finished.connect(self.sequence_finished)
                restored_sequences.append(this_seq)
            
            self.sequences = restored_sequences
            
            #print(f"Successfully loaded {len(self.sequences)} sequences from {file_path}")

        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except AttributeError:
            print("Error: The provided class lacks a 'from_json' method.")
        except Exception as e:
            print(f"An error occurred while loading: {e}")
            
    def thread_start (self, seq_num):
        if seq_num < len(self.sequences):
            self.sequences[seq_num].run(seq_num)
            
    def run_sequence(self, seq_num):
        # Only allow one check_responses thread to run at a time
               
        worker = Worker(self.thread_start, seq_num)
        self.threadpool.start(worker)
        return
    
    