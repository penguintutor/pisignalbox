import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPixmap
import logging
from layout import Layout
from pyvlcb import VLCB
from pyvlcb.utils import bytes_to_addr
from loco import Loco
from core import ApiHandler
from core import event_bus
from loco import loco_manager
from events import AppEvent, LocoEvent

logger = logging.getLogger(__name__)

# Tracks and generates events(activities) against a loco
# When we receive / send an event do we need to update devices and corresponding objects
# Currently heavily reliant on mw (mainwindow) from the parent
# perhaps decouple in future
class ControlLoco:
    def __init__(self):
        # Store a link to the loco (obtained from loco_manager)
        # Refer to self.loco 
        self.loco = None
        # loco moved to loco_manager

        
    def event_trigger (self, event):
        #print (f"ControlLoco received event {event.event_type} data {event.data}")
        if event.event_type == "PLOC":
            data = event.data
            self.set_session (data['Session'])
            self.set_speeddir (data['Speeddir'])
            self.set_functions (data['Fn1'], data['Fn2'], data['Fn3'])
            self.set_status (data['Status'])
        elif event.event_type == "ERR":
            self.handle_error (event.data)
        

    def handle_error(self, error_data):
        """
        Handle loco errors

        Depending upon the error code the data may have different interpretations
        Stored as Byte1, Byte2, ErrCode - where Byte1,Byte2 may eqal AddrHigh_AddrLow, or
        may be Byte1 = Session ID, Byte 2 = 0
        """
        match error_data:    
            # ---------------------------------------------------------
            # ErrCode 1: Error - no sessions available
            # ---------------------------------------------------------
            case {"ErrCode": 1, "Byte1": byte1, "Byte2": byte2}:
                if not self.is_acquiring():
                    logger.debug("Not acquiring loco - ignoring error")
                    return
                
                loco_id = bytes_to_addr(byte1, byte2) & 0x3FFF
                
                if self.get_id() != loco_id:
                    logger.debug(f"ERR ID {loco_id} does not match current Loco ID {self.get_id()}")
                    return
                    
                if self.loco is not None:
                    event_bus.publish(AppEvent({
                        "action": "uitext", 
                        "label": "locoStatusLabel", 
                        "value": "Error - no sessions available", 
                        "loco_id": self.loco.loco_id
                    }))

            # ---------------------------------------------------------
            # ErrCode 2: Already taken - option to steal
            # ---------------------------------------------------------
            case {"ErrCode": 2, "Byte1": byte1, "Byte2": byte2}:
                logger.debug("Error code 2 - loco taken")
                
                # Only for us if we haven't completed the session setup
                if self.get_status() == "on" or not self.is_acquiring():
                    return
                    
                loco_id = bytes_to_addr(byte1, byte2) & 0x3FFF
                
                if self.get_id() != loco_id:
                    logger.debug(f"ERR ID {loco_id} does not match current Loco ID {self.get_id()}")
                    return
                    
                if self.loco is not None:
                    event_bus.publish(AppEvent({
                        "action": "locotaken", 
                        "loco_id": self.loco.loco_id
                    }))

            # ---------------------------------------------------------
            # ErrCode 8: Session cancelled
            # ---------------------------------------------------------
            case {"ErrCode": 8, "Byte1": byte1}:
                if self.is_acquiring():
                    return
                    
                # Note: Byte2 is intentionally excluded from the match pattern 
                # above because dict matching does a partial match (it ignores extra keys).
                session_id = int(byte1)
                
                if session_id != 0 and session_id == self.get_session():
                    logger.debug(f"Session cancelled {session_id}")
                    self.reset_loco()
                    if self.loco is not None:
                        event_bus.publish(AppEvent({
                            "action": "resetloco", 
                            "loco_id": self.loco.loco_id
                        }))
                else:
                    logger.debug(f"Session not cancelled {session_id}, loco session {self.get_session()}")
                    
            # ---------------------------------------------------------
            # Fallback for unhandled error codes
            # ---------------------------------------------------------
            case _:
                logger.debug(f"Unknown error code caught in ControlLoco handle_error {error_data["ErrCode"]}")


    def is_active(self):
        if self.loco == None:
            return False
        return self.loco.is_active()
    
    def get_direction(self):
        # defaults to 1 if no loco specified
        if self.loco == None:
            return 1
        return self.loco.direction
    
    def speed_value(self):
        return self.loco.speed_value()
    
    def get_name(self):
        return self.loco.loco_name
    
    # Id is the loco id (eg DCC/running number) not index
    def get_id(self):
        #print (f"Loco index {self.loco_index} id {self.loco.loco_id} name {self.loco.loco_name}")
        # Removed error handling - instead use try except
        #if not isinstance(self.loco, Loco):
        #    return None
        return self.loco.loco_id
    
    def is_acquiring(self):
        return self.loco.is_acquiring
    
    def get_session (self):
        if self.loco == None:
            return None
        return self.loco.session
    
    def set_session (self, session):
        if self.loco == None:
            return None
        self.loco.session = session
    
    # Sets speed and direction together
    def set_speeddir (self, speeddir):
        if self.loco == None:
            return None
        self.loco.set_speeddir(speeddir)
        
    def get_speeddir (self):
        return self.loco.get_speeddir()
    
    def get_functions (self):
        if self.loco == None:
            return []
        return self.loco.get_functions()
    
    def set_functions (self, fn1, fn2, fn3):
        if self.loco == None:
            return []
        self.loco.set_functions(fn1, fn2, fn3)
        
    def get_function_status (self, func_index):
        # get [status, type]
        return (self.loco.get_function_status(func_index))
    
    # This is the low level status - perhaps use is_acquiring or a similar method instead
    def get_status (self):
        if self.loco == None:
            return None
        return self.loco.status
    
    def set_status (self, value):
        if self.loco == None:
            return None
        # Set controller - which triggers steal dialog if required
        # Note ignored if not value == 'rloc'
        self.loco.set_status(value, "controller")
        
    def set_function_dfun (self, func_index, value):
        # for a list need brackets around the method - or store in temp variable
        return (self.loco.set_function_dfun (func_index, value))

        
    def function_reset (self):
        self.loco.function_reset()

    def release (self):
        # Release old loco
        if self.loco.status == "on" and self.loco.session != 0:
            # Sends a release but doesn't check for a response
            #event_bus.publish(GuiEvent("start_request", {'command': 'release_loco', 'arg1': self.loco.session}))
            # Seperate request for GUI elements
            self.loco.released()
            # Normally would want to stop the keep alive but we are hoping to acquire a new session immediately after
            # So the keep alive will just ignore until acquired

        
    # Update function selected features
    # When combobox / tab selected
    def function_selected (self, func_index):
        if self.loco != None:
            # get [status, type]
            status = self.loco.get_function_status(func_index)
        else:
            status = None
        # If we don't have a status then the function button doesn't exist
        if status == None:
            return (" - ")
        # If trigger then button should be activate:
        if status[1] == "trigger":
            return ("Activate")
        elif status[1] == "latch":
            # if on - button will turn off
            if status[0] == 1:
                return ("Turn Off")
            else:
                return ("Turn On")
        # Eg if status is none then not supported
        else:
            return (" -- ")
            
            
    def steal_loco (self):
        # Check we have valid loco_id (if not reset)
        if (self.loco.loco_id == 0):
            self.reset_loco()
            return ""
        loco_name = self.loco.loco_name
        self.loco.status = 'gloc'
        return (f"Stealing {loco_name}")
        
    def share_loco (self):
        # Check we have valid loco_id (if not reset)
        if (self.loco.loco_id == 0):
            self.reset_loco()
            return ""
        loco_name = self.loco.loco_name
        return (f"Req sharing {loco_name}")
        
        
    # Reset remove references
    # Does not update GUI / remove keepalives
    # those should be handled by calling code
    def reset_loco (self):
        self.loco.reset()
        # Send keepalive signal
        #event_bus.publish(AppEvent({"action":"keepalive", 'loco_id': self.loco_id}))
        # Change combo after reset - that way the post change
        # will not send a release message
        
    ### Function change and Function Trigger are tied into QTimer so need to be part of mainwindow
    # This is used based on the dial
    # Returns True if the loco is active - else false
    def change_speed (self, new_speed):
        # If not in a session then ignore
        if self.loco != None and self.loco.is_active():
            # Special case if stop and 0 then reset stop
            if self.loco.status == "stop" and new_speed == 0:
                self.loco.status = "on"
            self.loco.set_speed (new_speed)
            return True
        return False
        
        
    def forward (self):
        self.loco.set_direction (1)
        if self.loco.is_active():
            return True
        return False
        
    def reverse (self):
        self.loco.set_direction (0)
        if self.loco.is_active():
            return True
        return False
        
        
    # Emergency stop - current loco
    # To reset need to set speed to 0 on the dial
    def stop (self):
        self.loco.set_stop()
        if self.loco.session != 0:
            # check we have a session
            # don't check speed as this is emergency stop so send regardless
            return True
        return False
        
    # Same as a stop as far as ControlLoco is concerned
    def stop_all (self):
        self.stop()
