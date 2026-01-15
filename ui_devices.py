# Devices module for handling device operations for mainwindow
# This includes the UI wrapper class for the device tree view
import os
import sys
import time
from PySide6.QtCore import QTimer, QSize, QPoint
from PySide6.QtWidgets import QMenu, QDialog, QFileDialog, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QFont, QResizeEvent
from devicemodel import device_model
from eventbus import event_bus
from guiobject import GuiObject
from layoutobject import LayoutObject
from layoutbutton import LayoutButton
from layoutlabel import LayoutLabel
from pyvlcb import VLCB, VLCBformat
from vlcbnode import VLCBNode
from vlcbev import VLCBEv

            
# Handle right click - need to get item from position
def tree_clicked_right(self, position: QPoint):
    item = self.ui.nodeTreeView.indexAt(position)
    # Ignore if no item clicked
    if not item.isValid():
        return
    #print (f"Item {item} - Data {item.data()}")
    # Update the node table view
    node_item = device_model.node_model.itemFromIndex(item)
    self.update_tree_selected (node_item)
    
    # Create a context Menu
    menu = QMenu()
    # different menu depending upon node type
    #print (f"Node {node_item.text()}")
    #print (f"Selected {self.selected_node}")
    if self.selected_node.device_type == "Gui":
        edit_action = menu.addAction("Edit")
    else:
        edit_action = None
    
    selected_action = menu.exec(self.ui.nodeTreeView.viewport().mapToGlobal(position))
    if selected_action == edit_action:
        # Which type of node is this?
        #print (f"Selected node is {type(self.selected_node)}")
        if type(self.selected_node) is GuiObject:
            self.edit_dialog_guiobject()
        elif type(self.selected_node) is LayoutButton:
            self.edit_dialog_layoutbutton()
        elif type(self.selected_node) is LayoutLabel:
            self.edit_dialog_layoutlabel()

def tree_clicked(self, item):
    node_item = device_model.node_model.itemFromIndex(item)
    self.update_tree_selected (node_item)


# Updates tree based on current selected_node (if any)
def update_table (self):
    # If none selected then do nothing
    if self.selected_node == None:
        return
    # If gui / layout object
    if self.selected_node.device_type == "Gui":
        if type(self.selected_node) == GuiObject:
            #self.selected_node = gui_node
            self.node_table_show_gui_node(self.selected_node)
            # If num states < 2 then no button
            if self.selected_node.num_states < 2:
                self.update_node_buttons (None, None)
            # If exactly 2 then toggle button
            elif self.selected_node.num_states == 2:
                self.update_node_buttons ("Toggle", None)
            # If more than 2 then up / down
            else:
                self.update_node_buttons ("Prev", "Next")
        # Otherwise it's a layoutobject (button / label)
        else:
            # new item for child is [parent, type, pos]
            self.node_table_show_gui_child(self.selected_node)
            # Typically GUI children will say Toggle (for a label), or value for a button
            self.update_node_buttons (self.selected_node.get_action_type(), None)
    elif self.selected_node.device_type == "VLCB":
        if type(self.selected_node) is VLCBNode:
            self.node_table_show_node(self.selected_node)
            self.update_node_buttons (None, None)
        # or if it's a ev
        else:
            self.node_table_show_ev(self.selected_node)
            self.update_node_buttons ("On", "Off")


# Update the node table (whether right or left click)
def update_tree_selected (self, node_item):
    # Reset selected_node to None - then update if selected node
    self.selected_node = None
    # Need to identify what type of node has been clicked
    # Create two values top_string (= parent for children / self text for top level)
    # node_string = text of this node
    # First check is this a top level (doesn't have a parent)
    if (node_item.parent() == None):
        #print (f"Parent node clicked {node_item.text()}")
        node_string = node_item.text()
        top_string = node_string	# For top level then same as name
    # Otherwise use parent to determine type of node
    else:
        #print (f"Node clicked {node_item.text()} - parent {node_item.parent().text()}")
        node_string = node_item.text()
        top_string = node_item.parent().text()
    # Check for structured devices (eg. Gui object always begins with GUI)
    if top_string[0:3] == "GUI":
        #print (f"GUI {node_string}")
        # Temp call On / Off - need to set based on type of GUI object
        #self.update_node_buttons ("On?", "Off?")
        for gui_node in device_model.other_nodes['Gui']:
            new_item = gui_node.check_item(node_item)
            if new_item != None:
                self.selected_node = new_item
    # If not structure name then most likely a normal node which can have any name
    else:
        # Special case - if CANCAM 65535 or CANCMD 65534 then hide buttons
        if node_string[0:6] == "CANCAB" or node_string[0:6] == 'CANCMD':
            self.update_node_buttons (None, None)
        else:
            # Set buttons to normal
            self.update_node_buttons ("On", "Off")
            
        # Check device_model for the node
        for key, node in device_model.nodes.items():
            new_item = node.check_item (node_item)
            if new_item != None:
                self.selected_node = new_item
                # If this is a node then show that in table

    self.update_table()

# Updates the two node buttons at the bottom of the table
# These are known as evButtonOff & evButtonOn, but may also be used by
# GUI elements, be hidden etc.
# Provide text for the On & Off buttons, or set to None to disable
def update_node_buttons (self, on_text, off_text):
    # Check for None (in which case hide)
    if on_text == None:
        self.ui.evButtonOn.hide()
    else :
        # if "value" set text to "Activate"
        if on_text == "value" or on_text == "Value":
            on_text = "Activate"
        self.ui.evButtonOn.setText(on_text)
        self.ui.evButtonOn.show()
    if off_text == None:
        self.ui.evButtonOff.hide()
    else :
        if off_text == "value" or off_text == "Value":
            off_text = "Activate"
        self.ui.evButtonOff.setText(off_text)
        self.ui.evButtonOff.show()

