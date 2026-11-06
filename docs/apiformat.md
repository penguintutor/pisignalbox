# API format for PiSignalBox


## New API - full client server - GUI Implementation

The new style API provides a full client server, where the server now manges the devices directly on the model railway. The API provides a way for the GUI client to send requests to the server which then provides a response which may be just a status or provide details of the railway.

There are other ways to communicate with the server including the CBUS interface, web interface and other clients. Certain signals (eg. loco speed change) are then fed back to connected clients so that they can update their local value. These updates are received and trigger appropriate events.

Commands are requested through the API Handler start_api_request(), which takes a dict with the parameters to be sent to the server.

### Loco API

This is the first API to be implemented on the server. 

All loco api requests must include "request_type": "loco" within the API. 

They then take a cmd
_ acquire
_ set_speed (also includes direction)
_ function

then parameters related to the command, eg. loco_id, speed, direction etc.

An example dictionary is shown below:

data_dict = {
        "request_type": "loco",
        "cmd": "set_speed",
        "loco_id": self.control_loco.get_id(),
        "speed": new_speed,
        "direction": self.control_loco.loco.direction
    }


### Loco Updates (stream)

Loco updates from the stream include the following

_ loco_speed


## GUI Authentication

Authentication is handled within the application by use of an api_key. This needs to be stored both in the gui client settings and the server. The values are identical as a unique key.

This can be setup through the setup process.

## GUI Application flow for requests and receive (new API)

### Updating a variable - thread safe

Note that updating simple variables can be performed on any thread.
This is due to the GIL on <=3.13 and free-threaded mode on >=3.13
As such it is common to make the update immediately and then get the data to send to the apprpriate thread. There is a small risk that if the GUI updates a value, then the API thread updates it from the stream to a different value, then sending the data could be either. The chance of this is very small and even if it does occur is no different to what happens if CBUS sends and receives commands from two sources at the same time. 
This is a feature of the shared server concept. It could be changed if that is a concern, but that would lose the benefit of having multiple ways to control the loco.

Note the operations that absolutely must be in the correct threads are:
_UI updates must all be on the GUI thread
_Any polling of data must be on threadpool to not lock up the GUI


### Sending a request
To send a request the parameters should be formed into a dict (often named data_dict) with the relevant parameters set.

It is then sent via the APIHanadler eg. 
self.api.start_api_request(data_dict)

The API Handler adds it to the send queue, which is picked up by the running thread thread_getupdate

Depending upon the request type it will be passed on to the
appropriate request within vlcbclient. For locos this is VLCBClient -> send_loco()

To ensure this is on the correct thread this is sent to
VLCBClient _execute_send_loco() - which passes to do_send_loco()

This maps the request (eg. cmd) into the appropriate api 
url 
**This needs to be updated whenever a new cmd is used**

The response is sent to VLCBClient _handle_loco_reply which handles receieving the data and passes on to _handle_loco_updates

If the client needs a response (eq. if aquiring or need to get a value back from the server) then the event needs to be handled there. 
**This needs to be updated regardless even if just to not create the "Unknown Response" log entry**

If an update is needed to the client, this will then publish a an appropriate event. Eg. for a loco it sends a LocoEvent

In the case of LocoEvents these are received by LocoManager event_trigger - which allows it to update itself

**Add here any updates that need to be made within the locos based on the response**

The packet will also be recieved by _logentry_recv_loco.

**Add here how to deal with the response eg. so that the console understands
what is received.**


## Incoming Data - GUI

Incoming data can come through responses to sent commands, stream notifications from the server, or regular polling (currently using the old API).


### Polling is issued from MainWindowUI using self.timer. 
This calls handle_polling(), which provides for throttling of requests in the event of a connection failure. 

This is passed to self.api - which uses the ThreadPool to run APIHandler without looking up the GUI thread. 

ApiHandler poll_server starts the qthread and runs thread_getupdate.

The thread_getupdate is responsible for sending the outgoing packets first, and passing to the appropriate server command (vlcbclient talks to the server). In the case of loco commands they eventually go into _do_send_loco. It sends the request and the response is directed through a finshed.connect to _handle_loco_reply.

The loco API responses are handled within 
VLCBClient _handle_loco_updates()

**All new api responses should be added to _handle_loco_updates().**

