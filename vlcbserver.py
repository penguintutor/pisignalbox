#!/usr/bin/env python3
from flask import Flask
import threading
import logging
from vlcbserver.canusb import CanUSB4, DeviceConnectionError
from datetime import datetime
import time
import argparse
import logging
import vlcbserver
from vlcbserver import create_app
import vlcbserver.requests
# Uses json5 to allow comments in the config file
import json5
from pathlib import Path

# --- Configuration Paths ---
# Find the directory where this script lives, then append the subdirectory
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "vlcbserver"

# These are the config files - fixed filenames
# Future: could have an option to call a different filename but not
# supported at the moment
DEFAULT_SETTINGS = CONFIG_DIR / "defaults.json"
CUSTOM_SETTINGS = CONFIG_DIR / "server.json"

# Configure logging for the entire application
logging.basicConfig(level=logging.ERROR) 

## Port now stored in the config file
#port = '/dev/ttyACM0'

# NOTE: Currently any errors and the server stops, 
# Consider adding additional error handling

# maximum number of entries to cache in server
# Will exceed this, but this is the trim level
# ie if we exceed max_entries we will trim to this level
# on each event loop
max_entries = 100

def load_settings(default_path, custom_path):
    # Load defaults first
    try:
        with open(default_path, 'r') as f:
            settings = json5.load(f)
    except FileNotFoundError:
        print(f"Critical: '{default_path}' not found. Cannot start without defaults.")
        return {}
    except ValueError as e:
        print(f"Critical: '{default_path}' is not valid JSON5. Error: {e}")
        return {}

    # Check for custom settings and override (using pathlib's .exists())
    if custom_path.exists():
        try:
            with open(custom_path, 'r') as f:
                custom_settings = json5.load(f)
                
            # Merge the dicts, overwriting defaults with custom values
            settings.update(custom_settings)
            
        except ValueError as e:
            print(f"Warning: '{custom_path}' contains invalid JSON5. Ignoring custom overrides. Error: {e}")
            
    return settings

def flaskThread(debug, config):
    tcp_port = config.get("tcp_port")
    host = config.get("hostname")
    print (f"Network address {host}:{tcp_port}")
    if not debug:
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
    app.run(host=host, port=tcp_port, use_reloader=False)
    
# Setup pixel strip and then start the updatePixels loop
def mainThread(debug, config):
    usb_port = config.get("usb_port")
    print (f"USB port: {usb_port}")
    while True:
        # Entire thread is in a loop which allows us to keep trying connection etc.

        # Connect to USB
        usb = CanUSB4(usb_port)
        try:
            usb.connect()
        except DeviceConnectionError as e:
            logging.error (f"Error connecting to {usb_port} - {e}")
            # At the moment stop - perhaps update in future
            break

        # Once connected, hand control over to the processing loop
        _run_connected_loop(usb, debug)


        
def _run_connected_loop(usb, debug):
    while True:
        # First part of loop - clear out any excessive entries
        # do now rather than each time we add something
        if (len(vlcbserver.data) > max_entries):
            num_pop = len(vlcbserver.data) - max_entries
            del vlcbserver.data[0:num_pop]
            vlcbserver.data_index += num_pop
        #print (f"Len data post {len(data)} index {data_index}")
            
        
        ### Check to see if we have any outgoing messages
        # prioritise sending
        while (len(vlcbserver.messages) > 0):
            this_message = vlcbserver.messages.pop(0)
            usb.send_data(this_message)
            # Add it to the data
            vlcbserver.data.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ",o," + this_message)
            
        # in_data is a list of data
        # first entry [0] is the number entries - if negative then error
        in_data = usb.read_data()
        _process_inbound_data(in_data, debug)


def _maintain_buffer_limits():
    """Prunes the server data logs if they exceed max_entries."""
    if len(vlcbserver.data) > max_entries:
        num_pop = len(vlcbserver.data) - max_entries
        del vlcbserver.data[0:num_pop]
        vlcbserver.data_index += num_pop


def _send_outgoing_messages(usb):
    """Flushes the outgoing message queue to the USB device."""
    while len(vlcbserver.messages) > 0:
        this_message = vlcbserver.messages.pop(0)
        usb.send_data(this_message)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        vlcbserver.data.append(f"{timestamp},o,{this_message}")


def _process_inbound_data(in_data, debug):
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
        vlcbserver.data.append(f"{timestamp},i,{this_input}")
        logging.debug(f"Received {this_input}")
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VLCB Server')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # Load the settings - using default filenames
    # could update to use commandline filenames in future if required
    config = load_settings(DEFAULT_SETTINGS, CUSTOM_SETTINGS)

    app = create_app()
    # Add the config to app.config so it's available to routes.py
    app.config.update(config)

    # run as two threads - main thread and flask thread
    mt = threading.Thread(target=mainThread, args=(args.debug, config))
    ft = threading.Thread(target=flaskThread, args=(args.debug, config))
    mt.start()
    ft.start()
