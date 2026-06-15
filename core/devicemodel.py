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
from locolist import LocoList
from loco import Loco
from deviceevent import DeviceEvent
from locoevent import LocoEvent
from appevent import AppEvent
from guievent import GuiEvent
from timerevent import TimerEvent


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
        
        # Locos is now replaced with a LocoList (object containing a list not a python list)
        # can't create until we've loaded the directories so set to None initially
        # Need to check it's not None before use
        self.locos = None

        # Monitor for loco events - eg. PLOC
        event_bus.loco_event_signal.connect (self.event_trigger)
        
        # These directories and filenames as specified when first loading the loco
        # Listed here for easy reference
        self.locos_dir = None
        
        # Track which locos are enabled (by filename)
        # Initially set based on settings file but then
        # Updated as clicked from locowindow
        #self.enabled_locos = []
        # moved to locos
        # self.locos.enabled_locos

        
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
        
        # Subscribe to events from the API layer
        #event_bus.device_event_signal.connect(self._update_device_status)
        #event_bus.gui_event_signal.connect(self._update_layout_status)
        
        # layout used for getting user name for devices
        self.layout = None
        # Also add any node information to QStandardItemModel
        # The GUI nodes are contained within the node class instances. This is specific to the node list in TreeView
        self.node_model = QStandardItemModel()
        self.node_model.setHorizontalHeaderLabels(['Nodes'])

    def locos_active (self):
        """ How many locos are active """
        active_locos = 0
        for loco in self.locos.get_all_locos():
            if loco.is_active():
                active_locos += 1
        return active_locos

    def event_trigger (self, event):
        #print (f"ControlLoco received event {event.event_type} data {event.data}")
        if event.event_type == "PLOC":
            loco_id = event.data.get('Loco_id', "")
            for loco in self.locos.get_all_locos():
                if loco_id == loco.loco_id:
                    loco.acquired(
                        event.data.get('Session'),
                        event.data.get('Speeddir'),
                        (event.data.get('Fn1'), event.data.get('Fn2'), event.data.get('Fn3'))
                    )
        elif event.event_type == "ERR":
            self.handle_error (event.data)

    def loco_from_id (self, loco_id):
        for loco in self.locos.get_all_locos():
            if loco.loco_id == loco_id:
                return loco
        return None
    
    def loco_from_session (self, session_id):
        """ Get loco based on session id"""
        # If session id is 0 then ignore
        if session_id == 0:
            return None
        for loco in self.locos.get_all_locos():
            if loco.session == session_id:
                return loco
        return None
    

    def handle_error(self, error_data):
        """Routes locomotive errors to their specific handler based on ErrCode."""
        err_code = error_data.get('ErrCode')
        
        # Dispatch dictionary mapping error codes to handler functions
        handlers = {
            1: self._handle_err_stack_full,
            2: self._handle_err_loco_taken,
            8: self._handle_err_session_cancelled
        }
        
        handler = handlers.get(err_code)
        if handler:
            handler(error_data)
        elif self.debug:
            print(f"Unhandled loco error code: {err_code} - Data: {error_data}")

    def _get_loco_from_bytes(self, byte1, byte2):
        """Helper to extract loco ID and object from error bytes."""
        loco_id = bytes_to_addr(byte1, byte2) & 0x3FFF
        return loco_id, self.loco_from_id(loco_id)

    def _handle_err_stack_full(self, error_data):
        """Handles ErrCode 1: Loco stack full (only valid during acquiring)."""
        loco_id, loco = self._get_loco_from_bytes(error_data['Byte1'], error_data['Byte2'])
        
        if loco is None:
            print(f"Loco Error 1 - Not acquiring loco {loco_id} - ignoring error")
            return
            
        loco.set_status("error")
        
        if loco.acquired_by == "controller":
            event_bus.publish(AppEvent({
                "action": "uitext", 
                "label": "locoStatusLabel", 
                "value": "Error - no sessions available", 
                "loco_id": self.loco.loco_id
            }))

    def _handle_err_loco_taken(self, error_data):
        """Handles ErrCode 2: Loco already taken."""
        if self.debug:
            print("Error code 2 - loco taken")
            
        loco_id, loco = self._get_loco_from_bytes(error_data['Byte1'], error_data['Byte2'])
        
        if loco is None:
            print(f"Loco Error 2 - Not acquiring loco {loco_id} - ignoring error")
            return
            
        if loco.acquired_by != "controller":
            event_bus.publish(LocoEvent('api', {
                'command': "share",
                'loco_id': loco_id
            }))
            loco.set_status("gloc")
            
        event_bus.publish(AppEvent({"action": "locotaken", 'loco_id': loco_id}))

    def _handle_err_session_cancelled(self, error_data):
        """Handles ErrCode 8: Session cancelled."""
        session_id = int(error_data['Byte1'])
        
        if self.debug:
            print(f"Session cancel for session_id {session_id}")
            
        loco = self.loco_from_session(session_id)
        
        if loco is None:
            if self.debug:
                print("Not a valid loco - ignoring")
            return

        if self.debug:
            # Fixed: loco_id was previously undefined here. Falling back to session_id.
            print(f"Session cancelled {session_id} successfully.")
            
        loco.reset()
        event_bus.publish(AppEvent({"action": "resetloco", 'loco_id': self.loco.loco_id}))

        
    # Enable / disable locos
    # Does not report back if successful (if already that state then just silently ignores)
    def enable_loco (self, filename):
        if filename not in self.locos.enabled_locos:
            self.locos.enabled_locos.append(filename)
            
    def disable_loco (self, filename):
        if filename in self.locos.enabled_locos:
            self.locos.enabled_locos.remove(filename)
            
    # Enable multiple locos from a list
    def enable_locos (self, loco_list):
        # Add individually - which will skip any that don't exist as locos
        for loco_filename in loco_list:
            self.enable_loco (loco_filename)
            
    def get_enabled_loco_filenames (self):
        # Get enabled_locs as list of filenames (no path)
        return self.locos.enabled_locos

    # Get the loco object from the loco name
    def get_loco_from_name (self, name):
        return self.locos.get_loco_from_name (name)
    
    # Does the loco filename already existing in the loaded locos
    # Doesn't check if the file exists, just if it's loaded
    def check_loco_filename (self, filename):
        if filename in self.locos.locos:
            return True
        return False

            
    # Load the locos file by opening in LocoList 
    def load_locos (self, locos_path, locos_filename):
        # Is this the first time we've seen locos_dir?
        # if so save - if not then ignore the path
        if self.locos_dir == None:
            self.locos_dir = locos_path
        # If the LocoList is not initialized then we do that here
        if self.locos == None:
            self.locos = LocoList (self.locos_dir, locos_filename)
        # If not then call load file against existing
        else:
            self.locos.load_file (locos_filename)
            
    def import_loco (self, filename):
        self.locos.load_loco (filename)

    # Get all locos as Loco objects            
    def get_all_locos (self):
        return self.locos.get_all_locos()
    
    # Get enabled locos - returns list of displaynames (or equivelant)
    def get_enabled_locos (self):
        # If locos not initialised yet return empty list
        if self.locos == None:
            return []
        #print (f"Returning enabled locos {self.locos.get_enabled_locos()}")
        return self.locos.get_enabled_locos()
                

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
        
    # Default add a loco with no details
    # Note that this does not save the file, or add it to the locos.json file
    # Instead that needs to be called separately when confirming
    # that the save was successful
    def add_loco (self, filename, loco_id=0):
        new_loco = self.locos.add_loco(filename, loco_id)
        return (new_loco)
    
    # Remove loco - if deleted or fail to save
    # delete = False does not clean up the <loco>.json file
    # Set to true to remove the loco file (images are not deleted in case used elsewhere)
    def remove_loco (self, filename, delete=False):
        self.locos.remove_loco (filename, delete)
    
    # Save locos to file
    def save_locos (self):
        self.locos.save_file()
        
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
    
    # uses filename only (strip using basename prior to calling this)
    def get_loco_from_filename (self, filename):
        # pass to locolist to reduce coupling
        return self.locos.get_loco_from_filename (filename)

    def add_variable (self, variable_name):
        self.other_nodes['Variable'].append(variable_name)

    def get_variable_names (self):
        return self.other_nodes['Variable']




# Singleton for the Device Model
device_model = DeviceModel()
