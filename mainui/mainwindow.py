import os
import shutil
import time
from PySide6.QtCore import QTimer, QCoreApplication, Signal, QThreadPool, Qt, QPoint, QSize
from PySide6.QtWidgets import QApplication, QMainWindow, QAbstractItemView, QMenu, QLineEdit, QDialog, QColorDialog, QFileDialog, QMessageBox, QHeaderView
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QFont, QResizeEvent
from PySide6.QtUiTools import QUiLoader
from pathlib import Path
#import core.paths as app_paths
from core import DATA_DIR, RESOURCES_DIR
from core import event_bus
from trackview import track_view_manager
from loco import loco_manager
from settings import Settings
from console.consolewindow import ConsoleWindowUI
from eventdialog import EventDialog
#rom layout import Layout, LayoutDisplay
from layout import Layout
from trackview import TrackViewDisplay
from loco import ControlLoco
from core import ApiHandler
from events import AppEvent
from loco import LocoWindow, StealDialog
from rules import RulesWindow
#from device.vlcbnode import VLCBNode
#from device.vlcbev import VLCBEv
from device import device_manager
from imageexistdialog import ImageExistDialog
from automate import AutomationManager, AutomationManagerDialog
from core import global_app_vars
#from core.appvar import AppVar
# UI code is split into Mixin classes so they can be placed in their own
# package but access the MainWindow as though native to MainWindow
from trackview import UITrackViewMixin, AddDeviceDialog, AddLabelDialog, AddButtonDialog
from loco import UILocoMixin
from automate import UIAutomateMixin
from .systemexplorer import SystemExplorer

# Setup file paths
basedir = os.path.dirname(__file__)

app_title = "Pi SignalBox"

url = "http://127.0.0.1:5000/"
#os.path.join(basedir, "data/")
read_rate = 200

