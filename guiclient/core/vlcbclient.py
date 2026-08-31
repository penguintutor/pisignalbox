# Client interface for VLCB server 
# sends using url to vlcbserver (c version)
# Needs url (eg. http://127.0.0.1:5000/)

# Note due to url restrictions : and ; need to be encoded

import urllib.request, urllib.parse
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
        
        