After handling the send, then it performs a server.read (using vlcbclient.read(). It sends the last packet received so that any packets received since then are handled. This is dispatched to vlcbclient _execute_read, and the response is sent to _handle_read_reply. After broadcasting to the console this is then passed to vlcb_read_response which passes it to the ApiHandler update_from_read() and on to _handle_response, which parses the request, checks for valid packets and sends them to handle_incoming_data. This handles the raw opcode. 

**All raw opcode reads need to be handled within ApiHandler handle_incoming_data.**

As new response are generally parsed by the server first, there should be no need to add new op-codes here, but it can still be used if desired. Any updates are then pushed by publishing an AppEvent / LocoEvent etc.


### Stream updates - to GUI

The stream is started from VLCBClient, using start_listening. There is a QTimer that is triggered to restart this if the connection is lost. 

Incoming data goes into _on_sse_data()

It is then passed to _route_event which checks for the data type, reads the payload and dispatches it to the appropriate handler. 

**All new event_types (eg. loco_speed) need to be added into VLCBClient _route_event() to route to the appropriate handler.**

In the case of loco commands then these are passed to _handle_loco_updates the same handler that handles responses from the API send requests. 

**If not already added then VLCBClient _handle_loco_updates() needs to be updated with how to action the updates.**

The _handle_loco_updates looks as the response status, which uses standard wording, like "loco acquired" or "speed change success". After receiving these the appropriate event is published.

**In the case of locos these events are sent to loco_manager event_trigger where the update should be handled.**

The update will also publish an AppEvent which can be used by the UI to update settings. In the case of a loco this is picked up by MainWindow app_event.

**It may be neccessary to update the MainWindow app_event method if the update issued needs to update the UI"

**Possibly also need to update vlcbclient _logentry_recv_loco - to provide user friendly info for console"


# Server Side API handling (new API)
If from web app then uses /api/command and typically uses loco_ref to refer to the specific loco
If from client API (eg. GUI Client) then uses /api/client/command and typically uses loco_id to refer based on DCC ID. The @ routes use client to refer to the client functions, but other functions refer to those as "basic"

In many cases both types of loco need to updated to ensure that all clients have the same values, and that is mainly through the stream (broadcast announcer)

The API point is generall a @ blueprint route.
eg. @api_loco_bp.route()
This can be referred to within blueprint templates by the function name eg. url_for('api.client.client_function')

Typically this calls another function within the file which returns the response as a dict {"status": <status>, "message: <message>

If the command needs data to be sent via vlcb then that is calculated and typically put into a variable called vlcb_cmd. This normally uses the functions from the pyvlcb library - see https://penguintutor.github.io/pyvlcb/reference/ 

The data is then packaged into a dict similar to the one used to send to the API. This needs to include the 'dev_type' (eg. "loco") and 'action', along with any other parameters. 
eg.
{
    'vlcb': vlcb_cmd,
    'dev_type': "loco",
    'action': "speeddir",
    'loco_id': loco_id,
    'speeddir': speeddir
}
This is then passed to vlcb_bridge send_data() 

This then adds it to the mainthread where it can be sent. The queue is read by mainthread run_connected_loop. That sends the vlcb packet and then passes it to the appropriate handler. For locos this is mainthread _update_loco_status() 

**New methods need to be added in the _update_loco_status()**

This calls the appropriate method - eg. on loco_manager. Which updates the values, which may be across all the sessions. This then updates the appropriate parameter within the individual classes eg. locos.py. Which in return sends the status updates to the stream.

**New updates need to be announced from the individual class**

Note if a DCC ID is associated with multiple locos that are all "on track" then it will broadcast to all of them even if it's a duplicate.



## Server Side - incoming packets

On the server then mainthread has a loop run_connected_loop, which is responsible for sending and receiving from USB and the CANUSB4 (or appropriate hardware device). 

First and keepalives are sent so that the locos remain managed by the server.

Then any queued send requests are sent to the USB port. If the command is from the new API with dev_type then it's passed on to the internal handler to update the local status - such as _update_loco_status. 

_update_loco_status needs to know about the different types of value and how to update locally. They can then update directly through loco_manager. Because locos may be repeated between the web app and the client api then it may be neccessary to update multiple objects. 

The objects are responsible for sending direct to the stream using announce to pass the update to the client gui etc.

**Any new loco API commands need to be added to MainThread _update_loco_status().**

Incoming data is then polled from the USB using MainThread _process_inbound_data

This passes the packets on to vlcb_bridge add_sensor_udpate(). _update_local_state gets the update packets and passes to parse_input. This parses into the op-code and calls the appropate update - eg triggers to loco_manager to update their status.

**vlcb_bridge _update_local_state needs to parse any USB input packets, update the appropriate entry which then announces to the stream.**

This is one area where the USB data needs to be parsed even after moving to the new API model. 

That will be announced to the GUI (and can be sent to web app etc. )




## Raw Commands (Old API)
Note for simplicity these are provided in a strict order and format

This is the old API format. This may be retired in future in future of the new API model. This is basic read of raw cbus/vlcb packets that are sent and received.This is still required for much of the functionality within the GUI. This is likely to persist for some time. 


To send then generate the raw vlcb request and pass to the api. 

/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
/vlcb?send=<string of send request>&format=txt

read can also use read=-<value> to count from end instead of packet number
if a start packet doesn't exist then start from lowest value


#read is used to "read" stored data

possibly allow get / query to integrate individual items - but currently expect the client to create
these as send commands

Send must be a single CBUS message starting with : and ending with ; (url encoded)
All content must be alphanum - anything else and it will not be sent to CBUS


Response 
First line = Read,start,end,count
If count is 0 then no new data
If count is negative then indicates error
Eg. if try to read beyond end of data

remaining entries are
msg_count,date,data_string



## Raw commands

/vlcb?data=<raw data>
vlcb,data
(data typically :S???????;

## Console

Query the console
/console?start=<lognum>
console,lognum
Returns log entries starting with lognum
Numbering starts with 0, so 0 will try and return all entries, but limited internally to set number
response includes total number of log entries
Passing a negative number will count that far back from end of log