class MainWindowUI(QMainWindow, UITrackViewMixin, UILocoMixin, UIAutomateMixin):
    
    steal_dialog_signal = Signal(int)
    # Handle loco selection
    # reset loco to none selected (if acquire failed or loco stolen by another controller)
    reset_loco_signal = Signal()
    steal_loco_signal = Signal() # Attempt to steal loco
    share_loco_signal = Signal() # Attempt to share loco
    
    # Keep alive timer must always be started and stopped on the GUI thread
    # this will start or stop as appropriate based on loco state
    update_kalive_signal = Signal()
    
    # If locos updated then refresh selection list
    updated_locos_signal = Signal()
    
    # Monitor for Window Activated to be able to manage the level of windows / dialog
    windowActivated = Signal()
    
    # Whenever settings change - request save
    save_settings_signal = Signal()
    
    var_signal = Signal()
    
    # files_dirs are passed from app - file structure is fixed
    # Are all relative to basedir
    # although some customisation of file names is allowed in configs
    # settings provides an option for command line arguments to the data dir
    def __init__(self, dirs, files, settings=None):
        super().__init__()
        self.debug = False

        # Loader used to load the ui files
        loader = QUiLoader()
        loader.registerCustomWidget(TrackViewDisplay)
        
        # Command line arguments and directory settings
        self.cmd_settings = settings or {}
        self.dirs = {} # dirs need to be updated with data_dir
        self.files = files
        
        # This will hold the QPixmap for the loco image
        self.loco_image = None

        self.stop_automation = False
        
        # All data files are relative to this directory
        # Default this is basedir/data
        # Get from paths
        self.data_dir = DATA_DIR
            
        # Update all the dirs to add data_dir
        for key, value in dirs.items():
            #self.dirs[key] = os.path.join(self.data_dir, value)
            self.dirs[key] = DATA_DIR / value
        
        self.threadpool = QThreadPool()
        self.update_in_progress = False
        
        # Setup API handler
        if 'mock_mode' in self.cmd_settings and self.cmd_settings['mock_mode']:
            #print("Using Mock VLCB Client")
            from tests.mock_vlcbclient import MockVLCBClient
            mock_client = MockVLCBClient()
            self.api = ApiHandler(self.threadpool, url, mock_client)
        else:
            self.api = ApiHandler(self.threadpool, url)

        # Get the QFont object for the default font
        app = QApplication.instance()
        self.default_font = app.font()
        
        # Create a timer to periodically check for updates
        self.timer = QTimer(self)
        self.timer.setInterval(read_rate)
        self.timer.timeout.connect(self.api.poll_server)
        self.timer.start()
        
        # Keep alive timer - used for DCC keep alive
        # Create timer, but don't start until acquire locomotive
        self.kalive_timer = QTimer(self)
        self.kalive_timer.setInterval(4000)
        self.kalive_timer.timeout.connect(self.keep_alive)
        
        # Load the Assets prior to setting up the GUI
        
        # Create App variable class
        # Variables are global across the app, but can prefix with specific automation
        # to avoid conflicts eg. "engshed1_variable1"
        # Note that the actual variables are not stored in the device_model but they do need
        # Added there for lookup by menus etc. but all updates are via the global_app_vars
        # which are then in the AppVar class
        # should be set using the following methods (in mainwindow.appvariables) so that they are also reflected here
        # and can also trigger events.
        # get_variable(variable_name), set_variable(variable_name, new_value), inc_variable(variable_name, inc_amount)
        #self.appvariables = AppVar(self.var_signal)

        

        # Load the settings file here
        self.settings = Settings(self, self.files['settings'])

        current_dir = Path(__file__).resolve().parent
        self.ui = loader.load(current_dir / "mainwindow.ui", None)
        self.setWindowTitle(app_title)
        self.loco_window = None
        self.rules_window = None
        

        self._load_assets ()
        self._initialise_automation ()
        
        # Signals
        self.steal_dialog_signal.connect (self.steal_loco_dialog)
        self.reset_loco_signal.connect (self.reset_loco)
        self.steal_loco_signal.connect (self.steal_loco)
        self.share_loco_signal.connect (self.share_loco)
        self.update_kalive_signal.connect (self.update_kalive)
        # Other event related signals
        self.updated_locos_signal.connect (self.update_loco_list)
        # Gui signal
        event_bus.gui_event_signal.connect(self.gui_event)
        # Listen to device_model signal for treeview updates
        #device_model.add_node_signal.connect (self.add_to_tree)
        # Save setings
        self.save_settings_signal.connect (self.save_settings)
        
        # File Menu
        self.ui.actionChangeLayout.triggered.connect(self.change_layout_dialog)
        # (Import sub menu)
        self.ui.actionImportLoco.triggered.connect(self.import_file)
        self.ui.actionExit.triggered.connect(self.quit_app)
        
        # Asset Menu
        self.ui.actionDiscover.triggered.connect(self.api.discover)
        
        # Tools Menu        
        self.ui.actionLocoManager.triggered.connect(self.loco_manager)
        self.ui.actionRules.triggered.connect(self.rules_edit)
        self.ui.actionAutomationMgr.triggered.connect(self.automation_manager_dialog)
        self.ui.actionShowConsole.triggered.connect(self.show_console)
        self.ui.actionLayoutEdit.triggered.connect(self.layout_edit)
        self.ui.actionSettings.triggered.connect(self.settings_edit)
        
        # EditLayout Menu - only show when in edit layout mode
        #self.ui.menuEditLayout.setVisible(False)
        self.ui.menuEditLayoutAction = self.ui.menuEditLayout.menuAction()
        self.ui.menuEditLayoutAction.setVisible(False)
        self.ui.actionChangeImage.triggered.connect(self.change_layout_image_dialog)
        self.ui.actionAddDevice.triggered.connect(self.add_device_dialog)
        self.ui.actionAddLabel.triggered.connect(self.add_label_dialog)
        self.ui.actionAddButton.triggered.connect(self.add_button_dialog)
        
        # Tree view
        #self.node_model = device_model.node_model
        #self.node_model.setHorizontalHeaderLabels(['Nodes'])
        # Todo this should have been removed with device_manager
        #self.ui.nodeTreeView.setModel(device_model.node_model)
        self.ui.nodeTreeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Tree View buttons moved to system_explorer
        
        # Event buttons
        #self.ui.evButtonOff.clicked.connect(self.system_explorer.ev_clicked_off)
        #self.ui.evButtonOn.clicked.connect(self.system_explorer.ev_clicked_on)
        
        # Last Node / Event that was selected - use for On/Off buttons
        #self.selected_node = None
        # This is now handled within the SystemExplorer
        
        # Update other GUI components
        # Add locos to menu
        self.update_loco_list ()
        # Add locos to table
        # Get the header object
        header = self.ui.locoTable.horizontalHeader()
        # Set Column 0 (Name) to fill all available empty space
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        # Set Column 1 (Button) to shrink exactly to the size of the button
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        # Keep a list of what loco objects relate to which table entry
        self.loco_table_list = []
        self.loco_table_buttons = []
        self.update_loco_table ()
        # Activated is based on user interaction (changing by code doesn't trigger)
        self.ui.locoComboBox.activated.connect(self.loco_change)
        self.ui.locoDial.valueChanged.connect(self.loco_change_speed)
        
        # With direction radio buttons just look for clicks (so can update without triggering)
        self.ui.locoForwardRadio.clicked.connect(self.loco_forward)
        self.ui.locoReverseRadio.clicked.connect(self.loco_reverse)
        self.ui.locoForwardButton.clicked.connect(self.loco_forward)
        self.ui.locoReverseButton.clicked.connect(self.loco_reverse)
        
        self.ui.locoStopButton.clicked.connect(self.loco_stop)
        self.ui.locoStopAllButton.clicked.connect(self.loco_stop_all)
        
        self.ui.locoFuncTab.tabBarClicked.connect(self.loco_change_functions)
        self.ui.locoFuncCombo.activated.connect(self.loco_function_selected)
        self.ui.locoFuncButton.clicked.connect(self.loco_function_pressed)
        
        # Used to generate codes for loco etc.
        self.control_loco = ControlLoco()
        event_bus.app_event_signal.connect(self.app_event)
        # automation_file
        # FUTURE:
        # Need to determine which rules to load - this is default
        event_bus.load_rules(os.path.join(self.dirs['rules'], "default.json"))
        
        # Pass the layout details to LayoutDisplay to allow it to load other resources
        # Also pass self so it can access mainwindow
        # Todo what is this doing? Is it required??
        #self.ui.layoutDisplayLabel.set_layout(self, self.layout)QEs
        self.ui.layoutDisplayLabel.set_layout(self, self.layout)
        # Includes load layout background image
        # and UI objects
        
        # Update LCD - used to set '-' at start
        self.update_lcd()

        
        self.setCentralWidget(self.ui)
        self.ui.nodeTreeView.show()
        self.show()
        self.create_console()

        # Load the system_explorer for showing Nodes (devices & layout objects)
        self.system_explorer = SystemExplorer (self)


        # Status of the http connection
        self.status = "Not connected"
                          
        # Initial discover request
        self.api.discover()


    # Loads and sets up the railway (Layout) and loading locos etc.
    # This needs to be delayed to allow Gui components to be setup frst
    # eg. SystemExplorer
    def _load_assets (self):
        # Load the Current Layout file from settings
        # Layout provides background image and
        # can also be used for giving real names to certain items
        # Needs to come after self.ui is loaded
        # Variable is named railway to avoid potential conflict if named layout
        self.layout = Layout(self, self.dirs['layouts'], self.settings.get_layout_filename())
        # pass the layout to the devicemodel
        #device_model.set_layout(self.layout)
        
         # Load all locos
        full_path_locos = os.path.join(self.data_dir, self.files['locos'])
        loco_manager.load_locos (self.dirs['locos'], full_path_locos)
        
        # Now set enabled locos from settings
        if 'enabledlocos' in self.settings.settings_dict:
            loco_manager.enable_locos (self.settings.settings_dict['enabledlocos'])

    def _initialise_automation (self):
        # Automation Manager class used to load / store the sequences
        self.automation = AutomationManager(self, self.threadpool, self.dirs['automation'], "Default")
        # Load the default automation
        self.automation.load()
        # Add any variables from the sequences to the appvariables
        auto_vars = self.automation.get_variables()
        for var in auto_vars:
            #print (f"Adding variable {var} to AppVar from AutomationManager")
            global_app_vars.add_variable (var, "", False)

        self.automation.global_status.connect(self.update_sequence_status)

        # Add automation list 
        self.update_automation_list()

        self.ui.automationRunButton.clicked.connect(self.run_selected_sequence)

    # TODO: handle sequence status updates
    def update_sequence_status (self, status_message):
        #print (f"Sequence status update: {status_message}") 
        pass

    def gui_event (self, gui_event):
        gui_node = track_view_manager.get_track_view_node_from_name(gui_event.data.get('node'))
        if gui_node != None:
            gui_node.set_state_value(gui_event.data.get('value'))
        self.system_explorer.update_table()

    # Edit events associations between different objects
    def loco_manager (self):
        if self.loco_window == None:
            self.loco_window = LocoWindow(self, self.dirs['locos'])
        self.loco_window.update()
        self.loco_window.display()

    # Edit rules - eg events associations between different objects
    def rules_edit (self):
        if self.rules_window == None:
            self.rules_window = RulesWindow(self)
        self.rules_window.update()
        self.rules_window.display()
        
    # Launch the automation manager dialog
    def automation_manager_dialog (self):
        """ Create and launch Automation Manager dialog
        used to manage the automation sequences

        usually triggered from actionAutomationMgr (mainwindow.ui)
        """
        #print (f"Launching Automation Manager Dialog {self.automation}")
        dialog = AutomationManagerDialog(self, self.automation)
        dialog.exec()
    
    # Edit settings
    def settings_edit (self):
        pass
    
    def save_settings (self):
        self.settings.save_settings()
    
    def get_enabled_locos (self):
        return self.loco_manager.get_enabled_loco_filenames ()
    
    
    def add_device_dialog (self):
        """ Create and launch Add Device dialog
        used to add new devices to the layout

        usually triggered from actionAddDevice (mainwindow.ui)
        """
        dialog = AddDeviceDialog()
        if dialog.exec():
            # the response is in the form id, text
            response = dialog.get_selected_values()
            # The first "text" is that it's a text style label (allows flexibility for future)
            self.layout.add_gui_device(response[0], response[1])
        
        
    def add_label_dialog (self):
        """ Create and launch Add label dialog
        used to add new labels to the layout

        usually triggered from actionAddLabel (mainwindow.ui)
        """
        dialog = AddLabelDialog(self.layout.gui_object_names())
        if dialog.exec():
            # the response is in the form id, text
            response = dialog.get_selected_values()
            #print(f"Selected value: {text}")
            # The first "text" is that it's a text style label (allows flexibility for future)
            self.layout.add_label(response[0], "text", {"text":response[1]})
        
    def add_button_dialog (self):
        """ Create and launch Add Button dialog
        used to add new buttons to the layout

        usually triggered from actionAddButton (mainwindow.ui)
        """
        dialog = AddButtonDialog(self.layout.gui_object_names())
        if dialog.exec():
            # # the response is in the form id, button_type
            response = dialog.get_selected_values()
            self.layout.add_button(response[0], response[1], {})
        
    def event_selection_dialog (self):
        dialog = EventDialog()
        if dialog.exec():
            node, event = dialog.get_selected_values()
            return (node, event)

        
    # App event is used to send events from other parts of the app
    def app_event (self, app_event):
        # If there is a loco_index then only interested in loco 0 (gui controlled loco)
        # If no loco_index then assume it's for us
        # Otherwise event is most likely for automation
        if 'loco_index' in app_event.data and app_event.data['loco_index'] != 0:
            return
        if app_event.action == "uitext":
            if app_event.data['label'] == "locoStatusLabel":
                self.ui.locoStatusLabel.setText (app_event.data['value'])
        elif app_event.action == "lcd":
            self.update_lcd()
        elif app_event.action == "keepalive":
            self.update_kalive_signal.emit()
        # If locotaken then launch steal_dialog
        elif app_event.action == "locotaken":
            # Only action if it is the controlloco that is taken
            loco_id = app_event.get_loco_id()
            if loco_id == None:
                return
            print (f"Loco taken {loco_id}")
            # use try in case we don't have a loco yet
            # eg. if start automation without selecting loco first
            try:
                if loco_id == self.control_loco.get_id():
                    # Set status message - then launch dialog
                    self.ui.locoStatusLabel.setText ('Warning - address taken')
                    self.steal_dialog_signal.emit(loco_id)
            except Exception as e:
                print (f"Acquire fail for a non existing loco {loco_id} - {e}")
                return
        elif app_event.action == "resetloco":
            # Only reset gui parts - already reset in controlloco
            self.reset_loco_gui()
            
    
    # Show console always calls show
    # If window already open then bring to front
    def show_console (self):
        # Send as an app event to decouple
        event_bus.publish(AppEvent({"action":"showconsole"}))
        


    def create_console(self, show=False):
        self.console_window = ConsoleWindowUI(self)
        if show:
            self.console_window.show()    
          
        
    # Send exit to automate as well as closing app
    def quit_app(self):
        QCoreApplication.quit()
        
        
    # check if a filepath is in dir (default to datadir, otherwise specify the dir to compare against)
    def is_datadir(self, filepath, dir=None):
        if dir==None:
            check_dir = os.path.dirname(self.data_dir)
        else:
            check_dir = os.path.dirname(self.dirs[dir])
        try:
            filedir = os.path.dirname(filepath)
            #print (f"Checking {filedir}, {check_dir}")
            return filedir == check_dir
        except Exception as e:
            print(f"Error checking path: {e}")
            return False
        
    # Import clicked on the menu - import assets (eg. loco file)
    def import_file(self, checked=False):
        """ Handles import request
        Launches a QFileDialog and then performs import
        Triggered from menu (mainwindow.ui)
        """
        try:
            file_dialog = QFileDialog(self,
                            caption="Select Loco file",
                            directory=self.dirs['locos'],
                            filter="Data (*.json)",
                            fileMode=QFileDialog.FileMode.ExistingFile
                            )
            file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

            # Get filename
            if file_dialog.exec():
                selected_file = file_dialog.selectedFiles()[0]

                filename = os.path.basename(selected_file)
                # Check it doesn't already exist
                if (loco_manager.check_loco_filename(filename) == True):
                    QMessageBox.warning(
                        self, 
                        "File exists", # The title of the dialog
                        f"Filename {filename} already exists. Please rename the file first." # The message content
                    )
                    return
                
                # Is the file in the locosdir
                if self.is_datadir(selected_file, 'locos'):
                    #print (f"{filename} in data directory")
                    new_path = selected_file
                # if not then copy (note it will overwrite existing, but already established it's not being loaded)
                else:
                    # New path - includes filename
                    new_path = os.path.join(self.dirs['locos'], filename)
                    print (f"Copying {selected_file} to {new_path}")
                    shutil.copyfile (selected_file, new_path)
                    # Todo wrap above in try clause
                    #loco_filename = filename
                
                # Now load and add to the file
                #print (f"Loading file {new_path}")
                loco_manager.import_loco(filename)
                self.loco_manager.save_locos()
                self.updated_locos_signal.emit()
        except Exception as e:
            # This will print the EXACT reason your app is crashing to the terminal
            print(f"CRASH AVERTED! Error in import_file: {e}")
            #traceback.print_exc()

    # Adds a variable to the AppVar class AND to the device_model
    # If variable already exists then returns false
    # event is whether to broadcast
    ### moved to the global_app_vars
    # def add_variable (self, variable_name, value="", event=True):
    #     # Check if variable exists
    #     if global_app_vars.is_variable(variable_name):
    #         return False
    #     global_app_vars.set_variable(variable_name, value, event)
    #     #device_model.add_variable(variable_name)
    #     device_manager.add_variable(variable_name)
    #     return True
    
    # Override reiszeEvent
    def resizeEvent(self, event: QResizeEvent):
        #print ("Resize event called")
        self.scale_image_to_fit()
        super().resizeEvent(event) # Call the base class implementation

    def closeEvent(self, event):
        """ called when the main window is closing """
        print("Closing... stopping threads.")
        
        # Tell threads to stop
        self.stop_automation = True

        #Force close any open "wait for user" dialogs
        self.close_all_windows()

        # Remove any tasks in the queue that haven't started yet
        #self.thread_manager.clear()

        # Wait for active threads to finish their current loop and exit
        # text allows the GUI to freeze slightly while waiting, ensuring no crash.
        print("Waiting for threads to finish...")
        #self.thread_manager.waitForDone(2000) # Wait up to 2 seconds
        time.sleep(2) # Simple sleep to allow threads to finish
        
        print("Threads finished or timed out. Closing.")
        event.accept()
    
    def close_all_windows(self):
        """ Closes all secondary windows except the main window itself. """
        # iterate over every window the app tracks
        for widget in QApplication.topLevelWidgets():
            
            # CRITICAL: Skip 'self' so we don't close the main window immediately
            if widget is self:
                continue
            
            # Optional: Check if the widget is visible before trying to close
            if widget.isVisible():
                print(f"Closing secondary window: {widget}")
                widget.close()