# Ev clicked off button - also used for "next" when guiobject has multiple
def ev_clicked_off (self):
    # None selected (shouldn't normally be the case as buttons disabled)
    if self.selected_node == None:
        return
    #print (f"Selected {self.selected_node}")
    if type(self.selected_node) is VLCBEv:
        self.api.start_request(self.api.vlcb.accessory_command(self.selected_node.node.node_id, self.selected_node.get_en(), False))
    elif type(self.selected_node) is GuiObject:
        self.selected_node.activate("GuiObject", 1)
    else:
        self.selected_node.activate()

# Ev clicked on button - also used for "prev" / activate / toggle for other objects
def ev_clicked_on (self):
    if self.selected_node == None:
        return
    #print (f"Selected {self.selected_node}")
    if type(self.selected_node) is VLCBEv:
        self.api.start_request(self.api.vlcb.accessory_command(self.selected_node.node.node_id, self.selected_node.get_en(), True))
    elif type(self.selected_node) is GuiObject:
        self.selected_node.activate("GuiObject", 0)
    else:
        self.selected_node.activate()

# Update table for GUI node
def node_table_show_gui_node (self, node_item):
    self.ui.tableLabel.setText("GUI Node:")
    item = self.ui.nodeTable.verticalHeaderItem(0)
    item.setText("Name:")
    item = self.ui.nodeTable.verticalHeaderItem(1)
    item.setText("Type:")
    item = self.ui.nodeTable.verticalHeaderItem(2)
    item.setText("Num states:")
    item = self.ui.nodeTable.verticalHeaderItem(3)
    item.setText("Current state:")
    item = self.ui.nodeTable.verticalHeaderItem(4)
    item.setText("Comments:")
    
    item = self.ui.nodeTable.item(0,0)
    item.setText(node_item.name)
    item = self.ui.nodeTable.item(1,0)
    item.setText(node_item.object_type)
    item = self.ui.nodeTable.item(2,0)
    item.setText(str(node_item.num_states))
    item = self.ui.nodeTable.item(3,0)
    item.setText(f"{node_item.state_value}")
    item = self.ui.nodeTable.item(4,0)
    item.setText("")

# Update table for gui child
def node_table_show_gui_child (self, node_item):
    self.ui.tableLabel.setText("GUI Node Object:")
    item = self.ui.nodeTable.verticalHeaderItem(0)
    item.setText("GUI Node:")
    item = self.ui.nodeTable.verticalHeaderItem(1)
    item.setText("Type:")
    item = self.ui.nodeTable.verticalHeaderItem(2)
    item.setText("ID:")
    item = self.ui.nodeTable.verticalHeaderItem(3)
    item.setText("Current state:")
    item = self.ui.nodeTable.verticalHeaderItem(4)
    item.setText("Click action:")
    
    item = self.ui.nodeTable.item(0,0)
    item.setText(node_item.parent.name)
    item = self.ui.nodeTable.item(1,0)
    item.setText(node_item.get_type_str())
    item = self.ui.nodeTable.item(2,0)
    item.setText(str(node_item.get_index()))
    item = self.ui.nodeTable.item(3,0)
    item.setText(f"{node_item.parent.state_value}")
    item = self.ui.nodeTable.item(4,0)
    item.setText(node_item.get_action_str())

# Have the node table show the node information
def node_table_show_node (self, node_item):
    self.ui.tableLabel.setText("Node:")
    item = self.ui.nodeTable.verticalHeaderItem(1)
    item.setText("Node ID / CAN ID:")
    item = self.ui.nodeTable.verticalHeaderItem(2)
    item.setText("Mode:")
    item = self.ui.nodeTable.verticalHeaderItem(3)
    item.setText("Manuf / Mod:")
    item = self.ui.nodeTable.verticalHeaderItem(4)
    item.setText("Events / Space:")
    
    item = self.ui.nodeTable.item(0,0)
    item.setText(f"{node_item.name}")
    item = self.ui.nodeTable.item(1,0)
    item.setText(node_item.node_string())
    item = self.ui.nodeTable.item(2,0)
    item.setText(f"{node_item.mode}")
    item = self.ui.nodeTable.item(3,0)
    item.setText(node_item.manuf_string())
    item = self.ui.nodeTable.item(4,0)
    item.setText(node_item.ev_num_string())
        

# node_item = (VLCBEv)
def node_table_show_ev (self, node_item):
    self.ui.tableLabel.setText("Event:")
    item = self.ui.nodeTable.verticalHeaderItem(1)
    item.setText("Node ID:")
    item = self.ui.nodeTable.verticalHeaderItem(2)
    item.setText("Event ID:")
    item = self.ui.nodeTable.verticalHeaderItem(3)
    item.setText("Value")
    item = self.ui.nodeTable.verticalHeaderItem(4)
    item.setText("Long / short:")
    
    item = self.ui.nodeTable.item(0,0)
    item.setText(f"{node_item.name}")
    item = self.ui.nodeTable.item(1,0)
    item.setText(f"{node_item.node.node_id}")
    item = self.ui.nodeTable.item(2,0)
    item.setText(f"{node_item.ev_id}")
    item = self.ui.nodeTable.item(3,0)
    item.setText(f"{node_item.en:#08x}")
    item = self.ui.nodeTable.item(4,0)
    item.setText(f"{node_item.long_string()}")

# Used to add a device to the TreeView
# Needed to ensure this is run on the GUI thread
# First create QStandardItem on the api thread, then send signal
# to GUI thread with the parent and the child details
def add_to_tree (self, parent, child):
    parent.appendRow(child)