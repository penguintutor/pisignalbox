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



