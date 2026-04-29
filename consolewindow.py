import os
from PySide6.QtCore import Qt, QTimer, QCoreApplication, Signal
from PySide6.QtWidgets import QMainWindow, QTextBrowser, QTableWidget, QTableWidgetItem
from PySide6.QtUiTools import QUiLoader
from eventbus import EventBus, event_bus
from pyvlcb import VLCB
from pyvlcb import VLCBOpcode
import queue
import console_ui_vlcb as ui_vlcb
import console_ui_automation as ui_auto

loader = QUiLoader()
basedir = os.path.dirname(__file__)


class ConsoleWindowUI(QMainWindow):
    
    def __init__(self, mainwindow):
        super().__init__()
        self.debug = False
        self.mainwindow = mainwindow
        
        self.window_title = "PiSignalbox Console"
        
        self.vlcb = VLCB()
        
        # Holds new entries as they are added
        # the UI will then update and remove them
        self.new_entries = []
        self.new_auto_entries = []
        
        # Monitor event bus for app updates
        event_bus.app_event_signal.connect (self.app_update)
        event_bus.log_event_signal.connect (self.log_update)
        
        # Each entry represents a row on the table
        # Each row is a list of the individual entries
        self.console_entries = []
        
        self.ui = loader.load(os.path.join(basedir, "console.ui"), None)
        self.setWindowTitle(self.window_title)
        
        # Set column width for first column to ensure data fits
        #self.ui.consoleTable.setColumnWidth(0, 150)
        #self.ui.consoleTable.setColumnWidth(2, 200)
        
        # File Menu
        self.ui.actionClose.triggered.connect(self.close_window)
        
        # Command shortcuts
        self.ui.commandSelect.currentIndexChanged.connect (self.command_changed)
        self.ui.scrollCheckBox.toggled.connect (self.scroll_checkbox)
        self.ui.sendCommandButton.clicked.connect (self.send_command)
        self.ui.makeCommandButton.clicked.connect (self.make_command)
        self.ui.arg1Select.currentIndexChanged.connect (self.arg1_changed)
        
        self.setCentralWidget(self.ui)

        ui_vlcb.setup_ui(self)
        ui_auto.setup_ui(self)
        
        # Run command changed to setup command combobox
        self.command_changed()
        
    def app_update (self, app_event):
        #print (f"App Event {app_event.data}")
        if app_event.action == "newdata":
            ui_vlcb.add_log(self, app_event.get_response())
            ui_vlcb.update_log(self)
        if app_event.action == "showconsole":
            self.show()
            self.showNormal()
            self.raise_()
            self.activateWindow()
        
    def log_update (self, log_event):
        print (f"Log Event {log_event.data}")
        if log_event.get_log_type() == "Automation":
            ui_auto.add_log(self, log_event)
            ui_auto.update_log(self)
        #Todo other logs could be handled if desired
            
    # Uses main window to send the contents of commandEdit
    def send_command (self):
        # If no string then ignore
        command_string = self.ui.commandEdit.text()
        if command_string == "":
            return
        self.mainwindow.api.start_request(command_string)
        
    # Close actually hides so we can continue to capture logs
    def close_window(self):
        self.hide()



    # Connectors to the ui files
    def command_changed(self):
        ui_vlcb.command_changed(self)

    def scroll_checkbox(self):
        ui_vlcb.scroll_checkbox(self)

    def arg1_changed(self):
        ui_vlcb.arg1_changed(self)

    def make_command(self):
        ui_vlcb.make_command(self)

