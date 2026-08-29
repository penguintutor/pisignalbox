""" Provides a command queue for flask to mainthread (usb / hardware)
"""
import threading
import queue

# The Command Queue (Flask -> Hardware)
# queue.Queue is thread-safe by default. No locking required.
command_queue = queue.Queue()

# Shared State (Hardware -> Flask)
sensor_data = []
sensor_data_index = 0 # index number for first entry in array
# eg. if 10 entries removed from start then this will be increased to 10 and
# new entries will be relative to that

# Mutex Lock used to ensure sensor_data and sensor_data_index are always updated together
state_lock = threading.Lock()

def send_data(command):
    """Called by Flask routes to queue a command for the hardware."""
    command_queue.put(command)

def get_data(start=0, last=None):
    """Called by Flask routes to read the current state."""
    # Copy the data in a state_lock so the lock can be released during processing
    with state_lock:
        local_sensor_data_index = sensor_data_index
        local_sensor_data = sensor_data.copy()

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
        sensor_data.append(item)
    
def cleanup_sensor_data(max_entries):
    """ remove superflous entries over max_entries"""
    # We must declare index as global since we are modifying an integer
    global sensor_data_index

    if (len(sensor_data) > max_entries):
        with state_lock:
            num_pop = len(sensor_data) - max_entries
            del sensor_data[0:num_pop]
            sensor_data_index += num_pop