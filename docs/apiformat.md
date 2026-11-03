# API format for PiSignalBox


## New API - full client server

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


## Authentication

Authentication is handled within the application by use of an api_key. This needs to be stored both in the gui client settings and the server. The values are identical as a unique key.

This can be setup through the setup process.

## Application flow for requests and receive (new API)

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


## Raw Commands
Note for simplicity these are provided in a strict order and format

This is the old API format. This may be retired in future in future of the new API model. This is basic read of raw cbus/vlcb packets that are sent and received.

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

