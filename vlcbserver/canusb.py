import serial
import logging

logger = logging.getLogger(__name__)

# Custom Exception class
class DeviceConnectionError(Exception):
    """Raised when the application fails to connect to the hardware device."""
    pass

# Based on CANUSB4 - sends using pyserial
# This just makes calls to pyserial, but by abstracting would mean you could
# replace easier if using a different way to connect to CANBUS
# Needs port (eg. /dev/ttyACM0)
class CanUSB4 ():
    def __init__ (self, port, baud=115200, timeout=0.01):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.max_retry = 30    # How many times to attempt on get_data must be at least as long as frame
        # buffer to hold partial string - allows us to continue if read ends partway through a packet
        self.current_buffer = ''
        # Track if we are in a valid string (ie. ignore any data outside of : ; blocks
        self.data_start = False
        # Wait for this * timeout - so could be 2 seconds before giving up
        self.connect()
        
        
    # Optional arguments override existing
    def connect(self, port=None, baud=None, timeout=None):
        if port != None:
            self.port = port
        if baud != None:
            self.baud = baud
        if timeout != None:
            self.timeout = timeout
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        except serial.SerialException as e:
            # Catch the low-level library error, raise a high-level domain error
            raise DeviceConnectionError(f"Sensor on {self.port} failed to initialize") from e


    # Data can either be string or bytestring
    def send_data(self, data):
        if self.debug:
            print (f"Sending {data}")
        self.ser.write(data.encode())
        
    
    def read_data(self):
        #print (f"Reading data - status {self.ser.is_open}")
        num_bytes = self.ser.in_waiting
        #print (f"Num bytes {num_bytes}")
        # As each data string is read then it is stored into this list
        # Which allows all new packets to be returned
        # First packet is number of entries (or in the case of error negative)
        # If error then always 2 more strings - First general error, next is output from e
        if num_bytes <= 1:
            return [0]
        
        try:
            in_chars = self.ser.read(num_bytes)
        except serial.SerialException:
            pass
        # Unable to communicate with USB
        except TypeError as e:
            # Close if not already
            self.ser.close()
            return [-1, "NotConnect", e]
        # Any other error
        except Exception as e:
            return [-2, "Error", e]
                    
        # Extracted packet parsing logic
        return self._parse_incoming_chars(in_chars)

    def _parse_incoming_chars(self, in_chars):
        """Private helper to handle the character state machine."""
        received_data = [0]
        
        for byte_val in in_chars:
            this_char = chr(byte_val)
            
            # End of packet
            if this_char == ';':
                if not self.current_buffer:
                    continue
                
                self.current_buffer += this_char
                if self.debug:
                    print(f"Read {self.current_buffer}")
                    
                received_data.append(self.current_buffer)
                received_data[0] += 1
                self.current_buffer = ''
                self.data_start = False
                
            # Start of packet
            elif this_char == ':':
                self.data_start = True
                self.current_buffer = ':'
                
            # Inside a data block
            elif self.data_start:
                self.current_buffer += this_char
                
        return received_data
