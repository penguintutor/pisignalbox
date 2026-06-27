# PiSignalbox - Windows and dialog
Guide to which classes are responsible for 
app.py - Opens MainWindow
## MainWindow
MainWindow Class - creates the main window - Launched from app.py

ui_layout - handles layout operations within mainwindow - includes ui wrappers for layoutview
ui_loco - creates and handles interaction with the Control and Locos panel tabs
ui_devices - creates and handles interaction with the Nodes panel tab
ui_automate - creates and handles interaction with the Automation panel tab

Launches the following dialogs

- AutomationManagerDialog - Manage automation sequences - triggered from actionAutomationMgr (mainwindow.ui) - AutomationRuleManager
- AddDeviceDialog - Add new devices (in layout)- triggered from actionAddDevice (mainwindow.ui)
- AddLabelDialog - Add new label (in layout) - triggered from actionAddLabel (mainwindow.ui)
- AddButtonDialog - Add new button (in layout) - triggered from actionAddButton (mainwindow.ui)

Indirect dialogs
- import_file - QFileDialog - Open Import file - triggered from actionImportLoco (mainwindow.ui)


### ui_automate

Launches the following dialogs (part of MainWindow)

- AutoLocoDialog



### ui_devices
- Calls dialogs from ui_layout - eg. edit_dialog_trackviewnode, edit_dialog_layoutbutton, edit_dialog_layoutlabel()


### ui_layout

Launches the following dialogs (part of MainWindow)

- ImageExistDialog
- edit_dialog_layoutbutton - Add / edit layout buttons - called from MainWindow (menu) or ui_devices (editgbuttondialog.ui)
- edit_dialog_trackviewnode - Add / edit layout device - called from MainWindow (menu) or ui_devices (editguidialog.ui)
- edit_dialog_layoutlabel - Add / edit layout labels - called from MainWindow (menu) or ui_devices (editglabeldialog.ui)


Indirect dialogs 
- file_dialog - 



### ui_loco.py

Launches the following dialogs (part of MainWindow)

- StealDialog - Option to steal / share a loco - Triggered by event where ui_loco failed to acquire a loco


## AutomationManagerDialog

AutomationManagerDialog - launched from MainWindow

Launches the following dialogs

- AutomationSeqDialog - Automation Sequence Dialog - Called for both Add and Edit Sequence


## AutomationSeqDialog

AutomationSeqDialog - launched from AutomationManagerDialog

Titled Automation Sequence

Launches the following dialogs

- AutomationStepDialog - Called for both create or edit an automation step


## AutomationStepDialog

AutomationStepDialog - launched from AutomationSeqDialog

Titled Configure Rule
