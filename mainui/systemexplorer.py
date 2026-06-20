# System Explorer provides the device tree view
# called directly from MainWindowUI
import os
import sys
import time
from PySide6.QtCore import Qt, QTimer, QSize, QPoint
from PySide6.QtWidgets import QMenu, QDialog, QFileDialog, QMessageBox
from PySide6.QtGui import QStandardItemModel, QStandardItem
from core import device_model, event_bus
from layout import GuiObject, LayoutObject, LayoutButton, LayoutLabel
from pyvlcb import VLCB
from device import device_manager, VLCBNode, VLCBEv
from layout import layout_manager
# This will replace device_model in future
#from layout import layout_manager

# Note: hardware = vlcb (or device)
# layout = GuiObject (and below)

class SystemExplorer:
    def __init__(self, tree_view_widget):
        """
        Takes the existing QTreeView from the MainWindow UI and takes control of it.
        """
        self.tree_view = tree_view_widget
        
        # Create the Model and attach it to the View
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Nodes"])
        self.tree_view.setModel(self.model)
        
        # Fast-lookup registry mapping backend IDs to memory locations
        # Format: { ("type", id1, id2...) : QStandardItem }
        self._registry = {}
        
        # Initialize
        self._build_backbone()
        self.populate_initial_data()
        self._wire_events()

    def populate_initial_data(self):
        """Fetches current data from managers at boot."""
        # --- Hardware Pass ---
        for node in device_manager.get_all_nodes():
            self.add_hardware_node(node)
            
        # --- Layout Pass ---
        # TODO Replace with layout_manager when implemented
        for gui_obj in layout_manager.get_all_nodes():
        #for layout_obj in device_model.nodes.values():
            self.add_gui_node(gui_obj)

    def _build_backbone(self):
        """Creates the permanent top-level categories."""
        self.hardware_root = QStandardItem("VLCB Nodes")
        self.hardware_root.setEditable(False)
        
        self.layout_root = QStandardItem("Layout Objects")
        self.layout_root.setEditable(False)

        self.model.appendRow(self.hardware_root)
        self.model.appendRow(self.layout_root)
        
        # Expand roots by default
        self.tree_view.expandAll()

    def add_hardware_node(self, node):
        print (f"System Explorer Adding hardware_node {node}")
        """Creates a Node row and its EV children."""
        # Create the Node Item using its built-in string representation
        node_item = QStandardItem(str(node))
        node_item.setEditable(False)
        
        # Stash the ID in the item so clself._registry.get(("node", event.node_id))icks can find it later
        node_item.setData(("node", node.node_id), Qt.UserRole)
        
        # Save to registry for instant updates later
        self._registry[("node", node.node_id)] = node_item
        
        # Loop through the Node's CBUS 'ev' objects and add as children
        # Iterate over the values of the events dictionary to get the VLCBev objects
        for ev in node.ev.values(): 
            self._add_ev_to_node(node_item, node.node_id, ev)
            
        # Add the fully built Node (with its children) to the root category
        self.hardware_root.appendRow(node_item)

    def add_gui_node(self, node):
        print (f"System Explorer Adding gui node {node}")
        """Creates a Node row and its children."""
        # Create the Node Item using its built-in string representation
        node_item = QStandardItem(str(node))
        node_item.setEditable(False)
        
        # Stash the ID in the item so clself._registry.get(("node", event.node_id))icks can find it later
        node_item.setData(("gui", node.node_id), Qt.UserRole)
        
        # Save to registry for instant updates later
        self._registry[("gui", node.node_id)] = node_item
        
        # # Loop through the Node's CBUS 'ev' objects and add as children
        # # Iterate over the values of the events dictionary to get the VLCBev objects
        # for ev in node.ev.values(): 
        #     self._add_ev_to_node(node_item, node.node_id, ev)
            
        # Add the fully built Node (with its children) to the root category
        self.layout_root.appendRow(node_item)

    def _add_ev_to_node(self, parent_node_item, node_id, ev):
        """Helper to create child EV rows."""
        # Assuming VLCBev has a __str__ method, otherwise use f"EV {ev.ev_id}: {ev.state}"
        ev_item = QStandardItem(str(ev))
        ev_item.setEditable(False)
        ev_item.setData(("ev", node_id, ev.ev_id), Qt.UserRole)
        
        # Register the specific EV for fast updates using the string ev_id
        self._registry[("ev", node_id, ev.ev_id)] = ev_item
        
        # Attach to the Node, not the root!
        parent_node_item.appendRow(ev_item)

    # def add_layout_object(self, layout_obj):
    #     """Creates a Layout object row."""
    #     item = QStandardItem(f"{layout_obj.name}")
    #     item.setEditable(False)
    #     item.setData(("layout", layout_obj.id), Qt.UserRole)
    #     self._registry[("layout", layout_obj.id)]
    #     self.layout_root.appendRow(item)

    # -------------------------------------------------------------------
    # EVENT UPDATES
    # -------------------------------------------------------------------
    def _wire_events(self):
        """Listen to the Event Bus for live changes."""
        event_bus.node_updated_signal.connect(self.on_device_event)
        # Same for gui objects - although less likely to be added in
        # real time this avoids needing to handle new objects differently
        print(f"Connecting to bus ID: {id(event_bus)}")
        event_bus.layout_updated_signal.connect(self.on_layout_event)

    def on_layout_event(self, event):
        print (f"System explorer Layout event {event}")

    def on_device_event(self, event):
        """Updates the tree instantly when hardware changes."""
        # Note: There is no delete there is currently no way to know
        # if an device disappears 
        # Isn't normally an issue as wouldn't normally remove
        # a device during a running session
        # Could consider either periodical check for active
        # and/or a refresh which clears all entries and sends a new 
        # discover
        print (f"System explorer new device event {event}")
        
        # If an entirely new node appeared on the network
        if event.get_attr("action") == "new_node":
            print (f"System explorer adding node {event}")
            self.add_hardware_node(event.get_node_object())

        elif event.get_attr("action") == "update_node":
            # actual node from the event
            node_object = event.get_node_object()
            # node item from the treeview
            node_item = self._registry.get(("node", node_object.get_node_id()))
            # if already exists
            if node_item:
                node_item.setText(str(node_object))
            # otherwise it's a new object (node_id changed)
            else:
                self.add_hardware_node(node_object)

        elif event.get_attr("action") == "new_ev":
            # To add a new_ev - first need to get it's parent node 
            ev_object = event.get_ev_object()
            parent_node_id = ev_object.get_node_id()
            parent_item = self._registry.get(("node", parent_node_id))
            self._add_ev_to_node(parent_item, parent_node_id, ev_object)

            
        # If an existing EV changed state (e.g., sensor triggered)
        elif event.get_attr("action"):
            # Instantly find the visual row using our registry cache and the string ev_id
            ev_item = self._registry.get(("ev", event.node_id, event.ev_id))
            
            # If it exists, update the text! No searching required.
            if ev_item:
                # Assuming the event payload has the updated object or state string
                ev_item.setText(str(event.ev_object))

    ## TODO Legacy methods - need updating

            
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
            if isinstance(self.selected_node, GuiObject):
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


    def update_tree_selected(self, node_item):
        self.selected_node = None
        
        # Cleanly resolve the node and top-level strings
        node_string = node_item.text()
        parent_item = node_item.parent()
        top_string = parent_item.text() if parent_item else node_string

        # Route to the appropriate handler
        if top_string.startswith("GUI"):
            self._set_gui_selected_node(node_item)
        else:
            self._handle_standard_node(node_item, node_string)

        self.update_table()

    def _set_gui_selected_node(self, node_item):
        """Helper to find and set a GUI specific node."""
        for gui_node in device_model.other_nodes['Gui']:
            new_item = gui_node.check_item(node_item)
            if new_item is not None:
                self.selected_node = new_item
                break  # Stop searching once we find the match
                
    def _handle_standard_node(self, node_item, node_string):
        """Helper to handle standard nodes and their associated UI button states."""
        # Use a tuple to cleanly check for multiple prefixes at once
        if node_string.startswith(("CANCAB", "CANCMD")):
            self.update_node_buttons(None, None)
        else:
            self.update_node_buttons("On", "Off")
            
        # Check device_model for the node
        for key, node in device_model.nodes.items():
            new_item = node.check_item(node_item)
            if new_item is not None:
                self.selected_node = new_item
                break  # Stop searching once we find the match

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
            

    # node_item is type VLCBEv
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