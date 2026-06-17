# Device Model or known as a Domain Model
# manages the logical state of devices
import os
import json
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from core import event_bus
from pyvlcb import VLCB
from pyvlcb.utils import bytes_to_addr
from vlcbnode import VLCBNode
from vlcbclient import VLCBClient
from events import DeviceEvent, LocoEvent, AppEvent, GuiEvent, TimerEvent


# Many of the methods in there (particularly when related to self.locos)
# are just used to hand off to the other class. This maintains device_model as
# the primary interface to decouple from LocoList etc.

class DeviceModel(QObject):
    # This signal is internal to the model or for ViewModels to subscribe to
    # to react to state changes in the core data.
    # model_updated = Signal(str) # Emits device_id when its state changes
    
    # Map to Classes
    event_map = {
        'VLCB': DeviceEvent,		# This should be used in preference to Device
        'Device': DeviceEvent,
        'Loco': LocoEvent,
        'App': AppEvent,
        'Gui': GuiEvent,
        'Timer': TimerEvent
        }
    
    # Used to update treeview on gui thread
    add_node_signal = Signal(QStandardItem, QStandardItem)

    def __init__(self):
        super().__init__()
        
        self.debug = False

        # dict of nodes indexed by NN
        self.nodes = {}
               
        # Other nodes are stored in here for lookup in menus or eventbus
        # Every "node" must be added to the device model
        self.other_nodes = {
            'App': [],
            'Gui': [],
            # 'DeviceEvent': [], # Device are stored in self.nodes
            # 'Loco': [], # Loco are in self.locos
            'Timer': [],
            'Variable': []	# Use to get and set variables - can trigger events as well
            # Variables are global across the app, but can prefix with specific automation
            # to avoid conflicts eg. "engshed1_variable1"
            # Note that the actual variables are not stored in the device_model - there names are
            # Added here for lookup by menus etc. but all updates are via the mainwindow self.appvariables
            # which are then in the AppVar class
            # should be set using the following methods (in mainwindow.appvariables) so that they are also reflected here
            # and can also trigger events.
            # get_variable(variable_name), set_variable(variable_name, new_value), inc_variable(variable_name, inc_amount)
        }
        
        
        # layout used for getting user name for devices
        self.layout = None
        # Also add any node information to QStandardItemModel
        # The GUI nodes are contained within the node class instances. This is specific to the node list in TreeView
        self.node_model = QStandardItemModel()
        self.node_model.setHorizontalHeaderLabels(['Nodes'])


    # Return Gui object matching name
    # Or return None
    def get_guiobject_name (self, name):
        for node in self.other_nodes['Gui']:
            if node.name == name:
                return node
        return None
        
    # Given a node respond with Event type
    # Eg. device, loco, app, gui, timer (in that order - if duplicate - although should not be duplicates) 
    def get_type_node (self, node_name):
        # First lookup own devices
        for key, this_node in self.nodes.items():
            if this_node.name == node_name:
                return "VLCB"
        # Check it's been initialised (not None)
        if self.locos != None:
            for loco in self.locos:
                if loco.name == node_name:
                    return "Loco"
        # Now included in tests
        for key in self.other_nodes.keys():
            for this_event in self.other_nodes[key]:
                #print (f"This event {this_event.name} node {node_name}")
                if this_event.name == node_name:
                    return this_event.type()
        # If not found return None
        return None
                
    # Get list of nodes by names
    # Default return All types - including VLCB & Gui etc.
    # null_events determines whether to check if the nodes must have events
    def get_nodes_names(self, node_type="all", null_events=True):
        node_list = []

        # 1. Handle VLCB devices
        if node_type in ("all", "VLCB"):
            node_list.extend(
                node.name for node in self.nodes.values() 
                if null_events or node.numev > 0
            )

        # 2. Handle Gui devices
        if node_type in ("all", "Gui"):
            node_list.extend(
                node.name for node in self.other_nodes['Gui']
            )

        return node_list
    
    # From name to key for DeviceEvents
    # Key is node_id so returning key will return node_id
    def name_to_key(self, name, type="VLCB"):
        if type == "VLCB":
            for key in self.nodes.keys():
                # match on either name or string
                if self.nodes[key].name == name or str(self.nodes[key]) == name:
                    #print (f"name match {name}, key {key}")
                    return key
        elif type == "Loco":
            print ("WARNING: name_to_key for locos - moved to locomanager")
            # Convert ID {num} to int num
            # very basic assumes fixed format (as used in combo)
            return int(name.split(" ")[1])
        elif type in self.other_nodes.keys():
            for i in range(len(self.other_nodes[type])):
                if self.other_nodes[type][i].name == name:
                    return i
        return None

    def key_to_name (self, key, type="VLCB"):
        if type == "VLCB":
            if key in self.nodes.keys():
                return self.nodes[key].name
        elif type == "Loco":
            print ("WARNING: key_to_name for locos - moved to locomanager")
            # key is loco ID
            return f"ID {key}"
        elif type in self.other_nodes.keys():
            if key < len(self.other_nodes[type]):
                return self.other_nodes[type][key].name
        # if no name found then name equals key
        return key

    # Based on node_id and evnaame get event_id
    def evname_to_evid (self, node_id, evname):
        node = self.nodes[node_id]
        for key in node.ev.keys():
            # Allow either event name, or if used in dialog allow __str__ format
            if node.ev[key].name == evname or str(node.ev[key]) == evname:
                return key
        return None
        
    
    # get events for specified node
    def get_events(self, node, type="VLCB"):
        #print (f"Get events {node}, {type}")
        if type == "VLCB":
            if node in self.nodes.keys():
                return self.nodes[node].get_ev_names()
        elif type == "Gui" or type == "User Interface":
            #A Gui has actions (rather than events) - currently hard coded
            # could add others if required based on actual Gui object
            return ["Toggle", "Set"]
        elif type in self.other_nodes.keys() and node in self.other_nodes[type]:
            #print (f"Checking for EVs {self.other_nodes[type]}")
            return self.other_nodes[type][node].get_ev_names()
        return []
        
    # set layout from mainwindow
    def set_layout (self, layout):
        self.layout = layout
        
        
    def node_exists (self, node):
        if node in self.nodes.keys():
            return True
        return False
    
    # Add node if not exist - else returnFalse
    # Only used for devices - also see add_gui_node
    def add_node (self, node):
        if node not in self.nodes.keys():
            self.nodes[node.node_id] = node
            # Also set name
            self.set_name (node.node_id, self.layout.node_name(node.node_id))
            
            # Add the node to the top level of the qtreeview
            # child nodes are added through the node as child on gui_node
            self.node_model.appendRow(self.nodes[node.node_id].get_gui_node())
            return True
        return False
    
    # Add GUI node - initially just add to tree view
    def add_gui_node (self, gui_object):
        # Adds this to the top level of the tree view
        # child nodes are added through the gui_object as child on gui_node
        self.node_model.appendRow(gui_object.get_gui_node())
        # Add the entire gui_object to other_nodes
        self.other_nodes['Gui'].append(gui_object)

    def set_name (self, node_id, name):
        if node_id not in self.nodes.keys():
            return False
        # This must be through method and not directly editing name
        # so as to be updated in the QStandardItem
        self.nodes[node_id].set_name(name)
        return True

    def set_numev (self, node_id, numev):
        if node_id not in self.nodes.keys():
            return False
        self.nodes[node_id].set_numev(numev)
        return True
    
    def set_evspc (self, node_id, evspc):
        if node_id not in self.nodes.keys():
            return False
        self.nodes[node_id].set_evspc(evspc)
        return True
    
    def add_ev(self, node_id, ev_id, en):
        #print (f"Adding EV {node_id}, {ev_id}, {en}")
        if node_id not in self.nodes.keys():
            return False
        # Add the EV
        ev_node = self.nodes[node_id].add_ev(ev_id, en)
        # Send signal so that the gui thread can perform addRow
        self.add_node_signal.emit (self.nodes[node_id].gui_node, ev_node.gui_node)
        # Update the name based on layout
        name = self.layout.ev_name(node_id, ev_id, en)
        self.update_ev(node_id, ev_id, "name", name)
        
        return True

    def update_node (self, node_id, upd_dict):
        return self.nodes[node_id].update_node(upd_dict)
    
    # updates event, field is the field to update (eg. "name")
    def update_ev (self, node_id, ev_id, field, value):
        if node_id not in self.nodes.keys():
            return False
        return self.nodes[node_id].update_ev(ev_id, field, value)
        
    
    def get_gui_node (self, node_id):
        return self.other_nodes["Gui"][node_id]


    def get_device_info(self, device_id: str):
        return self._devices.get(device_id, {})
    
    
    def add_variable (self, variable_name):
        self.other_nodes['Variable'].append(variable_name)

    def get_variable_names (self):
        return self.other_nodes['Variable']




# Singleton for the Device Model
device_model = DeviceModel()
