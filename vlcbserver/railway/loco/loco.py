# Loco within vlcbserver
# Because multiple clients could use locos then we load them anyway

# Holds a loco and it's session
import json
import logging
from vlcbserver.sse_broadcaster import SSEAnnouncer, announcer

logger = logging.getLogger(__name__)

class Loco:
    # All arguments have default allowing creation of a dummy loco
    # Normally use classmethod from_file to open an existing file
    # If filename specified must include full path
    def __init__ (self, loco_id=0, loco_ref = "", session=0, direction=1, speed=0, filename=None):
        # status starts in off, change to rloc when rloc sent, then on when allocated
        # if error after ploc then set to off
        # if gloc then set status to gloc - and then on after acquire (ploc)
        self.status = "off"   
        # Acquired by is what has requested the initial acquire - in case of ERR
        # If it's "controller" then can prompt the user whether to steal
        # If it's "manual" or "automate" then ignore
        self.acquired_by = ""   
        # Loco ID is the dcc ID - how we communicate with it
        self.loco_id = loco_id
        # The web app uses loco_ref which is filename (without .json)
        self.loco_ref = loco_ref
        self.loco_name = ""	# This needs to be unique (no checking so if not then the first will be returned)
        # Future - look to remove this unique dependency, perhaps use filename instead
        self.loco_data = {}
        self.session = session # If session == 0 then no session allocated (don't support none DCC)
        self.direction = direction # Values 1 = forward, 0 = reverse
        #self.speed = speed # Allow 0 to 128 but maximum sent is 127. Speed 1 = emergency stop (not used - instead status = stop)
        # This is a standardized speed 0 = stop, 1 = speed 1 etc. Up to 126 (above that is stored as 126 regardless)
        self._speed = speed # 0 to 126
        # Hold if the stop was due to an emergency stop (either CBUS speed =1 , or ermergency stop all)
        self.e_stop = False # True if emergency stop
        # Track all functions. Only F0 to F12 are found from PLOC - rest assume start off
        self.function_status = [0] * 29
        # Set filename to allow it to be saved - must be full path - this is unique
        # . review alternatives to using full path - although doesn't cause any issues with portability as not saved within file
        self.filename = filename


    @property
    def speed(self) -> int:
        """
        Standardized speed for the API, Web Client, and GUI Client.
        Always 0 when stopped (including during an E-Stop).
        """
        if self.e_stop:
            return 0
        return self._speed

    @speed.setter
    def speed(self, val: int) -> None:
        """
        Sets the logical speed from the API/UI.
        Setting a speed clears any active E-Stop state.
        """
        self._speed = max(0, min(int(val), 126))
        self.e_stop = False
        #print (f"railway/loco announce speed {self.loco_id} = {self._speed}")
        announcer.announce("loco_speed", {
            "loco_id" : self.loco_id,
            "speed": self._speed,
            "direction": self.direction
        })

    def emergency_stop(self) -> None:
        """Triggers an emergency stop regardless of the underlying controller."""
        self._speed = 0
        self.e_stop = True


    
    def get_id (self):
        return self.loco_id

    def get_direction (self):
        return self.direction

    # get normalised speed
    def get_speed (self):
        # Notes self.speed is a getter that handles the conversion already
        return self.speed

    # Sets the loco to stopped - ie. speed=0
    # emergency argument is provided for future use if need to track emergency vs standard stop
    def stop(self, emergency=False):
        # Just standard stop for now 
        # Future: consider whether the web UI should say
        # Emergency stop pressed etc.
        self._speed = 0
        if emergency:
            self.e_stop = True


    def set_status (self, value, acquired_by=""):
        """ set status - eg rloc if acquiring"""
        # acquired_by is optional - used if rloc, otherwise ignored
        self.status = value
        if value == "rloc":
            self.acquired_by = acquired_by

    def is_active (self):
        if self.status == "on":
            return True
        return False

    def get_session (self):
        return self.session

    def set_loco_acquire (self):
        # Note if we have a ploc then don't overwrite (most likely resend of rloc after aquired)
        if self.status != "ploc":
            self.status = "rloc"

    def acquired (self, session, speeddir, functions):
        self.session = session
        # note that acquired is called based on CBUS so it's speeddir (cbus value)
        # not speed_dir (which is kept as separate value)
        # The setting will perform the conversion
        self.set_speeddir (speeddir)    # converts to direction and speed
        self.set_functions (*functions)
        self.status = "on"
        #print (f"Loco {self.loco_id} acquired")

    def is_acquired(self):
        """Is the loco in an active session
        ie. session > 0
        """
        if self.session > 0 and self.status == "on":
            return True
        return False
        
    # Returns the display name / title
    def get_display_name(self):
        #print (f"Getting display name for loco: {self.loco_data}")
        return self.loco_data.get('displayname', 'Loco')
        
        
    # Returns filename. If not filename then return default so as valid image
    # Note that default.png must exist in the locos directory
    def get_image_filename (self):
        if 'image' in self.loco_data and self.loco_data['image'] != "":
            return self.loco_data['image']
        else:
            return "default.png"
    
    # Data is a dict of what to change
    # Changes info about the loco
    def update_loco (self, data):
        print (f"Updating loco {data}")
        for key, value in data.items():
            if key == 'address':
                self.loco_id = value
            #elif key == 'class':
            #    self.loco_class = value
            elif key == 'name':
                self.loco_name = value
            # Add to loco_data even if one of the special ones above
            self.loco_data[key] = value
        
    
    # Loads a json file with details of the loco
    # there are more details in the file - just pull out id and name for quick reference
    def load_file (self, loco_ref, filename):
        with open(filename, 'r') as data_file:
            self.loco_data = json.load(data_file)
        self.loco_ref = loco_ref
        self.loco_id = self.loco_data.get("address")
        self.loco_name = self.loco_data.get("displayname", "Loco")
        self.filename = filename
        
    # Returns True is successful save
    def save_file (self, filename=None):
        if filename == None:
            filename = self.filename
        try:
            with open(filename, 'w') as data_file:
                json.dump(self.loco_data, data_file, indent=4)
        # JSON serialization
        except TypeError as e:
            logger.warning (f"Loco save, JSON Serialization failed {e}")
            return False
        except PermissionError as e:
            logger.warning (f"Loco save, Permission denied {e}")
            return False
        except FileNotFoundError as e:
            logger.warning (f"Loco save, directory path does not exist {e}")
            return False
        # Catch all other system errors
        except OSError as e:
            logger.warning (f"Loco save, OS error writing to file {e}")
            return False
        return True
            
    # get number of functions
    # handles if none defined
    def num_functions (self):
        if "functions" in self.loco_data:
            return len(self.loco_data.get("functions", []))
        else:
            # If none then return 5 (just none defined)
            return 5
        
    # Resets the functions - sets to all 0
    def function_reset (self):
        num_functions = self.num_functions()
        # Minimum of 29 even if not used / available to allow dfun return codes
        if num_functions < 29:
            num_functions = 29
        self.function_status = [0] * num_functions
    
    def get_functions (self):
        """ Returns functions by title"""
        f_titles = []
        if "functions" not in self.loco_data.keys():
            # If no functions defined then provide some default
            return ["F0","F1","F2", "F3", "F4", "F5" ]
        for this_function in self.loco_data["functions"]:
            # Function titles includes Fx and text
            f_titles.append(f"{this_function[0]} - {this_function[1]}")
        return f_titles

    
    def get_function_bytes(self):
        data_out = [0, 0, 0]
        mask = [0b0001, 0b0010, 0b0100, 0b1000]
        
        # Handle the upper nibble bit stored at index 0
        if self.function_status[0]:
            data_out[0] |= 0b10000
            
        for i in range(0, 3):
            for j in range(0, 4):
                if self.function_status[(i * 4) + j + 1]:
                    data_out[i] |= mask[j]
                    
        return data_out[0], data_out[1], data_out[2]
    
    # Returns status (ie. 1 on / 0 off) and type "toggle" vs "latch"
    def get_function_status (self, func_num):
        # Check valid - should not get this as func_num should be based on the loaded functions
        if ("functions" not in self.loco_data.keys()) or (len(self.loco_data["functions"]) < func_num):
            return [self.function_status[func_num], "trigger"]
        this_function = self.loco_data["functions"][func_num]
        # 2 is type
        return [self.function_status[func_num], this_function[2]]

    def get_details_dict(self):
        """ get details for specified loco - returns in dict format
        used by loco_details """
        # Copies current state
        loco_dict = {
            "loco_id": self.loco_id,
            "loco_ref": self.loco_ref,
            "title": self.get_display_name(),
            "image_url": self.get_image_filename(),
            "summary": self.loco_data.get("summary")
        }
        return loco_dict
    
    # Do we have an active session (respond True even if force stop)
    def is_active (self):
        if self.session != 0 and (self.status == "on" or self.status == "stop"):
            return True
        return False
    
    # Is setup in progress (rloc / gloc)
    def is_acquiring (self):
        if self.status == 'gloc' or self.status == 'rloc':
            return True
        return False
    
    # normalize speed value 
    def speed_value (self):
        return self._speed
    
    # Same as release but also set loco_id to 0 to indicate none requested
    def reset (self):
        self.loc_id = 0
        self.released()
    
    # Use when loco released
    def released (self):
        self.status = "off"
        self.session = 0
        
    def session_established (self, session):
        # Add session id to the loco
        self.status = "on"
        self.session = session
        
    def get_speeddir(self) -> int:
        """
        Converts self.speed (display speed) and self.direction 
        into the combined CBUS speeddir byte.
        """
        if getattr(self, 'e_stop', False):
            cbus_speed = 1
        elif self.speed == 0:
            cbus_speed = 0
        else:
            cbus_speed = min(self.speed + 1, 127)

        # Combine with direction bit (assuming bit 7: 0x80 for forward)
        dir_bit = 0x80 if self.direction else 0x00
        return dir_bit | cbus_speed
    
    def set_speeddir(self, speeddir: int) -> None:
        """
        Unpacks an incoming CBUS speeddir byte (from PLOC or DSPD)
        into self.speed (display speed) and self.direction.
        """
        self.direction = bool(speeddir & 0x80)
        raw_speed = speeddir & 0x7F

        if raw_speed <= 1:
            self.speed = 0
            self.e_stop = (raw_speed == 1)
        else:
            self.speed = raw_speed - 1
            self.e_stop = False

    # Gets a status message about the loco
    def get_message (self):
        if self.status == "stop":
            return "Emergency Stop"
        return ""
    
    # emergency stop
    def set_stop (self):
        self.status = "stop"
        self.e_stop = True
      
    # Sets speed only - keep current direction
    # 0 = stop, 1 = vslow, 126 = amx speed
    def set_speed (self, speed_value):
        if speed_value < 0:
            return
        if speed_value > 126:
            speed_value = 126
        self.speed = speed_value

    # If required then use getters / setters from guiloco loco.py
    # # Direction is 1 for forward, 0 for reverse
    # # Could add support for other variable types
    # def set_direction (self, direction):
    #     if isinstance(direction, int) and (direction ==  0 or direction == 1):
    #         self.direction = direction
    #     # Otherwise just ignore
        
    # This sets the value of the functions from a PLOC message
    # Only stores values for F0 to F12
    # fn1 = <Dat5> is the function byte F0 to F4 - bit 5 = dir lighting (F0), bit 6 = direction, bit 7 = res, bit 8 = 0
    # fn2 = <Dat6> is the function byte F5 to F8 - bit 5 upwards reserved
    # fn3 = <Dat7> is the function byte F9 to F12
    def set_functions (self, fn1, fn2, fn3):
        data_in = [fn1, fn2, fn3]
        mask = [0b0001, 0b0010, 0b0100, 0b1000]
        # Handle 0 separately as it's in the upper nibble
        self.function_status[0] = data_in[0] & 0b10000
        for i in range (0, 3):
            for j in range (0, 4):
                self.function_status[(i*4)+j+1] = 1 if (data_in[i] & mask[j]) > 0 else 0
    

    # Sets function and returns bytes required for DFUN command
    # First byte is group (1 = F1 to F4, 2 = F5 to F8, 3 = F9 to F12)
    # 4 = F13 to 20, 5 = F21 to F27
    # Second byte is 1 bit per function - set 1 for on, 0 for off, lsb to right
    # eg. 1 = 0001, 2 = 0010
    # function = function number, on_off = 1 or 0
    # If on_off = None then return current status
    # function is always required as it only returns the related block
    def set_function_dfun (self, function, on_off=None):
        #print (f"Loco set_function_dfun - {function}, {on_off}, {self.function_status}")
        if function  > len (self.function_status):
            return None
        # if no change then skip
        if on_off != None:
            self.function_status[function] = on_off
        if function <= 4:
            byte1 = 1
            byte2 = (0b10000 * self.function_status[0] +  # fn0 is higher nibble (bit 5)
                     0b0001 * self.function_status[1] +
                     0b0010 * self.function_status[2] +
                     0b0100 * self.function_status[3] +
                     0b1000 * self.function_status[4]
                     )
        elif function <= 8:
            byte1 = 2
            byte2 = (0b0001 * self.function_status[5] +
                     0b0010 * self.function_status[6] +
                     0b0100 * self.function_status[7] +
                     0b1000 * self.function_status[8]
                     )
        elif function <= 12:
            byte1 = 3
            byte2 = (0b0001 * self.function_status[9] +
                     0b0010 * self.function_status[10] +
                     0b0100 * self.function_status[11] +
                     0b1000 * self.function_status[12]
                     )
        elif function <= 20:
            byte1 = 4
            byte2 = (0b0001 * self.function_status[13] +
                     0b0010 * self.function_status[14] +
                     0b0100 * self.function_status[15] +
                     0b1000 * self.function_status[16] +
                     0b10000 * self.function_status[17] +
                     0b100000 * self.function_status[18] +
                     0b1000000 * self.function_status[19] +
                     0b10000000 * self.function_status[20]
                     )
        elif function <= 28:
            byte1 = 5
            byte2 = (0b0001 * self.function_status[21] +
                     0b0010 * self.function_status[22] +
                     0b0100 * self.function_status[23] +
                     0b1000 * self.function_status[24] +
                     0b10000 * self.function_status[25] +
                     0b100000 * self.function_status[26] +
                     0b1000000 * self.function_status[27] +
                     0b10000000 * self.function_status[28]
                     )
        # Do not support above 28 using DFUN - would need to use DFNON / DFNOF instead
        else:
            print ("Functions above 28 are not supported")
            return None
        #print (f"Returning {byte1}, {byte2}")
        return [byte1, byte2]


    def get_acquire_status (self):
        # returns tuple with session_id, speeddir, functions
        return (self.session, self.get_speeddir(), self.get_function_bytes())

    # Gets loco status in a dict that can be returned via API 
    def get_status_dict (self):
        return {
            'loco_id': self.loco_id,
            'loco_ref': self.loco_ref,
            'session': self.session,
            #'speeddir': self.get_speeddir(),
            'speed': self.speed,
            'direction': self.direction,
            'e_stop': self.e_stop,
            'function_bytes': self.get_function_bytes()
        }
    
    # Return the loco data which is already a dict
    def to_dict (self):
        return self.loco_data
    
    
    # Use this to normally create the class
    @classmethod
    def from_file (cls, loco_ref, loco_file):
        # or we could no):
        # create a initial entry
        new_loco = cls()
        new_loco.load_file (loco_ref, loco_file)
        return new_loco
    
    def __str__(self):
        return (f"Loco {self.get_display_name()}")