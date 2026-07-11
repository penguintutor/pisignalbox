#!/usr/bin/env python3
import sys, os
# Supress debug messages from qt6ct
os.environ["QT_LOGGING_RULES"] = "*.debug=false;"
import argparse
import logging
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from core import DATA_DIR, RESOURCES_DIR
from mainui import MainWindowUI
from loco import LocoWindow
from loco import LocoDialog

os.environ["QT_QPA_PLATFORM"] = "xcb"

# Configure logging for the entire application
logging.basicConfig(level=logging.ERROR) 
# Change to logging.INFO to turn off all debug prints globally
# To enable detailed logging for apihandler then use below
# logging.getLogger('core.apihandler').setLevel(logging.DEBUG)

# filenames are relative to data directory
# by default that is basedir/data/
dirs = {
    'locos': 'locos/',
    'layouts': 'layouts/',
    'rules': 'rules/',
    'automation': 'automation/'
    }


files = {
    'settings': 'settings.json',
    'locos': 'locos.json',
    'rules': 'rules.json',
    'layouts': 'layouts.json'
    }

# Allows settings to be sent through arguments
settings = {}

# Any ui / css files are considered non user configurable and are hardcoded
class App(QApplication):
    def __init__ (self, args):
        super().__init__()
        
## Handle arguments
parser = argparse.ArgumentParser(
    description = "Model railway controller application for CBUS / VLCB"
    )

# override data directory
parser.add_argument (
    '-d', '--data_dir',		# short or long option
    type=str, 				# must be string
    default=None,			# Defaults to none
    metavar="<dirname>",	# usage message
    help="The directory with the data files."
    )

# Enable mock mode
# Used for testing GUI without a live server
parser.add_argument(
    '-m', '--mock',         # short or long option
    action='store_true',    # This makes it a boolean flag (True if present, False if not)
    help="Use mock client code instead of communicating with a real server."
    )

args = parser.parse_args()
data_dir = args.data_dir
if data_dir:
    override_path = Path(args.data_dir).resolve()
    
    # Keeping your defensive check: only override if the directory actually exists
    if override_path.is_dir():
        # Update the global path in the imported module!
        DATA_DIR = override_path
        print(f"Data directory overridden to: {DATA_DIR}")
    else:
        # Fall back gracefully to the default we established in paths.py
        print(f"Warning: Directory '{override_path}' does not exist.")
        print(f"Falling back to default: {DATA_DIR}")

# Handle Mock Mode
if args.mock:
    print("starting in MOCK mode...")
    settings['mock_mode'] = True
else:
    settings['mock_mode'] = False
        
# Windows with dialogs are ones that may lose focus to their dialogs
# Add to this list to ensure their dialogs are kept on top
# These can be mainwindows (such as LocoWindow) or dialogs with subdialogs (eg. AddLocoDialog)
windows_with_dialogs = (LocoWindow, LocoDialog)
# Dialogs that need to get raised
dialog_types = (QDialog, QFileDialog, QMessageBox)
    
# We can connect to the QApplication's focusChanged signal
# This allows us to handle focus changes across the entire app
def handle_focus_change(old_focus, new_focus):
    # Check if the newly focused widget belongs to a LocoWindow
    if new_focus and isinstance(new_focus.window(), windows_with_dialogs):
        #print (f"New focus {new_focus.window()}")
        # Find the active application-modal dialog
        for widget in QApplication.topLevelWidgets():
            # Check if the widget is a QDialog and is visible
            if isinstance(widget, dialog_types) and widget.isVisible():
                #print (f"Widget is {widget}")
                # Check for ApplicationModal modality
                if widget.windowModality() == Qt.ApplicationModal:
                    # Manually raise the dialog to the front
                    widget.raise_()
                    widget.activateWindow()
                    # The first dialog window is the last opened
                    # after raising that stop
                    break 
        

import faulthandler
faulthandler.enable()

# Create QApplication instance
# Already handled arguments so pass None
app = App(None)

app.setStyle('Fusion')

new_font = QFont("Sans Serif", 10) 
app.setFont(new_font)

# Load and apply QSS file
try:
    with open(RESOURCES_DIR / "style.qss", "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)
except FileNotFoundError:
    print("Stylesheet file not found.")
except Exception as e:
    print (f"Error stylesheet not loaded {e}")

# Monitor for focus change
app.focusChanged.connect(handle_focus_change)

# Create a Qt widget - main window
window = MainWindowUI(dirs, files, settings)

#Start event loop
app.exec()

# Application end


