from PySide6.QtCore import Qt, QTimer, QObject, QThreadPool, QRunnable
import logging
from .vlcbclient import VLCBClient
from .worker import Worker
from .eventbus import event_bus
from events import LocoEvent, GuiEvent, AppEvent, DeviceEvent
import time
from pyvlcb import VLCB
from pyvlcb import VLCBOpcode
from device import device_manager, VLCBNode

logger = logging.getLogger(__name__)

class ApiHandler(QObject):
    def __init__(self, thread_pool: QThreadPool, url, api_key, server_client=None):
        super().__init__()
        self.threadpool = thread_pool
        self.url = url
        self.api_key = api_key
       
        logger.debug (f"APiHandler URL {self.url}")

        # Keep alive timer must run on mainwindow and must be started / stopped using signals
        
        # Queue to hold commands as they are sent from the queue
        self.send_queue = []

        self.update_in_progress = False
        
        # The class is called client, but as it's used to communicate
        # with the server it's referred to in this as self.server
        # Allow injection of a mock or alternate client for testing.
        self.server = server_client or VLCBClient(self.url, self.api_key)

        # Add request to be sent next time timer expires
        #self.send_queue = []
        self.pc_can_id = 60      # CAN ID of CANUSB4
        
        # Current position in server log entries and amount of data received
        # If -1 will try and get all including old entries
        # If None just get the last few packets received (effectively start from current instead of history)
        # None is -5 to ensure see the initial discover
        self.last_packet = None
        
        # Get events from the event_bus
        event_bus.device_event_signal.connect(self.vlcb_event)
        # Loco events can be sent to API if unable to access API class
        # This is case if loco_manager is sending request  eg. if need to send gloc (share / steal)
        event_bus.loco_event_signal.connect(self.loco_event)
        
        # VLCB and node creation
        self.vlcb = VLCB(self.pc_can_id)
        
    # Receives event from event_bus and issues start_request
    def vlcb_event (self, event):
        self.start_request(self.vlcb.accessory_command(event.get_node_id(), event.get_event(), event.get_value()))

    def loco_event (self, event):
        """ The API action allows direct instructions to the API
        This can be particularly useful from automation step
        which doesn't have direct access to the mainwindow class to call 
        it's own commands 
        """
        if event.get_action() == "api":
            # loco_id is common, although many use session_id and some don't need either
            loco_id = event.get_loco_id()
            command = event.get_command()
            if command == "acquire":
                self.start_request(self.api.vlcb.allocate_loco(loco_id))
            # Allow share or steal
            elif command == "share":
                self.start_request(self.vlcb.share_loco(loco_id))
            elif command == "steal":
                self.start_request(self.vlcb.steal_loco(loco_id))
            elif command == "function":
                # Instead of needing to allocate the loco have the LocoEvent include current and new
                # Then can just send current / new as appropriate
                current = event.get_arg("currentvalue")
                new = event.get_arg("newvalue")
                session = event.get_arg("session")
                # current and new are byte1_2 as a tuple
                request_new =  self.vlcb.loco_set_dfun(session, *new)
                request_current = self.vlcb.loco_set_dfun(session, *current)
                func_type = event.get_arg("type")
                if func_type == "trigger":
                    # delay left to default (4 secs)
                    self.start_request_onoff (request_new, request_current)
                # if not just change to newvalue
                else:
                    self.start_request(request_new)
            elif command == "speed_dir":
                self.start_request(self.vlcb.loco_speed_dir(
                    event.get_session_id(),
                    event.get_arg("speed"),
                    event.get_arg("direction")
                    ))
            # Same as speed_dir but combined speed and direction
            elif command == "speeddir":
                self.start_request(self.vlcb.loco_speed_dir(
                    event.get_arg("session"),
                    event.get_arg("speeddir")
                    ))
        
    # Gets request off the queue
    # Returns false if no requests, otherwise returns request string
    # If remove = True (default) then remove entry from the queue
    def get_request (self, remove=True):
        # If no entries then return false
        if len(self.send_queue) < 1:
            return False
        # if no remove then just return value
        if remove == False:
            return self.send_queue[0]
        # Otherwise pop the entry
        return self.send_queue.pop(0)
    
    # Places request on wait list
    # type is what kind of command to prepend with - eg. send (for cbus) or server etc.
    # comma is added automatically
    # set to "" if already formatted
    # Adding priority pushes to front of queue
    def start_request (self, request, type="send", priority=False):
        # add type to request
        # Priority ignores list length and just inserts at front
        # pushes other priority items further down the list as well
        if priority:
            self.send_queue.insert(0, request)
        # only add to the list if <= 10 items already
        if len(self.send_queue) > 10:
            return False
        self.send_queue.append(request)
        return True

        
    # Use for sending multiple requests (needed for some messages)
    # Sent every 2 seconds (or change delay) - delay in seconds
    # Send num_send times
    def start_request_repeat (self, request, num_send = 1, delay = 2):
        self.start_request(request)
        num_send -= 1
        if num_send > 0:
            QTimer.singleShot(delay * 1000, lambda: self.start_request_repeat(request, num_send, delay))


    # Used for trigger commands where on is sent folloewd by off
    # Sends on followed by off (typically 4 seconds later)
    def start_request_onoff (self, request_on, request_off, delay = 4):
        # Turn on
        self.start_request(request_on)
        # Turn off after delay
        # Don't check for None returned as if it worked before should be no reason for it to fail now
        QTimer.singleShot(delay * 1000, lambda: self.start_request(request_off)) 


    # Run in thread
    # Query web - get data
    # If from web notify newdata
    # If update to node / events then update nodes and
    # notify updatenode
    def thread_getupdate(self):
        #Only allow one thread at a time
        self.update_in_progress = True
                      
        # see if there is a specific request
        request = self.get_request()
        if request != False:
            response = self.server.send (request)
            if response == None:
                self.update_in_progress = False
                self.status = "Not connected"
                return
            else:
                self.status = "Connected"
            
        # Get updates since last_packet
        response = self.server.read (self.last_packet)
        # If response None then error getting update - skip for now and
        # try again next time we poll
        if response == None:
            self.update_in_progress = False
            self.status = "Not connected"
            return
        else:
            self.status = "Connected"

        # First line is summary
        # Check for an empty data first as we can ignore
        if response[0:10] == "Read,0,0,0":
            # No new data received
            pass
        # Check response starts with "Read,"
        elif response[0:5] == "Read,":
            # split into status_line and data
            status_data = response.split('\n',1)
            logger.debug (f"Status data {status_data}")

            # First line format is "Read,<start>,<end>,<numlines>"
            header = status_data[0].split(',', 3)

            # check to see if field 3 is negative - if so then most likely that
            # the server has been restarted and we are ahead
            # Here just reset last_packet to 0 and then continue
            # If prefer could continue, or perhaps request a negative number
            # to just get a fixed number of entries
            packets_received = int (header[3])
            if packets_received < 0:
                logger.warning ("Restarting after possible server restart")
                self.last_packet = None
                self.update_in_progress = False
                return
            
            # need end to know what our last stored value is
            this_last_packet = int(header[2])
            if self.last_packet == None or self.last_packet < this_last_packet:
                self.last_packet = this_last_packet      
            data_packets = status_data[1].split('\n')
            for data_packet in data_packets:
                # if data_packet is empty then skip completely - without any notice as most likely due to \n at end
                if data_packet == '':
                    continue
                
                if len(data_packet) < 5:    # If data too short (perhaps empty line) - in reality this is much longer as includes date
                    logger.warning("Skipping empty packet")
                    logger.warning (f"This packet {data_packet}")
                    logger.warning (f"Data packets {data_packets}")
                    continue
                self.handle_incoming_data(data_packet)
        else:
            logger.warning (f"Unrecognised response {response}")
        self.update_in_progress = False


    def poll_server(self):
        # Only allow one check_responses thread to run at a time
        if self.update_in_progress == True:
            return
        
        worker = Worker(self.thread_getupdate)
        self.threadpool.start(worker)

    
    def handle_incoming_data (self, response):
        
        logger.debug(f"Incoming data {response}")

        # pass to console (unparsed)
        event_bus.publish(AppEvent({"action":"newdata", "response":response}))
        # temp send all as DeviceEvent (is that too much?)
        # Not implemented here - instead just send relevant events
        # event_bus.publish(DeviceEvent(response))
        
        # strip date off (don't need except for the log)
        id_date_data = response.split(',',3)
        if (len(id_date_data) < 4):
            logger.warning(f"Invalid entry - skipping {response}")
            return
        vlcb_entry = self.vlcb.parse_input(id_date_data[3])
        # If not a valid entry then ignore
        if vlcb_entry == False:
            logger.warning (f"Not a valid entry {id_date_data}")
            return
        
        logger.debug(f"VLCB Entry {vlcb_entry}")

        # Look for specific responses
        # future option? - should we check timestamp first? If the entry is from before the first request then may not be
        # interested as it's an old node. Alternatively we could load anyway (max 100 past entries are stored)
        # or we could not retrieve any previous messages by first checking for -1 entries and using that for
        # the start value
        # For now we handle all responses including old ones - but check for whether there are any changes

        # Special case check for null responses - If so set opcode to "NONE"
        ret_opcode = vlcb_entry.opcode()    # Instead of calling method for each condition save it in a variable
        logger.debug (f"Op code {ret_opcode}")

        match ret_opcode:    
            case 'ERSTOP':    # Emergency stop all
                # Emergency stop and stop all are the same
                # except for the message
                #self.loco_stop ("STOP ALL!")
                # Trigger an App Event to indicate all locos stopped
                event_bus.publish(AppEvent({
                            "action": "locoupdate", 
                            "value": "STOP ALL!"
                        }))
                
            case 'PNN':    # PNN (Response to query node)
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # Determine mode based on flags (bit 3)
                # Flags bit 0 = consumer, bit 1 = producer, bit 2= FliM, bit 3 = supports bootloading
                if data_entry['Flags'] & 0x4:
                    mode = "FLiM"
                else:
                    mode = "SLiM"


                # if we don't already have this device add it
                if not device_manager.node_exists(data_entry['NN']):
                    device_manager.add_node(VLCBNode(data_entry['NN'], mode, vlcb_entry.can_id, data_entry['ManufId'], data_entry['ModId'] ,data_entry['Flags']))

                else:
                    # Update existing entry
                    items_changed = device_manager.update_node(data_entry['NN'], {'Mode': mode, 'ManfId': data_entry['ManufId'], 'ModId': data_entry['ModId'], 'Flags': data_entry['Flags']})
                    # If no items changed then no need to check for further updates
                    if items_changed == 0:
                        return

                # If this is new, or has changed then we can also get the number of events
                self.discover_evn (data_entry['NN'])
            case 'NUMEV':    # Number of configured events
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # If we don't already have this node then didn't see a PNN response - so likely error
                if not device_manager.node_exists(data_entry['NN']):
                    logger.warning (f"NUMV response from Unknown node {data_entry['NN']}")
                    return
                # Update node with evnum value
                device_manager.set_numev(data_entry['NN'], data_entry['NumEvents'])
            case 'EVNLF':    # Number of event space left in node
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # If we don't already have this node then didn't see a PNN response - so likely error
                if not device_manager.node_exists(data_entry['NN']):
                    logger.warning (f"EVNLF response from Unknown node {data_entry['NN']}")
                    return
                # Update node with evnum value
                device_manager.set_evspc(data_entry['NN'], data_entry['EVSPC'])
                # Add a query for the next discovery stage - get a list of all the events
                self.discover_nerd (data_entry['NN'])
            case 'ENRSP':    # EV discovery
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # If we don't already have this node then didn't see a PNN response - so likely error
                if not device_manager.node_exists(data_entry['NN']):
                    # Most likely reason is connected to existing server with old entries
                    # So ignore unless debug
                    logger.debug(f"ENRSP response from Unknown node {data_entry['NN']}")
                    return
                # Add event to node
                device_manager.add_ev(data_entry['NN'], data_entry['EnIndex'], data_entry['En3_0'])

            # Indicates allocation of loco - need to verify this is expected
            case 'PLOC':
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # Session,AddrHigh_AddrLow,SpeedDir,Fn1,Fn2,Fn3'
                loco_id = data_entry['AddrHigh_AddrLow'] & 0x3FFF
                event_bus.publish(LocoEvent('PLOC', {
                    'Loco_id': loco_id,
                    'Session': data_entry['Session'],
                    'Speeddir': data_entry['SpeedDir'],
                    'Fn1': data_entry['Fn1'],
                    'Fn2': data_entry['Fn2'],
                    'Fn3': data_entry['Fn3'],
                    'Status': "on"
                    }))
                
                event_bus.publish(AppEvent({"action":"uitext", 'label': "locoStatusLabel", 'value': "Ready"}))
                # Set status to on last gives time to ensure all entries updated
                # Update controller with new values
                event_bus.publish(AppEvent({"action":"lcd"}))
                # Start the keepalive timer
                event_bus.publish(AppEvent({"action":"keepalive"}))
            ## Update events - these need to notify other devices
            # Accessory On (eg ACON = Acc / ASON = short)
            # Works on both event codes (eg. ACON) and status codes (eg. ARON)
            # Uses 'active' True / false
            # match guard clause: checks if the opcode is within a lit
            case _ if ret_opcode in VLCBOpcode.accessory_codes['on']:
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # pass all data into event, but also add additional information
                data_entry ['node_id'] = data_entry ['NN']
                # Long codes (ACON) use Event Number, Short codes (ASON) use Device Number
                if 'EnHigh_EnLow' in data_entry:
                    data_entry ['event_id'] = data_entry ['EnHigh_EnLow']
                elif 'DNHigh_DNLow' in data_entry:
                    data_entry ['event_id'] = data_entry ['DNHigh_DNLow']
                # Catch unknown
                else:
                    data_entry['event_id'] = 0
                data_entry ['active'] = True
                data_entry ['value'] = "on"
                #print (f"On code {data_entry}")
                self.consume_device_event (data_entry)
            # Accessory Off (eg ACOFF = Acc / ASOF = short)
            case _ if ret_opcode in VLCBOpcode.accessory_codes['off']:
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                data_entry ['node_id'] = data_entry ['NN']
                if 'EnHigh_EnLow' in data_entry:
                    data_entry ['event_id'] = data_entry ['EnHigh_EnLow']
                elif 'DNHigh_DNLow' in data_entry:
                    data_entry ['event_id'] = data_entry ['DNHigh_DNLow']
                # Catch unknown
                else:
                    data_entry['event_id'] = 0
                data_entry ['value'] = "off"
                #print (f"Off code {data_entry}")
                self.consume_device_event (data_entry)
            # ERR is error from DCC controller - eg. problem acquiring loco
            case 'ERR':
                logger.info ("Error message received")
                # Depending upon the error code the data may have different interpretations
                # Stored as Byte1, Byte2, ErrCode - where Byte1,Byte2 may eqal AddrHigh_AddrLow, or
                # may be Byte1 = Session ID, Byte 2 = 0
                # So only check after looking at the ErrCodepublish_device_event 
                data_entry = VLCBOpcode.parse_data(vlcb_entry.data)
                # After extracting data publish as an event then let receiving classes process
                event_bus.publish(LocoEvent('ERR', data_entry))
            case _:
                logger.warning(f"Unknown opcode {ret_opcode}")

    
    # Initial discovery of modules    
    def discover (self):
        self.start_request(self.vlcb.discover())
        
    # 2nd phase in discovery RQEVN to get number of events
    # and NNEVN - get number of events available
    def discover_evn (self, node_id):
        self.start_request(self.vlcb.discover_evn(node_id))
        self.start_request(self.vlcb.discover_nevn(node_id))
        
    # 3rd phase of discover Read back all stored events in a node (NERD)
    def discover_nerd (self, node_id):
        self.start_request(self.vlcb.discover_nerd(node_id))
        
    # Separate method for notifying automation of incoming device events
    # Searching for this shows which responses send device notify events to automation
    def consume_device_event (self, data):
        event_bus.consume(DeviceEvent(data))

        
