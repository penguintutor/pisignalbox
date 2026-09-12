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
import vlcbserver.blueprints.web
from vlcbserver.vlcb_bridge import command_queue, add_sensor_update, cleanup_sensor_data, sensor_data
# Uses json5 to allow comments in the config file
import json5
from pathlib import Path
import queue
from vlcbserver.config import Config
from vlcbserver.settings import get_config, load_settings, cfg_checks
from vlcbserver.mainthread import run_connected_loop


# --- Configuration Paths ---
# These are in caps as constants, but some can be overwritten
# by command line options or environment settings
# Find the directory where this script lives, then append the subdirectory

# Constants moved to constants.py / config.py

## NOTE these are duplicated in setup scripts, if updated here
## similar changes may be needed in that script
## Also included in tests

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

def flaskThread(app, debug, config):
    tcp_port = config.get("tcp_port")
    host = config.get("hostname")
    print (f"Network address {host}:{tcp_port}")
    if not debug:
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
    app.run(host=host, port=tcp_port, use_reloader=False)
    
# Run the main thread for reading and writing to usb.
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
        run_connected_loop(usb, config)


def run_server(cfg, config):

    # Perform checks against cfg before server start
    # eg. if no DB then no point in proceeding
    if cfg_checks(cfg) == False:
        sys.exit(1) # Halt application startup

    app = create_app(config)

    logging.info ("*** cfg.Application Start ***")

    # run as two threads - main thread and flask thread
    # Set daemon=True. This tells Python: "If the main script exits, 
    # instantly kill these threads. Do not wait for them.
    # If one stops then there is no point in the other continuing
    mt = threading.Thread(target=mainThread, args=(args.debug, config), daemon=True)
    ft = threading.Thread(target=flaskThread, args=(app, args.debug, config), daemon=True)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VLCB Server')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument("--base-dir", type=Path, default=None, help="Override project base directory")
    # Launch authentication setup
    parser.add_argument('--setup-auth', action='store_true', help='Launch interactive auth setup instead of starting server')
    args = parser.parse_args()

    cfg = Config(base_dir=args.base_dir)

    # Load and setup config using both config consts and settings
    config = get_config(cfg)

    if args.setup_auth:
        from vlcbserver.setup_auth import new_auth
        new_auth(config)
    else:
        run_server(cfg, config)