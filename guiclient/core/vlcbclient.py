# Client interface for VLCB server 
# sends using url to vlcbserver (c version)
# Needs url (eg. http://127.0.0.1:5000/)

# Note due to url restrictions : and ; need to be encoded

import urllib.request, urllib.parse
from .eventbus import event_bus
from events import LocoEvent, GuiEvent, AppEvent, DeviceEvent
import json
import logging

logger = logging.getLogger(__name__)

### Set logging to console during testing
### Uncomment the following text to allow debugging to the terminal
### This will show all URL requests etc.
# #Create a handler that outputs to the console (terminal)
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.DEBUG)
# # Create a formatter to make the output readable
# formatter = logging.Formatter('%(levelname)s in %(name)s: %(message)s')
# console_handler.setFormatter(formatter)
# # Attach the handler to your logger
# logger.addHandler(console_handler)


class VLCBClient():
    def __init__ (self, url, api_key=None):
        self.url = url
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key

    # Todo return and handle different messages
    # Eg. notify if an error so the API knows (to throttle)
    # and to notify the user
    def send (self, message):
        message = urllib.parse.quote(message)
        # Note that this adds the api prefix to act as an api
        request_string = f"{self.url}api/vlcb?send={message}&format=txt"
        logger.debug(f"Send request {request_string}")
        req = urllib.request.Request(request_string, headers=self.headers)
        try:
            request_url = urllib.request.urlopen(req)
            response = request_url.read()
        except urllib.error.HTTPError as e:
            # Catches server errors eg. 404 not found, 401 unathorized, 500 internal server error
            logger.warning(f"Error sending via http {request_string}: {e.code}, {e.reason}")
            # Todo - create user friendly messages
            # probably want to stop the app requests for something that needs an update
            # eg. 401 - not authorised
            print (f"HTTP Error {e.code} {e.read().decode('utf-8')}")
            # None indicates not connected
            return None
        except urllib.error.URLError as e:
            logger.warning(f"Error sending via http, due to network connection error {e.reason}")
            # None indicates not connected
            return None
        except TimeoutError as e:
            logger.warning(f"Error sending via http, due to timeout {e}")
            # None indicates not connected
            return None
        except Exception as e:
            logger.warning(f"Error sending via http, other error {e}")
            # None indicates not connected
            return None
        if response[0:7] == "Success":
            logger.debug(f"Send response received {response}")
            return True
        logger.debug(f"Message not working {response}")
        return False

    # Uses new "unamnaged loco api"
    # Takes a dict with "request_type" == "loco"

    # Typial data_dict keys 
    # "request_type" = loco
    # "cmd" (eg. acquire)
    # loco_id / session_id
    # optional speeddir etc....

    def send_loco (self, data_dict):
        request_string = None
        # check that it is a loco command 
        if "request_type" not in data_dict or data_dict["request_type"]!= "loco":
            logger.debug("Invalid request")
            # Returns False - if return None then interpretted as disconnected
            return False
        
        # Note that this adds the api prefix to act as an api
        api_string = f"{self.url}api/loco/client"

        match data_dict.get("cmd"):
            case "acquire":
                loco_id = data_dict.get("loco_id")
                if loco_id > 0: 
                    request_string = f"{api_string}/acquire?loco_id={loco_id}"
            case "set_speed":
                loco_id = data_dict.get("loco_id", 0)
                speed = data_dict.get("speed", 0)
                direction = data_dict.get("direction", 1)
                if loco_id > 0:
                    request_string = f"{api_string}/speed_dir?loco_id={loco_id}&speed={speed}&direction={direction}"
            case "get_status":
                loco_id = data_dict.get("loco_id", 0)
                if loco_id > 0:
                    request_string = f"{api_string}/status?loco_id={loco_id}"


        # if request_string not set then nothing to send
        if not request_string:
            logger.debug(f"Unknown loco command {data_dict['cmd']}")
            return False

        
        logger.debug(f"Send request {request_string}")
        req = urllib.request.Request(request_string, headers=self.headers)
        try:
            request_url = urllib.request.urlopen(req)
            response = request_url.read()
        except urllib.error.HTTPError as e:
            # Catches server errors eg. 404 not found, 401 unathorized, 500 internal server error
            logger.warning(f"Error sending via http {request_string}: {e.code}, {e.reason}")
            # Todo - create user friendly messages
            # probably want to stop the app requests for something that needs an update
            # eg. 401 - not authorised
            print (f"HTTP Error {e.code} {e.read().decode('utf-8')}")
            # None indicates not connected
            return None
        except urllib.error.URLError as e:
            logger.warning(f"Error sending via http, due to network connection error {e.reason}")
            # None indicates not connected
            return None
        except TimeoutError as e:
            logger.warning(f"Error sending via http, due to timeout {e}")
            # None indicates not connected
            return None
        except Exception as e:
            logger.warning(f"Error sending via http, other error {e}")
            # None indicates not connected
            return None
        
        # convert response to dict
        try:
            response_dict = json.loads(response)
        except Exception as e:
            logger.warning(f"Send loco returned none JSON format {e}")
            return None

        # Now have response as a dict - pass it on to 
        # handler to update the loco
        self._handle_loco_updates(loco_id, response_dict)


    def _handle_loco_updates (self, loco_id, response_dict):
        # Check the response and mostly create an event which
        # locomanager will pick up and process
        match response_dict["status"]:
            case "loco acquired":
                event_bus.publish(LocoEvent('acquired', response_dict))
                logger.debug(f"Loco acquired for {loco_id}")
                return True
            case "acquiring":
                logger.debug(f"Acquiring received for {loco_id}")
                event_bus.publish(LocoEvent('acquiring', response_dict))
                return True
            case "loco update":
                # check he loco_id matches this loco_id
                if response_dict.get("loco_id") != loco_id:
                    logger.warning(f"Incorrect loco_id received from server {response_dict}")
                    return 
                # pass on to loco_manager to perform update
                # Not all parameters in dict will be used by 
                # loco_manager but all passed
                event_bus.publish(LocoEvent('update', response_dict))
                return True
                

        logger.debug(f"Unknown response from loco api request {response_dict}")
        return False
    
    # Read after last packet 
    def read (self, last_packet):
        # if lastpacket does not have a value then read from 0 (have no data)
        if last_packet == None:
            last_packet = -5
        else:
            last_packet += 1	# Read next packet
        request_string = f"{self.url}api/vlcb?read={last_packet}&format=txt"
        logger.debug(f"Reading {request_string}")
        # Create a Request object
        req = urllib.request.Request(request_string, headers=self.headers)
        try:
            request_url = urllib.request.urlopen(req)
            response = request_url.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            # Todo: handle errors here as well
            # Catches server errors eg. 404 not found, 401 unathorized, 500 internal server error
            logger.warning(f"Error reading via http {request_string}: {e.code}, {e.reason}")
            # None indicates not connected
            return None
        except urllib.error.URLError as e:
            logger.warning(f"Error reading via http, due to network connection error {e.reason}")
            # None indicates not connected
            return None
        except TimeoutError as e:
            logger.warning(f"Error reading via http, due to timeout {e}")
            # None indicates not connected
            return None
        except Exception as e:
            logger.warning(f"Error reading via http, other error {e}")
            # None indicates not connected
            return None
        logger.debug(f"Read response received {response}")
        return response
        
        