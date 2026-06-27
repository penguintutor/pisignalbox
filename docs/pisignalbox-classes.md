# PiSignalBox - Classes and files

## app.py

Used to launch the application

Defines the file locations, starts mainwindow. Ensures that the appropriate Window gains focus

## MainWindow - mainwindow.py

Creates the Main window and defines the event handling

Includes the following files which provide various UI components

## layout package

### UILayoutMixin - Mixin pattern class with UI parts from MainWindow (Layout related)

Includes actions related to the Layout and the main layout area of the screen.

Creates dialogs based on the following ui files

* editguidialog.ui
* editglabeldialog.ui
* editgbuttondialog.ui

### Layout / Layouts

* Layout
* Layouts (multiple Layout objects)

### Dialogs for adding layout objects

* AddButtonDialog
* AddDeviceDialog
* AddLabelDialog

### GUI Objects

* TrackViewNode (Groups TrackViewNodes into a TrackViewNode)
* TrackViewNode (Parent class for following classes)
* LayoutButton
* LayoutDialog
* LayoutDisplay
* LayoutLabel



## loco package

### UILocoMixin - Mixin pattern class with UI parts from MainWindow (Loco related)

Includes actions related to the Locos within the main window

### LocoManager singleton

Used to create loco_manager as collection of locos

* LocoList - list of locos and their files

### Loco classes

* Loco - holds a loco

### LocoWindow

Window to managed Locos

* LocoEntry - holds a row for a loco

### Other Dialogs

* LocoDialog (locodialog.ui)
* StealDialog (stealdialog.ui) - Used for aquiring a loco already aquired





## ui_devices package

### ui_devices.py - Mixin pattern class with UI parts from MainWindow (Device related)

Includes actions related to the Devices within the main window

## ui_automate package

### ui_automate.py - Mixin pattern class with UI parts from MainWindow (Automation related)

Includes actions related to Automation within the main window



## events package

The first entries are children of Event

* Event
* AppEvent
* DeviceEvent
* GuiEvent

The others are standalone events

* LocoEvent
* TimerEvent
* LogEvent
* VarEvent



