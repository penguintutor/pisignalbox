#!/usr/bin/env python3
import os, sys
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
from vlcbserver.vlcb_bridge import command_queue, add_sensor_update, cleanup_sensor_data, sensor_data
# Uses json5 to allow comments in the config file
import json5
from pathlib import Path
import queue


# --- Configuration Paths ---
# These are in caps as constants, but some can be overwritten
# by command line options or environment settings
# Find the directory where this script lives, then append the subdirectory
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "vlcbserver"

# These are the config files - fixed filenames
# Future: could have an option to call a different filename but not
# supported at the moment
DEFAULT_SETTINGS = CONFIG_DIR / "defaults.json"
CUSTOM_SETTINGS = CONFIG_DIR / "server.json"

# Database is in the instances directory - holds user details etc.
INSTANCE_DIR = BASE_DIR / 'instances'
DATABASE_PATH = INSTANCE_DIR / 'users.db'

# String for setup command - used to inform user how to add user
SETUP_CMD = "setup/setup_auth.py"

# Future: Consider overriding using config file or environment variables
LOGLEVEL_CONSOLE = logging.WARNING
LOGLEVEL_FILE = logging.INFO

LOG_DIR = BASE_DIR / 'logs'
LOG_PATH = LOG_DIR / 'vlcbserver.log'

# Configure logging for the entire application
#logging.basicConfig(level=logging.ERROR) 
# Compromise warning 
#logging.basicConfig(level=logging.WARNING) 
# Add debugging at INFO and above
# logging.basicConfig(level=logging.INFO) 

## Port now stored in the config file
#port = '/dev/ttyACM0'

# NOTE: Currently any errors and the server stops, 
# Consider adding additional error handling

# maximum number of entries to cache in server
# Will exceed this, but this is the trim level
# ie if we exceed max_entries we will trim to this level
# on each event loop
# max_entries = 100
# This entry is now in the defaults.json



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
            logging.exception (f"Error connecting to {usb_port} - {e}")
            # At the moment stop - perhaps update in future
            break

        # Once connected, hand control over to the processing loop
        _run_connected_loop(usb, config)


        
def _run_connected_loop(usb, config):
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
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VLCB Server')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # LOG_PATH can be overwridden by environment setting 
    env_log_dir = os.environ.get('APP_LOG_DIR', None)
    if env_log_dir:
        LOG_PATH = Path(env_log_dir) / 'vlcbserver.log'

    # Load the settings - using default filenames
    # could update to use commandline filenames in future if required
    config = load_settings(DEFAULT_SETTINGS, CUSTOM_SETTINGS)

    # Add paths to config if required elsewhere
    config.update({
        # Flask-SQLAlchemy expects a URI string. Uses an f-string to inject the Path.
        'SQLALCHEMY_DATABASE_URI': f"sqlite:///{DATABASE_PATH}",
        # Disabling this saves memory and suppresses a warning
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        # Log details
        'LOG_PATH' : LOG_PATH,
        'LOGLEVEL_CONSOLE': LOGLEVEL_CONSOLE,
        'LOGLEVEL_FILE': LOGLEVEL_FILE

    })

    # Check the database exists
    # Doesn't check a user - that comes later in the create_app
    if not DATABASE_PATH.exists():
        print("ERROR: The database file does not exist.")
        print(f"Please run the setup step {SETUP_CMD} before starting the app.")
        sys.exit(1) # Halt application startup

    # Create the log dir if not already exist - and it's local (not overridden with /var/log etc.)
    if LOG_DIR == BASE_DIR / 'logs':
        LOG_DIR.mkdir(exist_ok=True)


    app = create_app(config)

    # run as two threads - main thread and flask thread
    # Set daemon=True. This tells Python: "If the main script exits, 
    # instantly kill these threads. Do not wait for them.
    # If one stops then there is no point in the other continuing
    mt = threading.Thread(target=mainThread, args=(args.debug, config), daemon=True)
    ft = threading.Thread(target=flaskThread, args=(args.debug, config), daemon=True)
    mt.start()
    ft.start()

    # Add a monitor loop, so that if either thread stops it errors and quits
    try:
        while True:
            # Check if the hardware thread died
            if not mt.is_alive():
                sys.exit("\nCRITICAL ERROR: The VLCB hardware mainThread stopped unexpectedly. Shutting down the entire server.")
            
            # Check if the Flask thread died
            if not ft.is_alive():
                sys.exit("\nCRITICAL ERROR: The Flask web thread stopped unexpectedly. Shutting down the entire server.")
            
            # Sleep for 1 second so this while loop doesn't consume 100% of your CPU
            time.sleep(1)
            
    except KeyboardInterrupt:
        # Graceful manual exit
        # If you press Ctrl+C in the terminal, it breaks the loop cleanly
        print("\nCtrl+C detected. Shutting down VLCB Server...")
        sys.exit(0)
