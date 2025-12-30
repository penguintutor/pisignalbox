""" Dialog for creating a new AutomationSequence."""
# TODO: Fix Gui loading
# TODO: Allow text string to wait (allow variable) - hide further rows

import sys
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QHBoxLayout, QWidget, QMessageBox,
    QListWidget, QFormLayout, QLineEdit, QSpinBox, QSizePolicy, QSpacerItem,
    QInputDialog 
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from automationrule import AutomationRule
from automationsequence import AutomationStep, AutomationSequence
from automationdialogrows import AutomationDialogRows
from devicemodel import device_model
from locoevent import LocoEvent


# Dialog for creating automation step (eg. rule)
class AutomationStepDialog(QDialog):
    def __init__(self, parent, num_locos, step: AutomationStep = None):
        super().__init__(parent)
        self.parent = parent
        self.mainwindow = self.parent.mainwindow
        self.setWindowTitle("Configure Rule")
        self.resize(350, 250)
        # Always show 1 more loco in case a new one is required
        self.num_locos_req = num_locos + 1
        self.step = step
        self.params = {}

        # Used to track current selections to avoid reloading combos unnecessarily
        self.current_row_value = [""] * 6

        # TODO: remove these
        # OLD method
        # Used to track if loading a new dialog and whether type has changed
        # If current type equals new selected type then no need to reload combos
        self.current_type = "New"
        # same for current node (row 2)
        self.current_row2 = "New"
        # current event (row 3)
        self.current_row3 = "New"
        # current value (row 4)
        self.current_row4 = "New"
        # current value2 (row 5)
        self.current_row5 = "New"

        self.setLayout(QFormLayout())

        self.rows = AutomationDialogRows(self, self.layout())
        
        
        # Buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.save_step)
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        self.layout().addRow(button_box)
               
        # Update the rows - intially call with load 
        # If step is not set then load is ignored
        self.update_rows (load=True)

    
    def _hide_rows (self, row_index ):
        # Hide all rows from row_index to 5
        for i in range (row_index, 6):
            self.rows.show_hide_row(i, False)
            # Also reset current row values
            self.current_row_value[i] = "" 

    def _reset_row_currents (self, from_row, type="VLCB"): 
        # New method - reset to ""
        for i in range (from_row, 6):
            self.current_row_value[i] = ""

        # used to reset current row trackers if prev combo has changed  
        if from_row <= 2:
            if type == "App":
                self.current_row3 = "Select Command"
            self.current_row2 = "Select Node"
        if from_row <= 3:
            if type == "Loco":
                self.current_row3 = "Select Loco"
            elif type == "App":
                self.current_row3 = "default"
            else:
                self.current_row3 = "Select Event"
        if from_row <= 4:
            if type == "Loco":
                self.current_row4 = "Select Action"
            else:
                self.current_row4 = "default"
        if from_row <= 5:
            self.current_row5 = "default"

    def _set_input_types (self, type="default", mode="default"):
        """Set the input types based on type."""
        # Type is the main type (VLCB, Loco, GUI, App)
        # Mode is if special setting (eg. Loco has "non-dccid" for loco no)
        # Used in single method so all updates can be made here and relected in the other types
        #if type == "Loco" and mode == "non-dccid":
        #    self.rows.set_field_type(3, "fieldlabel")  # Event is label
        #elif type == "Loco":
        #    self.rows.set_field_type(3, "lineedit")  # Event is lineedit for DCC ID
        # For loco manage within selection - for others set row 3 back to combo
        if type == "Loco":
            pass
        # Default for all others
        else:
            self.rows.set_field_type(3, "combo")  # Event is combobox

    def update_rows (self, load = False):
        # disable signals - prevents multiple calls during update
        self.rows.enable_combo_signals(False)

        # Load progress is used to determine state of loading
        # If set to load then load from self.step, if continue then load from ui, if new then
        # UI has changed above position so reset to default 
        self.load_progress = "continue"
        if load == True and self.step != None and "data" in self.step:
            self.load_progress = "load"

        # If initial open and step is not None then set current title and type
        if self.load_progress == "load":
            self.rows.set_lineedit_text(0, self.step.get('name'))
            step_type = self.step.get('type')
            if step_type == "User Interface":
                step_type = "Gui"   # adjust for combo display
            self.rows.set_combo_text(1, step_type)

        # Get form type and call appropriate method to set up the form
        form_type = self.rows.get_type_text()
        #self.current_row_value[1] = form_type  # Update later
        if form_type == None:
            self.form_selected_none()
        elif form_type == "VLCB":
            self.form_selected_vlcb()
        elif form_type == "Loco":
            self.form_selected_loco()
        elif form_type == "User Interface":
            self.form_selected_gui()
        elif form_type == "App":
            self.form_selected_app()
        else:
            self.form_selected_none()

        # enable signals
        self.rows.enable_combo_signals(True)


    def form_selected_none (self):
        self.current_row_value[1] = "Select Type"
        self._hide_rows(2)

    def form_selected_vlcb (self):
        self._set_input_types(type="VLCB")
        self.rows.show_hide_row(2, True, "Node:")    # Show node row
        # Only hide when finished 
        # if  current type has changed then generate node list
        #print (f"Current_row _values {self.current_row_value}")
        if self.current_row_value[1] != "VLCB":
            node_items = ["Select Node"] + device_model.get_nodes_names("VLCB", null_events=False)
            # if no nodes then just show NA
            if node_items == ["Select Node"]:
                node_items = ["NA"]
            self.rows.combo_add_items(2, node_items)
        # Otherwise node list is already set
        # remember current setting
        self.current_row_value[1] = "VLCB"
        # If loading then set
        if self.load_progress == "load":
            # Set row 2 (node) based on loaded step
            self.rows.set_combo_text(2, device_model.key_to_name(self.step['data'].get('node_id'), "VLCB"))

        # Node selection is populated - check for a value
        selected_node = device_model.name_to_key(self.rows.get_combo_text(2), "VLCB")
        # If this was new and not loaded or moved back to "Select Node" then return here - need to select node first
        if selected_node == None or selected_node == "Select Node":
            self.current_row_value[2] = "Select Node"
            # Hide remaining elements
            self._hide_rows(3)
            return
        
        # Node selected to reach here
        #print (f"selected node {selected_node} curr {self.current_row2}")
        # Set Event to visible
        self.rows.show_hide_row(3, True, "Event:")
        if self.current_row_value[2] != selected_node:
            # node is different to current - so update event list
            event_items = ["Select Event"] + device_model.get_events(selected_node, "VLCB")    
            if event_items == ["Select Event"]:
                event_items = ["NA"]
            self.rows.combo_add_items(3, event_items)
            self.current_row_value[2] = selected_node
            
        if self.load_progress == "load":
            # Set based on loaded step
            self.rows.set_combo_text(3, device_model.key_to_name(self.step['data'].get('event'), "VLCB"))
                
        # Read in row 3 (event) and check for change
        selected_event = self.rows.get_combo_text(3)
        if selected_event == None or selected_event == "Select Event":
            self._hide_rows(4)    # Hide remaining rows (from value onwards)
            self.current_row_value[3] = "Select Event"
            return
        
        # show value field
        self.rows.show_hide_row(4, True, "Value:")
        #print (f"selected event {selected_event} curr {self.current_row3}")
        if selected_event != self.current_row_value[3]:
            # event is different to current - so update value list
            # For vlcb then value is on / off depending on event (no select default to on)
            value_items = ["on", "off"]
            self.rows.combo_add_items(4, value_items)
            
            if self.load_progress == "load":
                # Set based on loaded step
                self.rows.set_combo_text(4, self.step['data'].get('value'))
            # value 2 not used - set defaults and hide value 2
            self._reset_row_currents(4, type="VLCB")    # Reset from value onwards
            self._hide_rows(5)    # Hide remaining rows (from value2 onwards)
        self.current_row_value[3] = selected_event
        # Don't need to check value as there are no fields below it


    def form_selected_loco (self):
        #print (f"Loco selected action current row4 {self.current_row4}")
        self._set_input_types(type="Loco")
        self.rows.show_hide_row(2, True, "Loco No.:")    # Show loco row

        # If changed then load loco list
        if self.current_row_value[1] != "Loco":
            node_items = ["Select Loco"] + [device_model.key_to_name(i, "Loco") for i in range(1, self.num_locos_req + 1)] + ["Use DCC ID"]
            self.rows.combo_add_items(2, node_items)
        self.current_row_value[1] = "Loco"

        # Load existing if appropriate
        if self.load_progress == "load":
            # Set based on loaded step
            locoid = self.step['data'].get('locoid')
            if locoid is not None:
                # Locid is already as a string
                # self.rows.set_combo_text(2, device_model.key_to_name(locoid, "Loco"))
                self.rows.set_combo_text(2, locoid)
            # There should be only one of locoid and dccid if both then locoid takes precedence
            # If dccid then set to Use DCC ID which will load if appropriate
            elif self.step['data'].get('dccid') is not None:
                self.rows.set_combo_text(2, "Use DCC ID")
            
        # Loco selection is populated - check for a value
        selected_loco = self.rows.get_combo_text(2)
        if selected_loco == None or selected_loco == "Select Loco":
            self.current_row_value[2] = "Select Loco"
            self._hide_rows(3)    # Hide remaining rows (from DCC ID onwards)
            return
        
        # If DCC ID then attempt to load
        if selected_loco == "Use DCC ID":
            self.rows.set_field_type(3, "lineedit")  # Event is lineedit for DCC ID
            # If previous was not "Use DCC ID" then clear value
            if self.current_row_value[2] != "Use DCC ID":
                self.rows.set_lineedit_text(3, "")
            self.rows.show_hide_row(3, True, "DCC ID:")
            # Set edit field (show label later)
            # If loading from step then set DCC ID if present

            if self.load_progress == "load":
                dccid = self.step['data'].get('dccid')
                if dccid is not None:
                    self.rows.set_lineedit_text(3, device_model.key_to_name(dccid, "Loco"))
        else:
            # A Loco ID is selected so show field label 
            # These say allocated at run time
            self.rows.show_hide_row(3, True, "DCC ID:")
            self.rows.set_field_type(3, "fieldlabel")  # Event is label
        # Set this later as need to know if action needs to be changed
        #self.current_row_value[2] = selected_loco
        # Continue regardless of DCC value as only verify on save
        # Set the row 3 to "" as not relevant
        self.current_row_value[3] = ""

        ## Now add Action field (row 4 as dccid is row 3)
        self.rows.show_hide_row(4, True, "Action:")
        #print (f"Loco action current row4 {self.current_row4}")
        # Actions aren't dependent on loco so just add when new
        if self.current_row_value[2] != selected_loco:
            action_items = ["Select Action"] + LocoEvent.get_action_names()
            self.rows.combo_add_items(4, action_items)
        self.current_row_value[2] = selected_loco
            
        if self.load_progress == "load":
            self.rows.set_combo_text(4, self.step['data'].get('action'))

        # Read in row 4 (action) and check for change
        selected_action = self.rows.get_combo_text(4)

        if selected_action == None or selected_action == "Select Action":
            self._hide_rows(5)    # Hide remaining rows (from value onwards)
            self.current_row_value[4] = "Select Action"
            return

        # show value field
        self.rows.show_hide_row(5, True, "Value:")

        if selected_action != self.current_row_value[4]:
            # action is different to current - so update value list
            # Options depends upon action - due to number of options
            # this is moved into AutomationDialogRows
            # if it's new then send the value to the setup
            if self.load_progress == "load":
                data = self.step.get('data')
                self.rows.loco_action_setup(selected_action, data)
            else:
                self.rows.loco_action_setup(selected_action)
            
        self.current_row_value[4] = selected_action
        # row5 value doesn't matter as long as set to not New
        # row 5 depends upon loco_action_setup
        #self._reset_row_currents(5, type="Loco")    # Reset from value 5 onwards
        #self._hide_rows(5)    # Hide remaining rows (from value2 onwards)
       

    def form_selected_gui (self):
        self._set_input_types(type="Gui")
        self.rows.show_hide_row(2, True, "Node:")    # Show node row
        
        # if  current type has changed then generate node list
        if self.current_row_value[1] != "Gui":
            node_items = ["Select Node"] + device_model.get_nodes_names("Gui", null_events=False)
            # if no nodes then just show NA
            if node_items == ["Select Node"]:
                node_items = ["NA"]
            self.rows.combo_add_items(2, node_items)

        self.current_row_value[1] = "Gui"

        if self.load_progress == "load":
            # Set based on loaded step
            self.rows.set_combo_text(2, device_model.key_to_name(self.step['data'].get('node_id'), "Gui"))

        # Node selection is populated - check for a value
        selected_node = device_model.name_to_key(self.rows.get_combo_text(2), "Gui")
        # If this was new and not loaded or moved back to "Select Node" then return here - need to select node first
        if selected_node == None or selected_node == "Select Node":
            self.current_row_value[2] = "Select Node"
            self._hide_rows(3)
            return
        
        # Node selected to reach here
        # Set Action to visible
        self.rows.show_hide_row(3, True, "Action:")
        if selected_node != self.current_row_value[2]:
            # node is different to current - so update action list
            action_items = ["Select Action"] + device_model.get_events(selected_node, "Gui")    
            if action_items == ["Select Action"]:
                action_items = ["NA"]
            self.rows.combo_add_items(3, action_items)

        if self.load_progress == "load":
            self.rows.set_combo_text(3, device_model.key_to_name(self.step['data'].get('event'), "Gui"))

        self.current_row_value[2] = selected_node
        
        # Read in row 3 (action) and check for change
        selected_action = self.rows.get_combo_text(3)
        
        if selected_action == None or selected_action == "Select Action":
            self._hide_rows(4)    # Hide remaining rows (from value onwards)
            self.current_row_value[3] = "Select Action"
            return

        # If action requires a value then show value row
        # Not required for Toggle
        if selected_action == "Toggle":
            self._hide_rows(4)
            self.current_row_value[3] = "Toggle"
            return

        self.rows.show_hide_row(4, True, "Value:")
        # If previous entry changed then need to create value list
        if selected_action != self.current_row_value[3]:
            value_items = ["on", "off"]
            self.rows.combo_add_items(4, value_items)

        self.current_row_value[3] = selected_action

        if self.load_progress == "load":
            self.rows.set_combo_text(4, self.step['data'].get('value'))
            
        # value 2 not used - set defaults and hide value 2
        self._hide_rows(5)
        # Don't need to check value as there are no fields below it


    def form_selected_app (self):
        self._set_input_types(type="App")
        self.rows.show_hide_row(2, True, "Command:")    # Show node row
        # if  current type has changed then generate node list
        if self.current_row_value[1] != "App":
            # For app then just hard code some options for now
            command_items = ["Select Command", "Wait", "Set Variable"]
            self.rows.combo_add_items(2, command_items)

        self.current_row_value[1] = "App"

        if self.load_progress == "load":
            # Set based on loaded step
            self.rows.set_combo_text(2, self.step['data'].get('command'))

        # Command selection is already populated - check for a value
        selected_command = self.rows.get_combo_text(2)

        # If this was new and not loaded or moved back to "Select Command" then return here - need to select node first
        if selected_command == None or selected_command == "Select Command":
            self.current_row_value[2] = "Select Command"
            self._hide_rows(3)
            return
        
        #print (f"App command selected {selected_command} curr {self.current_row_value[2]}")

        # Set Argument to visible - different argument depending upon command
    
        if selected_command == "Wait":
            self.form_app_wait()
        elif selected_command == "Set Variable":
            self.form_app_variable()
        
        self.current_row_value[2] = selected_command

    def form_app_wait (self):
        self.rows.set_field_type(3, "lineedit")
        self.rows.show_hide_row(3, True, "Delay:")

        # If command changed - reset lineedit value
        if self.current_row_value[2] != "Wait":
            self.rows.set_lineedit_text (3, "")

        if self.load_progress == "load":
            self.rows.set_lineedit_text (3, self.step['data'].get('delay', ""))

        self._hide_rows (4)


    def form_app_variable (self):
        #if self.step != None:
        #    print (f"In variable form {self.step}, row3 {self.current_row3}, row 4 {self.current_row4}")
        #print (f"Set Variable selected current row 3 {self.current_row3}")
        self.rows.set_field_type(3, "combo")
        self.rows.show_hide_row(3, True, "Variable name:")

        # row may be set to Select Command from defaults
        if self.current_row_value[2] != "Set Variable":
            variable_list = ["Select Variable"] + device_model.get_variable_names() + ["New Variable"]
            self.rows.combo_add_items(3, variable_list)

        # If loading existing then select variable
        if self.load_progress == "load":
            #print (f"Variable {self.step}")
            variable_name = self.step['data'].get('variable')
            # Check variable name is not ""
            if variable_name != None and variable_name != "":
                # If variable doesn't exist then add
                if self.mainwindow.appvariables.is_variable(variable_name) != True:
                    # Create the variable but do not give it a value - as that will only be when automation run
                    self.mainwindow.add_variable(variable_name, "", False)    
                    # Reload the combo list 
                    variable_list = ["Select Variable"] + device_model.get_variable_names() + ["New Variable"]
                    self.rows.combo_add_items(3, variable_list)
                self.rows.set_combo_text (3, variable_name)
        
        # Read value back to check setting
        selected_variable = self.rows.get_combo_text (3)

        if selected_variable == "Select Variable":
            # hide remaining - need to choose variable first
            self.current_row_value[3] = "Select Variable"
            self._hide_rows(4)
            return

        # If new variable then request variable through a 
        # new dialog
        elif selected_variable == "New Variable":
            self.rows.show_hide_row(3, True, "Variable name:")
            #print ("Launching add variable dialog")
            new_variable = self.create_variable_dialog()
            if new_variable != None and new_variable != "" and self.mainwindow.appvariables.is_variable(new_variable) != True:
                # Create new variable by setting value to ""
                self.mainwindow.add_variable(new_variable, "", False)
                # Update menu
                variable_list = ["Select Variable"] + device_model.get_variable_names() + ["New Variable"]
                self.rows.combo_add_items(3, variable_list)
                self.rows.set_combo_text(3, new_variable)
            else:
                # If didn't get a new variable then return so that the user can select again
                self.current_row_value[3] = "Select Variable"
                self._hide_rows(4)
                return 
            
        # Here - confirm a variable is selected
        selected_variable = self.rows.get_combo_text(3)

        # Check haven't gone back to Select Variable (eg. variable creation error)
        if selected_variable == "Select Variable":
            self.current_row_value[3] = "Select Variable"
            self._hide_rows(4)
            return

        # Now have variable name
        # Show row 4 - value entry - which is a lineedit
        self.rows.set_field_type(4, "lineedit")
        self.rows.show_hide_row(4, True, "Value:")

        # If variable changed then clear value
        if self.current_row_value[3] != selected_variable:
            self.rows.set_lineedit_text (4, "")

        self.current_row_value[3] = selected_variable

        # if loading existing
        if self.load_progress == "load":
            self.rows.set_lineedit_text (4, self.step['data'].get('value'))

        self._hide_rows(5)

    # Gets data if valid and returns as a dict
    def save_step(self):
        rule_type = self.rows.get_combo_text(1)
        if rule_type == None or rule_type == "Select Type":
            QMessageBox.warning(self, "Invalid Type", "Please select a valid rule type.")
            return
        # All steps needed a name - but if empty can be created automatically
        self.name = self.rows.get_lineedit_text(0).strip()     

        if rule_type == "VLCB":          
            data_dict = self._get_step_data_vlcb()
            # If error then prev would give a QMessage and return None
            # just return to allow correct and try again
            if data_dict is None:
                return
            # If no name given then can replace with a user friendly
            if self.name == "":
                self.name = f"{rule_type}, {data_dict['node_id']} - {data_dict['event']} - {data_dict['value']}"
            
            # Return as a dict - let Automation Sequence convert into an Automation Step
            self.step = {"type": rule_type, "name": self.name, "data" : data_dict}
        elif rule_type == "Loco":          
            data_dict = self._get_step_data_loco()
            # If error then prev would give a QMessage and return None
            # just return to allow correct and try again
            if data_dict is None:
                return
            # If no name given then can replace with a user friendly
            if self.name == "":
                # Value depends upon action so not included at the moment
                if "locoid" in data_dict:
                    self.name = f"Loco {data_dict['locoid']} - {data_dict['action']}"
                else:
                    self.name = f"Loco {data_dict['dccid']} - {data_dict['action']}"
            
            # Return as a dict - let Automation Sequence convert into an Automation Step
            self.step = {"type": rule_type, "name": self.name, "data" : data_dict}
        elif rule_type == "User Interface":
            data_dict = self._get_step_data_gui()
            # If error then prev would give a QMessage and return None
            # just return to allow correct and try again
            if data_dict is None:
                return
            # If no name given then can replace with a user friendly
            if self.name == "":
                self.name = f"{rule_type}, {data_dict['node_id']} - {data_dict['action']}"
                if 'value' in data_dict:
                    self.name += f" - {data_dict['value']}"
            
            # Return as a dict - let Automation Sequence convert into an Automation Step
            self.step = {"type": "Gui", "name": self.name, "data" : data_dict}

        elif rule_type == "App":
            data_dict = self._get_step_data_app()
            # If error then prev would give a QMessage and return None
            # just return to allow correct and try again
            if data_dict is None:
                return
            # If no name given then can replace with a user friendly
            if self.name == "":
                self.name = f"{rule_type}, {data_dict['command']}"
                if 'variable' in data_dict:
                    self.name += f" - {data_dict['variable']}"
                if 'value' in data_dict:
                    self.name += f" - {data_dict['value']}"
                if 'delay' in data_dict:
                    self.name += f" - {data_dict['delay']}"
            
            # Return as a dict - let Automation Sequence convert into an Automation Step
            self.step = {"type": "App", "name": self.name, "data" : data_dict}
            
        # Todo need to implement all rule types so this doesn't happen
        else:
            print (f"Unable to validate entries {rule_type}")
            return
        
        # here validate values before accepting
        super().accept()
        
    def get_step(self):
        return self.step
    
    def _get_step_data_vlcb(self):
        """ Gets step data for vlcb - used in save_step """
        # If fails uses QMessage and returns None
        data_dict = {}
        node = self.rows.get_combo_text(2)
        if node == None or node == "Select Node" or node == "NA":
            QMessageBox.warning(self, "Invalid Node", "Please select a valid node.")
            return None
        data_dict['node_id'] = device_model.name_to_key(node)
        event = self.rows.get_combo_text(3) 
        if event == None or event == "Select Event" or event == "NA":
            QMessageBox.warning(self, "Invalid Event", "Please select a valid event.")
            return None
        data_dict['event'] = event
        # Value should not return an invalid value but check anyway
        value = self.rows.get_combo_text(4)
        if value == None or value == "NA":
            QMessageBox.warning(self, "Invalid Value", "Please select a valid value.")
            return None
        data_dict['value'] = value
        return data_dict

    def _get_step_data_loco(self):
        """ Gets step data for loco - used in save_step """
        # If fails uses QMessage and returns None
        data_dict = {}
        locoid = self.rows.get_combo_text(2)
        if locoid == None or locoid == "Select Loco" or locoid == "NA":
            QMessageBox.warning(self, "Invalid Loco", "Please select a valid loco.")
            return None
        elif locoid == "Use DCC ID":
            # Get DCC ID from lineedit
            dccid_str = self.rows.get_lineedit_text(3)
            try:
                dccid = int(dccid_str)
                if not (1 <= dccid <= 9999):
                    QMessageBox.warning(self, "Invalid DCC ID", "DCC ID must be between 1 and 9999.")
                    return None
            except ValueError:
                QMessageBox.warning(self, "Invalid DCC ID", "DCC ID must be an integer.")
                return None
            data_dict['dccid'] = dccid
        else:
            # Save with ID {locoid} format
            data_dict['locoid'] = locoid
        action = self.rows.get_combo_text(4)
        if action == None or action == "Select Action" or action == "NA":
            QMessageBox.warning(self, "Invalid Action", "Please select a valid action.")
            return None
        data_dict['action'] = action
        # Value depends on action
        if action == "Set Speed":
            speed = self.rows.get_spinbox_value(5)
            data_dict['speed'] = speed
        elif action == "Set Direction":
            direction = self.rows.get_combo_text(5)
            if direction == None or direction == "NA":
                QMessageBox.warning(self, "Invalid Direction", "Please select a valid direction.")
                return None
            data_dict['direction'] = direction
        elif action == "Function":
            function = self.rows.get_inner_spinbox_value(5)
            function_action = self.rows.get_inner_combo_text(5)
            data_dict['function'] = function
            data_dict['function_action'] = function_action
        return data_dict
        
    def _get_step_data_gui(self):
        """ Gets step data for vlcb - used in save_step """
        # If fails uses QMessage and returns None
        data_dict = {}
        node = self.rows.get_combo_text(2)
        if node == None or node == "Select Node" or node == "NA":
            QMessageBox.warning(self, "Invalid Node", "Please select a valid node.")
            return None
        data_dict['node_id'] = device_model.name_to_key(node)
        action = self.rows.get_combo_text(3) 
        if action == None or action == "Select Action" or action == "NA":
            QMessageBox.warning(self, "Invalid Action", "Please select a valid action.")
            return None
        data_dict['action'] = action
        # Do not need a value if action is Toggle
        if action != "Toggle":
            value = self.rows.get_combo_text(4)
            if value == None or value == "NA":
                QMessageBox.warning(self, "Invalid Value", "Please select a valid value.")
                return None
            data_dict['value'] = value
        return data_dict

    def _get_step_data_app(self):
        app_command = self.rows.get_combo_text(2)
        if app_command == "Wait":
            return self._get_step_data_app_wait()
        elif app_command == "Set Variable":
            return self._get_step_data_app_variable()
        else:
            print ("Unknown app command")
            return None


    def _get_step_data_app_wait(self):
        """ Gets step data for app wait command - used in save_step """
        # If fails uses QMessage and returns None
        data_dict = {'command': "Wait"}
        delay = self.rows.get_lineedit_text (3)
        data_dict['delay'] = delay
        return data_dict

    def _get_step_data_app_variable (self):
        """ Gets step data for app set variable command - used in save_step """
        # If fails uses QMessage and returns None
        data_dict = {'command': "Set Variable"}
        variable = self.rows.get_combo_text (3)
        if variable == "Select Variable" or variable == "New Variable":
            QMessageBox.warning(self, "Invalid Variable", "Please select a valid variable.")
            return None
        data_dict['variable'] = variable
        value = self.rows.get_lineedit_text (4)
        data_dict['value'] = value
        return data_dict

    # Swaps the widget specified (eg. combobox with lineedit or spinbox)
    # Uses label_widget to find the row
    # New widget is the one to insert
    # defaults to hiding the old widget & showing the new
    def swap_field_widget(self, label_widget: QWidget, new_widget: QWidget, hide_old: bool = True):
        form_layout = self.layout()
        # Find the row and role of the label
        row, role = form_layout.getWidgetPosition(label_widget)
        if row == -1:
            raise ValueError("Label widget not found in the layout.")

        # Get the current field widget
        field_item = form_layout.itemAt(row, QFormLayout.FieldRole)
        if field_item is None:
            raise ValueError("No field widget found in the same row as the label.")

        old_widget = field_item.widget()
        
        # Set the new_widget visible
        new_widget.show()
        
        # Check if already set to the new_widget
        if old_widget == new_widget:
            return None	# No swap needed

        # Replace the widget
        form_layout.replaceWidget(old_widget, new_widget)

        # Optionally hide or delete the old widget
        if hide_old:
            old_widget.hide()

    def create_variable_dialog(self):
        """
        Prompts the user for a variable name. 
        Returns the string if successful, or None if cancelled.
        """
        # getText returns (text, ok_pressed)
        text, ok = QInputDialog.getText(
            self, 
            "Create New Variable", 
            "Variable Name:", 
            QLineEdit.Normal, 
            ""
        )

        if ok and text.strip():
            return text.strip()
        
        return None                


