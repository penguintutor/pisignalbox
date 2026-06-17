# Loco manager - based on the previous
# Device Model (Domain Model)
# manages the logical state of locos
import os
import json
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from core import event_bus
from pyvlcb import VLCB
from pyvlcb.utils import bytes_to_addr
from vlcbnode import VLCBNode
from vlcbclient import VLCBClient
from .locolist import LocoList
from events import DeviceEvent, LocoEvent, AppEvent, GuiEvent, TimerEvent


# Many of the methods in there (particularly when related to self.locos)
# are just used to hand off to the other class. This maintains loco_manager as
# the primary interface to decouple from LocoList etc.

class LocoManager(QObject):
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

    # This was previously name_to_key - now specific to locos
    # From name to key for Locos
    # Key is node_id so returning key will return node_id
    def loco_name_to_key(self, name):
        # Convert ID {num} to int num
        # very basic assumes fixed format (as used in combo)
        return int(name.split(" ")[1])

    # This was previously key_to_name - now specific to locos
    def loco_key_to_name (self, key):
        return f"ID {key}"

       
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
            
    # uses filename only (strip using basename prior to calling this)
    def get_loco_from_filename (self, filename):
        # pass to locolist to reduce coupling
        return self.locos.get_loco_from_filename (filename)

# Singleton for the LocoManager
loco_manager = LocoManager()
