""" Provides a command queue for flask to mainthread (usb / hardware)
Packets sent to the queue are read by run_connected_loop
"""
import threading
import queue
import logging
from vlcbserver.extensions import vlcb
from vlcbserver.railway.loco.locomanager import loco_manager
from pyvlcb import VLCB, VLCBOpcode

# Do we keep a local state of locos devices etc.
# If just using GUI then this is not required and will improve
# performance avoiding need to update local settings
# If using web app (normally the case) then this is required
LOCAL_STATE = True

logger = logging.getLogger(__name__)

# The Command Queue (Flask -> Hardware)
# queue.Queue is thread-safe by default. No locking required.
# pass a dict to the command_queue - the actual payload for vlcb
# should be in {"vlcb": "xxxxxx"}
command_queue = queue.Queue()

# Shared State (Hardware -> Flask)
# Renamed to prefix with a _
# Although these are still shared to protect against threaded writes 
# they should only be updated using the helper functions
_sensor_data = []
_sensor_data_index = 0 # index number for first entry in array
# eg. if 10 entries removed from start then this will be increased to 10 and
# new entries will be relative to that

# Mutex Lock used to ensure sensor_data and sensor_data_index are always updated together
state_lock = threading.Lock()

# Send data sends the packet - doesn't check it's a valid request
# which should be handled by calling - eg. check loco aquired
# before sending requests to it
# This provides a way to pass it to the the mainthread
def send_data(command: dict | str):
    """Called by Flask routes to queue a command for the hardware.
    Can handle a single string command, or a dict
    Allows to update other objects / status from flask
    The actual vlcb / cbus packet is in a dict['vlcb']
    """
    if isinstance(command, dict):
        command_queue.put(command)
    elif isinstance(command, str):
        command_queue.put({"vlcb": command})
    else:
        raise TypeError(f"Expected dict or str, got {type(command).__name__}")

def get_data(start=0, last=None):
    """Called by Flask routes to read the current state."""
    # Copy the data in a state_lock so the lock can be released during processing
    with state_lock:
        local_sensor_data_index = _sensor_data_index
        local_sensor_data = _sensor_data.copy()

    # if start is higher than last then return error
    data_last = local_sensor_data_index + len(local_sensor_data)
    if start > data_last:
        return ["Read,0,0,-1"]
    # if start is 1 more than last entry then that would be the next
    if start == data_last + 1:
        return ["Read,0,0,0"]
    # if start is negative then it's relative from end
    if start < 0:
        start = data_last + start # Add as start is negative this is from end
    # Now check for within range
    if start < local_sensor_data_index:
        start = local_sensor_data_index
    if last == None or last > data_last:
        last = data_last
    # If no data return null status
    if last <= start:
        return ["Read,0,0,0"]
    # Reach here there should be some data we can send
    return_data = [f"Read,{start},{last-1},{last-start}"]
    for i in range (start, last):
        return_data.append(f"{i},{local_sensor_data[i-local_sensor_data_index]}")
    return return_data


def add_sensor_update(item):
    """Called by the main hardware thread to update state."""
    with state_lock:
        _sensor_data.append(item)
    # If applicable update local state
    if LOCAL_STATE:
        _update_local_state(item)
    
def cleanup_sensor_data(max_entries):
    """ remove superflous entries over max_entries"""
    # We must declare index as global since we are modifying an integer
    global _sensor_data_index

    if (len(_sensor_data) > max_entries):
        with state_lock:
            num_pop = len(_sensor_data) - max_entries
            del _sensor_data[0:num_pop]
            _sensor_data_index += num_pop

# Called whenever a packet is seen - 
# Use to update local state used by web app
def _update_local_state(item):
    # split into timestamp, vlcb_entry (unlike gui no id)
    try:
        date_data = item.split(',',2)
        vlcb_entry = vlcb.parse_input(date_data[2])

        ret_opcode = vlcb_entry.opcode() 
    except Exception as e:
        logger.warning (f"Invalid VLCB packet {item} - {e}")
        return


    # Look for op-codes which indicate a state change
    # If a responding action is required then 
    # response should be provided a dict which can be sent to send_data
    response = None
    match ret_opcode:
        # Allocation of loco 
        case 'PLOC':
            data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
            # Session,AddrHigh_AddrLow,SpeedDir,Fn1,Fn2,Fn3'
            loco_id = data_entry['AddrHigh_AddrLow'] & 0x3FFF
            # These are the data values returned:
            """ Eg data_values = {
                'Loco_id': loco_id,
                'Session': data_entry['Session'],
                'Speeddir': data_entry['SpeedDir'],
                'Fn1': data_entry['Fn1'],
                'Fn2': data_entry['Fn2'],
                'Fn3': data_entry['Fn3'],
                'Status': "on"
                }
                """
            functions = [data_entry['Fn1'], data_entry['Fn2'], data_entry['Fn3']]
            loco_manager.acquire_confirm(loco_id, data_entry['Session'], data_entry['SpeedDir'], functions)
        # Loco Error - eg. loco taken
        # Pass on to loco_manager and let that deal with 
        case 'ERR':
            data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
            response = loco_manager.handle_error(data_entry)
        # Emergency Stop
        case ' RESTP': 
            loco_manager.emergency_stop_received()
        # Speed/Dir
        case 'DSPD':
            # Update any locos matching session with the speeddir seen on CBUS
            data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
            loco_manager.update_session_speeddir(data_entry.get("Session"), data_entry.get('SpeedDir'))

    # Check to see if there was a response from a handler
    # If so then that needs to be sent back to the queue
    if response:
        #print (f"vlcb_bridge - response from error handler {response}")
        send_data(response)


    # Uncomment for the raw data received from USB - very noisy!
    #print (f"vlcb_bridge: VLCB Entry {vlcb_entry}, op_code {ret_opcode}")