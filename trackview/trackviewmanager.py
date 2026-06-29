# TrackView manager - based on the previous
# Device Model (Domain Model)
# provides a way to access TrackViewNodes (from Layout) 
# without needing to be part of the layout
import os
import json
import itertools
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from core import event_bus
from pyvlcb import VLCB
from pyvlcb.utils import bytes_to_addr
from device.vlcbnode import VLCBNode
from vlcbclient import VLCBClient
from events import DeviceEvent, LocoEvent, AppEvent, GuiEvent, TimerEvent



class TrackViewManager(QObject):

    def __init__(self):
        super().__init__()
        
        self.debug = False
        # links back to the layout which owns the actual objects
        self.active_layout = None

        # These are TrackViewNodes

        # Uses list from layout


        # dict of nodes indexed by NN
        # A Gui object does not have a node_id by default
        # Instead one is allocated dynamically based on 
        # node_index
        #self.nodes = {}
        # Number nodes is an itertools.count which 
        # ensures don't allocate a new one.
        # Note we should not be removing nodes, but even if do
        # don't ever decrement this value
        # Unless resetting and also clearing out the self.nodes (load new layout)
        #self.node_index = itertools.count(start=0)
        # To get next value use next(num_index) but subtract 1 to get index value

                      
        # layout used for getting user name for devices
        self.layout = None

    def register_layout(self, layout_instance):
        self.active_layout = layout_instance

    def get_all_nodes(self):
        return self.active_layout.track_view_nodes
    

    # Return Gui object matching name
    # Or return None
    def get_track_view_node_from_name (self, name):
        return self.active_layout.get_node_from_name(name)
        
                
    # Get list of nodes by names
    # null_events determines whether to check if the nodes must have events
    def get_nodes_names(self, null_events=True):
        node_list = []

        for node in self.active_layout.track_view_nodes:
            # if no children and don't want (eg. when selecting a child)
            # skip
            if null_events == False and node.num_children() < 1:
                continue
            node_list.append(node.name)

        return node_list
    
    # # From name to key for DeviceEvents
    # # Key is node_id so returning key will return node_id
    # def name_to_key(self, name, type="VLCB"):
    #     if type == "VLCB":
    #         for key in self.nodes.keys():
    #             # match on either name or string
    #             if self.nodes[key].name == name or str(self.nodes[key]) == name:
    #                 #print (f"name match {name}, key {key}")
    #                 return key
    #     elif type == "Loco":
    #         print ("WARNING: name_to_key for locos - moved to locomanager")
    #         # Convert ID {num} to int num
    #         # very basic assumes fixed format (as used in combo)
    #         return int(name.split(" ")[1])
    #     elif type in self.other_nodes.keys():
    #         for i in range(len(self.other_nodes[type])):
    #             if self.other_nodes[type][i].name == name:
    #                 return i
    #     return None

    def key_to_name (self, key):
        if key in self.nodes.keys():
            return self.nodes[key].name
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
        
        
    def node_exists (self, node):
        if node in self.nodes.keys():
            return True
        return False
    

    # # Add GUI node - passes gui_object to add
    # def add_gui_node (self, gui_object):
    #     # If already has a node_id then already added
    #     if gui_object.node_id != None:
    #         print (f"Warning guid_node already exists {gui_object}")
    #         return False
    #     # Get node_id in a thread safe way
    #     gui_object.node_id = next(self.node_index) - 1
    #     self.nodes[gui_object.node_id] = gui_object
    #     # Note that if this is added before systemmanager then 
    #     # the signal does not go anywhere - instead loaded by 
    #     # Initial object scan. This is here is subsequent updates are
    #     # made to the GUI that need to be updated in the tree etc.
    #     event_bus.layout_updated_signal.emit (GuiEvent({
    #         "action": "new_node",
    #         "node_object": gui_object
    #     }))
    #     return True


    def set_name (self, node_id, name):
        if node_id not in self.nodes.keys():
            return False
        # This must be through method and not directly editing name
        # so as to be updated in the QStandardItem
        self.nodes[node_id].set_name(name)
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

    
    
    def add_variable (self, variable_name):
        self.other_nodes['Variable'].append(variable_name)

    def get_variable_names (self):
        return self.other_nodes['Variable']



# Singleton for the Device Model
track_view_manager = TrackViewManager()
