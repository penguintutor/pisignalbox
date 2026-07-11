# Client interface for VLCB server 
# sends using url to vlcbserver (c version)
# Needs url (eg. http://127.0.0.1:8888/)

# Note due to url restrictions : and ; need to be encoded

import urllib.request, urllib.parse
import logging

logger = logging.getLogger(__name__)

class VLCBClient():
    def __init__ (self, url):
        self.url = url
    
    def send (self, message):
        message = urllib.parse.quote(message)
        request_string = f"{self.url}vlcb?send={message}&format=txt"
        logger.debug(f"Send request {request_string}")
        try:
            request_url = urllib.request.urlopen(request_string)
            response = request_url.read()
        except urllib.error.HTTPError as e:
            # Catches server errors eg. 404 not found, 401 unathorized, 500 internal server error
            logger.warning(f"Error sending via http {request_string}: {e.code}, {e.reason}")
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
        if response[0:7] == "Success":
            return True
        return False
    
    # Read after last packet 
    def read (self, last_packet):
        # if lastpacket does not have a value then read from 0 (have no data)
        if last_packet == None:
            last_packet = -5
        else:
            last_packet += 1	# Read next packet
        request_string = f"{self.url}vlcb?read={last_packet}&format=txt"
        logger.debug(f"Reading {request_string}")
        try:
            request_url = urllib.request.urlopen(request_string)
            response = request_url.read().decode('utf-8')
        except urllib.error.HTTPError as e:
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
        return response
        
        