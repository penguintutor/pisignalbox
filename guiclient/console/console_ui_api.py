# UI for the console window - api tab
from PySide6.QtWidgets import QMainWindow, QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView
from datetime import datetime
from pyvlcb import VLCB
from pyvlcb import VLCBOpcode
from events import LogEvent


def setup_ui(self):
    header = self.ui.apiTableView.horizontalHeader()

    # Disable 'stretchLastSection' so column 6 doesn't hog all the extra space
    header.setStretchLastSection(False)

    # Set fixed/initial widths for the other columns
    self.ui.apiTableView.setColumnWidth(0, 170)
    self.ui.apiTableView.setColumnWidth(1, 100)
    self.ui.apiTableView.setColumnWidth(3, 170)

    # Tell both columns 5 and 6 to dynamically share any remaining space
    header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

# log_event is a LogEvent object
# Method should only be passed objects that are type = Api
def add_log (self, log_event):
    # Extract details for log
    # Don't have a time, so create that
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_list = [
        timestamp,
        log_event.get_value("api_direction"),
        log_event.get_value("api_type"),
        log_event.get_value("api_command"),
        log_event.get_value("api_device"),
        log_event.get_value("api_settings"),
        log_event.get_value("api_description")
    ]
    #print (f"Console UI API - Adding log {log_list}")
    self.new_api_entries.append(log_list)

def update_log (self):
    while len(self.new_api_entries) > 0:
        # log_details is already in the form of a list
        log_details = self.new_api_entries.pop(0)
        # Add new row to the model
        self.api_log_model.add_log_entry(log_details)
    
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
    except (ValueError, TypeError):
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
    except (ValueError, TypeError):
        return None
    # Also check number is not negative or too large
    if ev_id < 0 or ev_id > 65535:
        return None
    return ev_id


# Update checkbox wording
def scroll_checkbox (self):
    if self.ui.autoScrollCheckBox.isChecked():
        self.ui.autoScrollCheckBox.setText("Scroll on ")
    else:
        self.ui.autoScrollCheckBox.setText("Scroll off")
    
