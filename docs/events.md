# Events

Signals and Slots are fundamental to the implementation of the PiSignalbox application

These are handled through events, managed by the event_bus which dispatches
signals to the appropriate parts of the application.

These are the event types and how they are used

VLCB should be used in preference to Device for mapping purposes
'VLCB': DeviceEvent
'Device': DeviceEvent,
'Loco': LocoEvent,
'App': AppEvent,
'Gui': GuiEvent,
'Timer': TimerEvent,
'Var': VarEvent,
'Log': LogEvent

Note that any device can consume from any event through the use of rules. This guide lists the typical use outside of the custom rules.

## AppEvent
Used to notify the Gui when it needs to update its status or interact with a user (eg. Dialog for aquiring loco)

Note that due to logging in console all incoming actions from the API (eg. VLCB) are sent as AppEvents. 

## DeviceEvent 
These are triggered in response to a notification from a VLCB or other device node. 

The Device Event is triggered whenever a new node is added, or a node / ev changes any status.

Device Events are typically consumed by rules (eg. to pass to treeview objects) or for automation.

Typically these are triggered from the ApiHandler (updated from VLCB) or from DeviceManager (eg. when a node is added)

## GuiEvent 
Typically triggered in response to a click or interaction with a TreeViewNode, or other Gui request from the user. 

# LocoEvent

