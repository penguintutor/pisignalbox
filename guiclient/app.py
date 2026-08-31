#!/usr/bin/env python3
import sys
import os
import argparse
import logging
import time
from pathlib import Path
import faulthandler

# Supress debug messages from qt6ct and set platform
# (Keep these outside main() so they apply before Qt initializes)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;"
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import 'core' directly to allow mutating its global state
import core 
from core import RESOURCES_DIR 
from mainui.mainwindow import MainWindowUI
from loco.locowindow import LocoWindow
from loco.locodialog import LocoDialog

# --- Globals & Constants ---

# filenames are relative to data directory
# by default that is basedir/data/
dirs = {
    'locos': 'locos/',
    'layouts': 'layouts/',
    'rules': 'rules/',
    'automation': 'automation/'
    }


files = {
    'defaults': 'default-settings.json',
    'settings': 'settings.json',
    'locos': 'locos.json',
    'rules': 'rules.json',
    'layouts': 'layouts.json'
    }

# Windows with dialogs are ones that may lose focus to their dialogs
# Add to this list to ensure their dialogs are kept on top
# These can be mainwindows (such as LocoWindow) or dialogs with subdialogs (eg. AddLocoDialog)
windows_with_dialogs = (LocoWindow, LocoDialog)
# Dialogs that need to get raised
dialog_types = (QDialog, QFileDialog, QMessageBox)

# --- Classes & Handlers ---
class App(QApplication):
    def __init__(self, args):
        super().__init__()
        
def handle_focus_change(old_focus, new_focus):
    if new_focus and isinstance(new_focus.window(), windows_with_dialogs):
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, dialog_types) and widget.isVisible():
                if widget.windowModality() == Qt.ApplicationModal:
                    widget.raise_()
                    widget.activateWindow()
                    break

        
    
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
        

# --- Main Execution ---
def main():
    # Configure logging for the entire application
    logging.basicConfig(level=logging.ERROR) 
    # Change to logging.INFO to turn off all debug prints globally
    # To enable detailed logging for apihandler then use below
    #logging.getLogger('core.apihandler').setLevel(logging.DEBUG)
    # Or even more detailed logging from the vlcbclient
    #logging.getLogger('core.vlcbclient').setLevel(logging.DEBUG)

    faulthandler.enable()

    # Handle arguments
    parser = argparse.ArgumentParser(
        description="Model railway controller application for CBUS / VLCB"
    )
    parser.add_argument('-d', '--data_dir', type=str, default=None, metavar="<dirname>",
                        help="The directory with the data files.")
    # Enable mock mode
    # Used for testing GUI without a live server
    parser.add_argument('-m', '--mock', action='store_true', 
                        help="Use mock client code instead of communicating with a real server.")
    
    args = parser.parse_args()
    
    # Initialize settings inside main so they stay scoped
    settings = {}

    if args.data_dir:
        override_path = Path(args.data_dir).resolve()
        if override_path.is_dir():
            # Mutate the actual module variable so MainWindowUI sees it
            core.DATA_DIR = override_path
            print(f"Data directory overridden to: {core.DATA_DIR}")
        else:
            print(f"Warning: Directory '{override_path}' does not exist.")
            print(f"Falling back to default: {core.DATA_DIR}")

    if args.mock:
        print("starting in MOCK mode...")
        settings['mock_mode'] = True
    else:
        settings['mock_mode'] = False

    # Create QApplication instance
    app = App(None)

    # Styling and Fonts
    app.setStyle('Fusion')
    new_font = QFont("Sans Serif", 10) 
    app.setFont(new_font)

    try:
        with open(RESOURCES_DIR / "style.qss", "r") as f:
            _style = f.read()
            app.setStyleSheet(_style)
    except FileNotFoundError:
        print("Stylesheet file not found.")
    except Exception as e:
        print(f"Error stylesheet not loaded {e}")

    # Monitor for focus change
    app.focusChanged.connect(handle_focus_change)

    # Create main window
    window = MainWindowUI(dirs, files, settings)

    # Start event loop and gracefully exit
    sys.exit(app.exec())

# --- Entry Point ---
if __name__ == '__main__':
    main()

