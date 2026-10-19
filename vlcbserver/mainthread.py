import logging
import queue
import time
from datetime import datetime
from vlcbserver.vlcb_bridge import command_queue, add_sensor_update, cleanup_sensor_data
from vlcbserver.railway.loco.locomanager import loco_manager
from vlcbserver.extensions import vlcb

KALIVE_INTERVAL = 4.0   # seconds

        
def run_connected_loop(usb, config):
    # initialize the timer before starting
    last_kalive = time.monotonic()

    while True:
        # First part of loop - clear out any excessive entries
        cleanup_sensor_data(config.get("max_entries"))

        # Check if 4 seconds have elapsed since last keep-alive
        now = time.monotonic()
        if now - last_kalive >= KALIVE_INTERVAL:
            # keep alive sends directly to usb
            send_kalive(usb)
            last_kalive = now

        ### Check to see if we have any outgoing messages
        # prioritise sending - so gather all commands
        while True:
            try:
                # Read from message queue for any requests from flask
                # get_nowait() pulls a command if one exists, otherwise throws queue.Empty
                command_dict = command_queue.get_nowait()
                
            except queue.Empty:
                # No commands from Flask - break out of loop
                break

            # Send the command to the usb
            if "vlcb" in command_dict:
                command = command_dict.get("vlcb")
                #print(f"[Hardware] Sending command to layout: {command}")
                # Send it to the serial port
                usb.send_data(command)
                # Also add it to the data - so run_connected_loopother clients can also see it
                add_sensor_update(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ",o," + command)

            # If there a dev_type then pass the data to the appropriate handler
            # so they can update their status
            # Eg. so we can track the status of acquired locos
            if "dev_type" in command_dict:
                match command_dict["dev_type"]:
                    case 'loco':
                        _update_loco_status(command_dict)

            
            
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
    # store raw data into sensor_update
    # See vlcb_bridge for updating loco_manager etc.
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for this_input in in_data[1:]:
        add_sensor_update(f"{timestamp},i,{this_input}")
        logging.debug(f"Received {this_input}")

def _update_loco_status(command_dict):
    """ Update loco status - on an outbound request to usb """
    if "action" in command_dict:
        match command_dict["action"]:
            case "acquire":
                # Inform the loco_manager
                loco_manager.acquire_sent(command_dict["loco_id"], command_dict["loco_ref"])
            case "acquire_basic":
                loco_manager.acquire_sent_basic(command_dict["loco_id"])
            case "stop_all":
                loco_manager.stop_all()


# Send a kalive packet for all active locos    
def send_kalive(usb):

    for session in loco_manager.get_active_sessions_mainthread():
        command = vlcb.keep_alive(session)
        usb.send_data(command) 

        # Also add it to the data - so other clients can also see it
        add_sensor_update(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ",o," + command)