import logging
import queue
import time
from datetime import datetime
from vlcbserver.vlcb_bridge import command_queue, add_sensor_update, cleanup_sensor_data, sensor_data


        
def run_connected_loop(usb, config):
    while True:
        # First part of loop - clear out any excessive entries
        cleanup_sensor_data(config.get("max_entries"))

        ### Check to see if we have any outgoing messages
        # prioritise sending - so gather all commands
        while True:
            try:
                # Read from message queue for any requests from flask
                # get_nowait() pulls a command if one exists, otherwise throws queue.Empty
                command = command_queue.get_nowait()
                #print(f"[Hardware] Sending command to layout: {command}")
                # Send it to the serial port
                usb.send_data(command)
                # Also add it to the data - so other clients can also see it
                add_sensor_update(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ",o," + command)
                
            except queue.Empty:
                # No commands from Flask - break out of loop
                break
            
            
        # in_data is a list of data
        # first entry [0] is the number entries - if negative then error
        in_data = usb.read_data()
        _process_inbound_data(in_data)


def _send_outgoing_messages(usb):
    """Sends the outgoing message queue to the USB device.
    Keeps sending whilst there are messages to send
    - sending is higher priority than receiving """
    
    while True:
        try:
            # Attempt to grab a message without waiting
            cmd = command_queue.get_nowait()  
            
            # Process the message here
            usb.send_data(cmd)
                    
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            add_sensor_update(f"{timestamp},o,{cmd}")
            
        except queue.Empty:
            # If no messages waiting then return
            return



def _process_inbound_data(in_data):
    """Evaluates and processes the result of a USB buffer read."""
    # Handle empty or error states
    if in_data[0] == 0:
        time.sleep(0.1)
        return
    elif in_data[0] < 1:
        print(f"Error {in_data[1]}, {in_data[2]}")
        return

    # Data integrity check
    if len(in_data) - 1 != in_data[0]:
        print(f"Warning incorrect data returned, expected {in_data[0]}, received {len(in_data) - 1}")

    # Process packet collection
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for this_input in in_data[1:]:
        add_sensor_update(f"{timestamp},i,{this_input}")
        logging.debug(f"Received {this_input}")
            
