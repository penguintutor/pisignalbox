# Device manager - based on the previous
# Device Model (Domain Model)
# manages the logical state of devices
import os
import json
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from core import event_bus
from pyvlcb import VLCB
from pyvlcb.utils import bytes_to_addr
from .vlcbnode import VLCBNode
from vlcbclient import VLCBClient
from events import DeviceEvent, LocoEvent, AppEvent, GuiEvent, TimerEvent


# Many of the methods in there (particularly when related to self.locos)
# are just used to hand off to the other class. This maintains device_model as
# the primary interface to decouple from LocoList etc.

class DeviceManager(QObject):
    

    def __init__(self):
        super().__init__()
        
        self.debug = False

        # dict of nodes indexed by NN
        self.nodes = {}
                      
        # layout used for getting user name for devices
        self.layout = None
               
    def get_all_nodes(self):
        return self.nodes.values() 
    
    # Get list of nodes by names
    # Default Only return vlcb nodes
    # null_events determines whether to check if the nodes must have events
    def get_nodes_names(self, null_events=True):
        node_list = []

        node_list.extend(
            node.name for node in self.nodes.values() 
            if null_events or node.numev > 0
        )

        return node_list
    
    # From name to key for DeviceEvents
    # Key is node_id so returning key will return node_id
    def name_to_key(self, name):
        for key in self.nodes.keys():
            # match on either name or string
            if self.nodes[key].name == name or str(self.nodes[key]) == name:
                #print (f"name match {name}, key {key}")
                return key
        return None

    def key_to_name (self, key):
        if key in self.nodes.keys():
            return self.nodes[key].name

    # Based on node_id and evnaame get event_id
    def evname_to_evid (self, node_id, evname):
        node = self.nodes[node_id]
        for key in node.ev.keys():
            # Allow either event name, or if used in dialog allow __str__ format
            if node.ev[key].name == evname or str(node.ev[key]) == evname:
                return key
        return None
        
    
    # get events for specified node
    def get_events(self, node):
        #print (f"Get events {node}, {type}")
        if node in self.nodes.keys():
            return self.nodes[node].get_ev_names()
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
    def add_node (self, node_id):
        if node_id not in self.nodes.keys():
            self.nodes[node_id.node_id] = node_id
            # Also set name
            self.set_name (node_id.node_id, f"Temp Node Name: {node_id.node_id}")
            
            # Add the node to the top level of the qtreeview
            # child nodes are added through the node as child on gui_node
            # Gui node handled separately in system_manager
            #self.node_model.appendRow(self.nodes[node.node_id].get_gui_node())
            event_bus.node_updated_signal.emit (DeviceEvent({
                "action": "new_node",
                "node_object": self.nodes[node_id.node_id]
            }))
            return True
        return False
    

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
        #self.add_node_signal.emit (self.nodes[node_id].gui_node, ev_node.gui_node)
        # Update the name based on layout
        # Todo add this feature back - using layout for names
        #name = self.layout.ev_name(node_id, ev_id, en)
        #self.update_ev(node_id, ev_id, "name", name)
        # Notify of new node
        event_bus.node_updated_signal.emit (DeviceEvent({
            "action": "new_ev",
            "node_object": self.nodes[node_id],
            "ev_object": ev_node
        }))

        return True

    def update_node (self, node_id, upd_dict):
        # Make sure node_id exists - otherwise abort
        # Hopefully already checked this - but just in case
        if node_id not in self.nodes:
            return 0
        
        num_updates = self.nodes[node_id].update_node(upd_dict)

        # If don't make any changes then no need to broadcast update
        if num_updates < 1:
            return 0
        
        # Notify of update
        event_bus.node_updated_signal.emit (DeviceEvent({
            "action": "update_node",
            "node_object": self.nodes[node_id]
        }))

    
    # updates event, field is the field to update (eg. "name")
    def update_ev (self, node_id, ev_id, field, value):
        if node_id not in self.nodes.keys():
            return False
        return self.nodes[node_id].update_ev(ev_id, field, value)
        



    def get_device_info(self, device_id: str):
        return self._devices.get(device_id, {})
    
    
    def add_variable (self, variable_name):
        self.other_nodes['Variable'].append(variable_name)

    def get_variable_names (self):
        return self.other_nodes['Variable']


# Singleton for the Device Model
device_manager = DeviceManager()
