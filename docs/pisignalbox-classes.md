# PiSignalBox - Classes and files

## App - app.py - Application launcher for GUI application

Used to launch the application

Defines the file locations, starts mainwindow. Ensures that the 
appropriate Window gains focus

## mainui - directory - Graphical Application

Primary systems associated with the main application window. 
Also see console for details of the console window.

### MainWindow - mainwindow.py - Main application winwo

Creates the Main window and defines the event handling

Uses the mxin patter to include files prefixed with ui_ which provide 
various UI components.

### SystemExplorer - systemexplorer.py

Provides the device tree view. Called directly from the MainWindow, it 
displays it within the main window.

When adding nodes (including hardware and trackview) then they should 
be added through this class.

## Core - directory - Core non-GUI classes

The core directory holds the core classes used in implementing the 
functionality. These are non-GUI classes that should not be aware, nor 
require Pyside6 libraries, except where used for Signals and Slots, or 
threads.

### ApiHandler - apihandler.py - Api connections for communicating with VLCB

The API handler provides communications to and from the VLCBServer API. 
This includes sending and receiving messges from the VLCB server for 
messages sent via CBUS. 

It polls the VLCBserver for new messages and where appropriate handles
adding new devices. Other messages are usually sent to the event_bus for
onward processing.

### AppVar - appvar.py

Provides special Global Variables which can be used across the 
application including for automation. 

Variables should always be updated through the getters and setters 
which ensure that the event_bus is also informed of new / changed 
variables. 

### Constants - contants.py

Constants used across the application. These are not created as a class
and can be imported directly into a suitable application.

### event_bus - eventbus.py - Event Bus for sending and receiving events.

Application classes will typically publish an event. This will apply 
any standard rules and then broadcast a signal allowing other classes
to handle the event. 

The Api Handler will useally request the event_bus to consume and event
which will apply the rules without broadcasting the event.

### Paths - paths.py

The paths file provides variables for holding paths for the application
and data. These are treated like constants, but can be changed during
early stages of runtime if appropriate (eg. from command line options).

### Settings - settings.py - Application settings

The Settings class handles loading, querying and saving of application
settings. 

### VLCBClient - vlcbclient.py - Communication to the API

The API handler calls the VLCBClient when it needs to communicate with
the VLCBServer API. This provides a send and read method which can be
used to communicate with the server.

### Worker - worker.py - Worker class for threads

The Worker class is used by the ApiHandler for handling threads. 

### WorkerSignals - workersignals.py - Signals for workers

The Worker Signals class provides the signals which other parts of the 
application to listen to. These are used to broadcast thread based
messages.


## layout - directory

### Layout - layout.py - Single Layout

Holds a layout, which is used to manage active elements. 

Holds the track_view_nodes which are added and managed through the 
Layout class

### LayoutDialog - layoutdialog.py

Used to select a layout and create a new layout.

### Layouts - layouts.py

Used to list and manage the layouts. 
Currently limited in use as don't allow editing layout unless actively 
loaded. Could be expanded in future if required.


## trackview - directory

Track view adds graphical / app related elements, such as points, 
labels etc.
Creates dialogs based on the following ui files

* AddDeviceDialog uses editguidialog.ui
* AddLabelDialog uses editglabeldialog.ui
* AddButtonDialog uses editgbuttondialog.ui

Includes the following object types

* TrackViewNode (Groups TrackViewNodes into a TrackViewNode)
* TrackViewNode (Parent class for following classes)
* TrackViewDisplay (used to hold and display the objects)
* TrackViewButton
* TrackViewLabel

### UITrackViewMixin - Mixin pattern class with UI parts from MainWindow (Layout related)

Includes actions related to the Layout and the main layout area of the 
screen.

### track_view_manager - trackviewmanager.py

Holds the track view elements

### TrackViewDisplay - trackviewdisplay.py - Manages display of track view objects

Handles the layout of the track view objects within the screen. 

### TrackViewNode - trackviewnode.py

A node is a high level object, such as a point or a signal. This will
then have child nodes (elements) such as labels and buttons. 

### TrackViewElement - trackviewelement.py - Abstract element class

This is an abstract class used for the child objects such as
TrackViewButtons and TrackViewLabels

### TrackViewLabel - trackviewlabel.py

A label is usually a text string used to identify a particular node.
For example one may be called "point 1". When clicked these will 
typically toggle the status through the different node states.

### TrackViewButton - trackviewbutton.py

Typically a clickable image. Typically used to indicate the position 
of a point, or a signal etc. It has it's own state and can change
it's appearance accordingly (eg. red / green). When clicked it will 
typically set that element to the active state.




## loco - directory

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



## Automation

### Automation Sequence
Handle the creation of steps & rules
Ensures that locomotives are allocated if required
Handles the sequence flow - eg. loops 


#### Automation Step
Creates and handles rules 
Looks up and updates variables
Handles wait commands
Runs the rules, typically through sending broadcast (eg. to VLCB)








