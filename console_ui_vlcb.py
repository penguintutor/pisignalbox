# UI for the console window - vlcb tab
from PySide6.QtWidgets import QMainWindow, QTextBrowser, QTableWidget, QTableWidgetItem
from pyvlcb import VLCB
from pyvlcb import VLCBOpcode


def setup_ui (self):
    # Set column width for first column to ensure data fits
    #self.ui.consoleTable.setColumnWidth(0, 170)
    #self.ui.consoleTable.setColumnWidth(2, 200)
    pass

# log_details is unformatted string
# Extract details and store as:
# Cbus data (original string), can_id, op_code, data
def add_log (self, resp_string):
    # If it's blank then ignore
    if resp_string == "":
        return
    self.new_entries.append(resp_string)

def update_log (self):
    #print (f"Updating console with {self.new_entries}")
    while len(self.new_entries) > 0:
        resp_string = self.new_entries.pop(0)
        log_details = self.vlcb.log_entry(resp_string)
        # Add new row to the model
        self.vlcb_log_model.add_log_entry(log_details)
 
        
    # If in scrollmode then go to the bottom
    # Todo - change this to MVC model
    #if self.ui.scrollCheckBox.isChecked():
    #    self.ui.consoleTable.scrollToBottom()
    
# Command pulldown menu (QComboBox)
# Set the other argument lists
def command_changed (self):
    command = self.ui.commandSelect.currentText()
    # Commands with no arguments
    if  command == "Discover":
        num_args = 0
    # Commands which need a node id
    elif (command == "Query Node Number Events Configured" or
            command == "Query Node Number Available Events" or
            command == "Query Node Stored Events" ):
        num_args = 1
        # Add nodes to arg1
        self.ui.arg1Select.clear()
        for node_id in sorted(self.mainwindow.nodes.keys()):
            self.ui.arg1Select.addItem(str(node_id))
    # Command that takes node_id, EV ID and State (on/off)
    elif (command == "Accessory Command"):
        num_args = 3
        # Add nodes to arg1
        self.ui.arg1Select.clear()
        self.ui.arg2Select.clear()
        for node_id in sorted(self.mainwindow.nodes.keys()):
            self.ui.arg1Select.addItem(str(node_id))
        # Now call arg1_changed to update next field with EVID
        self.arg1_changed()
    else:
        num_args = 0
    
    # Only show arguments with options
    if num_args < 1:
        self.ui.arg1Select.hide()
    else:
        self.ui.arg1Select.show()
    if num_args < 2:
        self.ui.arg2Select.hide()
    else:
        self.ui.arg2Select.show()
    if num_args < 3:
        self.ui.arg3Select.hide()
    else:
        self.ui.arg3Select.show()
        # It's arg1 that determines if this is needed
        self.arg1_changed()
        self.arg2_changed()

# This is called by commands that need arg 2 (eg. EVID) and typically arg 3 (On / Off)
def arg1_changed(self):
    # Set arg 2
    self.ui.arg2Select.clear()
    # first get node_id - to lookup ev id
    node_id = self.arg1_nodeid()
    if node_id == None:
        return
    for ev_id in sorted(self.mainwindow.nodes[node_id].ev.keys()):
        self.ui.arg2Select.addItem(str(ev_id))
    # Assume arg 3 still gives On/Off
        
# This is called by commands that need arg 3
# Defaults to On/Off
def arg2_changed(self):
    pass
#    # Set arg 3
#    self.ui.arg3Select.clear()
#    # first get node_id - to lookup ev id
#    node_id = self.arg1_nodeid()
#    if node_id == None:
#        return
#    print (f"Node {node_id} + evs {self.mainwindow.nodes[node_id].ev.keys()}")
#    for ev_id in sorted(self.mainwindow.nodes[node_id].ev.keys()):
#        self.ui.arg3Select.addItem(str(ev_id))
#    # Assume arg 3 still gives On/Off
        
        
# Generate command
def make_command (self):
    command = self.ui.commandSelect.currentText()
    if command == "Discover":
        self.ui.commandEdit.setText(self.vlcb.discover())
    elif command == "Query Node Number Events Configured":
        node_id = self.arg1_nodeid()
        if node_id == None:
            return
        self.ui.commandEdit.setText(self.vlcb.discover_evn(node_id))
    elif command == "Query Node Number Available Events":
        node_id = self.arg1_nodeid()
        if node_id == None:
            return
        self.ui.commandEdit.setText(self.vlcb.discover_nevn(node_id))
    elif command == "Query Node Stored Events":
        node_id = self.arg1_nodeid()
        if node_id == None:
            return
        self.ui.commandEdit.setText(self.vlcb.discover_nerd(node_id))
    elif (command == "Accessory Command"):
        node_id = self.arg1_nodeid()
        if node_id == None:
            return
        ev_id = self.arg2_evid()
        if ev_id == None:
            return
        state_str = self.ui.arg3Select.currentText()
        if state_str == "On":
            state_str = "on"
        elif state_str == "Off":
            state_str = "off"
        else:
            return
        self.ui.commandEdit.setText(self.vlcb.accessory_command(node_id, ev_id, state_str))
        
        
    
# Get nodeid from argument 1
def arg1_nodeid (self):
    try :
        node_str = self.ui.arg1Select.currentText()
        node_id = int(node_str)
        # If no node_id, or it's not a number return
    except:
        return None
    # Also check number is not negative or too large
    if node_id < 0 or node_id > 65535:
        return None
    return node_id

# Get ev_id from argument 2
def arg2_evid (self):
    try :
        ev_str = self.ui.arg2Select.currentText()
        ev_id = int(ev_str)
        # If no node_id, or it's not a number return
    except:
        return None
    # Also check number is not negative or too large
    if ev_id < 0 or ev_id > 65535:
        return None
    return ev_id


# Update checkbox wording
def scroll_checkbox (self):
    if self.ui.scrollCheckBox.isChecked():
        self.ui.scrollCheckBox.setText("Scroll on ")
    else:
        self.ui.scrollCheckBox.setText("Scroll off")
    
