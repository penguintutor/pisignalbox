# Client interface for VLCB server 
# sends using url to vlcbserver (c version)
# Needs url (eg. http://127.0.0.1:5000/)

# Note due to url restrictions : and ; need to be encoded

import urllib.request, urllib.parse
from PySide6.QtCore import QObject, QUrl, QUrlQuery, QByteArray, Signal, Slot, QTimer, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from .eventbus import event_bus
from events import LocoEvent, GuiEvent, AppEvent, DeviceEvent, LogEvent
import json
import uuid
import logging

logger = logging.getLogger(__name__)


class VLCBClient(QObject):

    # Internal signals for cross-thread bouncing
    _internal_send_loco = Signal(dict)
    _internal_send_msg = Signal(str)
    _internal_read = Signal(object) # uses object to allow None or int

    # Message back to api handler when 
    # a read response occurs
    vlcb_read_response = Signal(str)


    def __init__(self, url, api_key=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key

        # Generate a random ID every time the app launches
        self.client_id = str(uuid.uuid4())

        self.nam = QNetworkAccessManager(self)
        self.sse_reply = None
        self.buffer = ""

        # CSRF refresh state and queued retry callbacks
        self._is_refreshing_csrf = False
        self._pending_csrf_retries = []

        # Auto-reconnect timer for the SSE stream
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.setInterval(3000)
        self.reconnect_timer.timeout.connect(self.start_listening)

        # Wire the signals to the execution slots using QueuedConnection
        self._internal_send_loco.connect(self._execute_send_loco, Qt.ConnectionType.QueuedConnection)
        self._internal_send_msg.connect(self._execute_send_msg, Qt.ConnectionType.QueuedConnection)
        self._internal_read.connect(self._execute_read, Qt.ConnectionType.QueuedConnection)

        # If no API key is configured, fetch an initial CSRF token and session cookie
        if not api_key:
            QTimer.singleShot(0, self._refresh_csrf_token)

        # Start listening for the stream
        # 0ms delay to ensure the init has finished before starting
        QTimer.singleShot(0, self.start_listening)

    @Slot()
    def _on_disconnected(self):
        event_bus.broadcast(LogEvent( self._logentry_stream_status ("disconnect") ))
        logger.warning("SSE Stream disconnected. Reconnecting in 3 seconds...")
        self.reconnect_timer.start()


    ################################################
    # CSRF Token Management
    ################################################

    def _refresh_csrf_token(self):
        """Fetches a fresh CSRF token from the server and replays queued requests."""
        if self._is_refreshing_csrf:
            return

        self._is_refreshing_csrf = True
        csrf_url = QUrl(f"{self.url}api/csrf-token")
        logger.debug(f"Fetching fresh CSRF token from {csrf_url.toString()}")

        req = QNetworkRequest(csrf_url)
        req.setRawHeader(b"Accept", b"application/json")

        for key, value in self.headers.items():
            req.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))

        reply = self.nam.get(req)
        reply.finished.connect(lambda r=reply: self._handle_csrf_reply(r))

    def _handle_csrf_reply(self, reply: QNetworkReply):
        """Stores the new CSRF token and triggers any requests waiting on it."""
        self._is_refreshing_csrf = False
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                logger.warning(f"Failed to fetch CSRF token: {reply.errorString()}")
                self._pending_csrf_retries.clear()
                return

            response_bytes = reply.readAll().data()
            data = json.loads(response_bytes.decode("utf-8"))
            new_token = data.get("csrf_token")

            if new_token:
                self.headers["X-CSRFToken"] = new_token
                logger.debug("CSRF token updated successfully.")

                # Replay all queued requests with the new token
                pending = self._pending_csrf_retries[:]
                self._pending_csrf_retries.clear()
                for retry_callback in pending:
                    retry_callback()
            else:
                logger.warning("CSRF endpoint did not return a csrf_token.")
                self._pending_csrf_retries.clear()

        except Exception as e:
            logger.warning(f"Error parsing CSRF token response: {e}")
            self._pending_csrf_retries.clear()
        finally:
            reply.deleteLater()

    def _check_csrf_error(self, reply: QNetworkReply, retry_callback) -> bool:
        """
        Checks if a failed reply was caused by a missing or expired CSRF token.
        If so, queues the retry_callback, initiates a token refresh, and returns True.
        """
        if retry_callback is None:
            return False

        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status_code in (400, 401):
            try:
                raw_bytes = reply.readAll().data()
                err_data = json.loads(raw_bytes.decode("utf-8"))
                if err_data.get("code") in ("CSRF_EXPIRED", "CSRF_MISSING"):
                    logger.info(f"CSRF token {err_data.get('code')}. Refreshing and retrying request...")
                    self._pending_csrf_retries.append(retry_callback)
                    self._refresh_csrf_token()
                    return True
            except Exception:
                pass
        return False


    ################################################
    # Public API (Safe to call from ANY thread)
    # Also broadcast a log event
    ################################################

    def send_loco(self, data_dict):
        """ Send loco event using new API """
        event_bus.broadcast(LogEvent( self._logentry_send_loco (data_dict) ))
        self._internal_send_loco.emit(data_dict)

    def send(self, message: str):
        """ Send VLCB request using old API """
        self._internal_send_msg.emit(message)

    def read(self, last_packet):
        """ Read VLCB requests using old API (polling)"""
        self._internal_read.emit(last_packet)


    ################################################
    # Internal Slots (Forced to run on the Main GUI Thread)
    ################################################

    @Slot(dict)
    def _execute_send_loco(self, data_dict):
        """Slot wrapper that calls _do_send_loco with retry enabled."""
        self._do_send_loco(data_dict, is_retry=False)

    def _do_send_loco(self, data_dict: dict, is_retry: bool = False):
        """The actual network code, safely running on the main thread."""
        if data_dict.get("request_type") != "loco":
            logger.debug("Invalid request")
            return
        
        cmd = data_dict.get("cmd")
        loco_id = data_dict.get("loco_id", 0)
        
        if loco_id <= 0:
            logger.debug("Invalid loco_id")
            return

        api_string = f"{self.url}api/loco/client"
        url = QUrl()
        
        # Build the JSON payload dictionary
        payload = {"loco_id": loco_id}
        
        # Prevent SSE echoes using client_id
        if hasattr(self, "client_id"):
            payload["source_id"] = self.client_id

        # Map commands to endpoints and populate the payload
        match cmd:
            case "acquire":
                url.setUrl(f"{api_string}/acquire")
            case "set_speed":
                url.setUrl(f"{api_string}/speed_dir")
                payload["speed"] = data_dict.get("speed", 0)
                payload["direction"] = data_dict.get("direction", 1)
            case "get_status":
                url.setUrl(f"{api_string}/status")
            case _:
                logger.debug(f"Unknown loco command {cmd}")
                return

        logger.debug(f"Send async POST request to {url.toString()} with {payload}")

        json_data = json.dumps(payload).encode("utf-8")

        req = QNetworkRequest(url)
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        if hasattr(self, "headers"):
            for key, value in self.headers.items():
                req.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))

        reply = self.nam.post(req, QByteArray(json_data))
        retry_cb = (lambda d=data_dict: self._do_send_loco(d, is_retry=True)) if not is_retry else None
        reply.finished.connect(
            lambda r=reply, l_id=loco_id, cb=retry_cb: self._handle_loco_reply(r, l_id, cb)
        )


    @Slot(str)
    def _execute_send_msg(self, message: str):
        """Slot wrapper that calls _do_send_msg with retry enabled."""
        self._do_send_msg(message, is_retry=False)

    def _do_send_msg(self, message: str, is_retry: bool = False):
        """The generic send method, safely running on the main thread."""
        url = QUrl(f"{self.url}api/vlcb")
        
        query = QUrlQuery()
        query.addQueryItem("send", message)
        query.addQueryItem("format", "txt")
        query.addQueryItem("client_id", self.client_id)
        
        form_data = query.toString(QUrl.ComponentFormattingOption.FullyEncoded).encode("utf-8")

        req = QNetworkRequest(url)
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/x-www-form-urlencoded")

        # Adds any headers - including X-API-Key or X-CSRFToken
        for key, value in self.headers.items():
            req.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))

        reply = self.nam.post(req, QByteArray(form_data))
        retry_cb = (lambda m=message: self._do_send_msg(m, is_retry=True)) if not is_retry else None
        reply.finished.connect(lambda r=reply, cb=retry_cb: self._handle_send_response(r, cb))


    def _handle_loco_reply(self, reply: QNetworkReply, loco_id: int, retry_callback=None):
        """Processes the background network response once the server replies."""
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                if self._check_csrf_error(reply, retry_callback):
                    return
                logger.warning(f"Network error on loco POST command: {reply.errorString()}")
                return

            response_bytes = reply.readAll().data()
            try:
                response_dict = json.loads(response_bytes.decode("utf-8"))
            except Exception as e:
                logger.warning(f"Send loco returned non-JSON format: {e}")
                return

            # Pass to existing update handler
            self._handle_loco_updates(loco_id, response_dict)
            
        finally:
            reply.deleteLater()


    def _handle_loco_updates(self, loco_id, response_dict):
        """ Handles loco status changes - can be direct response to send_loco 
        requests, or could be via stream (pushed from server) """
        # Use .get() safely in case "status" is missing from a malformed response
        status = response_dict.get("status")

        # Broadcast to only send event for logging 
        event_bus.broadcast(LogEvent(self._logentry_recv_loco(response_dict)))

        match status:
            case "loco acquired":
                logger.debug(f"Loco acquired for {loco_id}")
                # Publish event to update status and apply rules
                event_bus.publish(LocoEvent('acquired', response_dict))
                
            case "acquiring":
                logger.debug(f"Acquiring received for {loco_id}")
                event_bus.publish(LocoEvent('acquiring', response_dict))
                
            case "loco update":
                if response_dict.get("loco_id") != loco_id:
                    logger.warning(f"Incorrect loco_id received from server {response_dict}")
                    return 
               
                # Pass on to loco_manager to perform update
                event_bus.publish(LocoEvent('update', response_dict))
            case _:
                logger.debug(f"Unknown response from loco api request {response_dict}")
    
    @Slot(object)
    def _execute_read(self, last_packet):
        """Executes the GET request safely on the main thread."""
        if last_packet is None:
            last_packet = -5
        else:
            last_packet += 1

        request_string = f"{self.url}api/vlcb/?read={last_packet}&format=txt"
        logger.debug(f"Reading {request_string}")

        req = QNetworkRequest(QUrl(request_string))

        for key, value in self.headers.items():
            req.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))

        reply = self.nam.get(req)
        reply.finished.connect(self._handle_read_reply)


    @Slot()
    def _handle_read_reply(self):
        """Processes the console data when the server finally replies."""
        reply = self.sender()
        if not reply:
            return
            
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                logger.warning(f"Error reading via http: {reply.errorString()}")
                return
                
            response = reply.readAll().data().decode("utf-8")
            
            if response:
                logger.debug("Read response received, emitting to UI.")
                # Push the data to the UI instead of returning it!
                self.vlcb_read_response.emit(response)
                
        finally:
            reply.deleteLater()       

    def _handle_send_response(self, reply: QNetworkReply, retry_callback=None):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                if self._check_csrf_error(reply, retry_callback):
                    return
                logger.warning(f"Network error on generic POST: {reply.errorString()}")
                return
            
            response = reply.readAll().data().decode("utf-8")
            logger.debug(f"Send response received: {response}")
        finally:
            reply.deleteLater() 

    def start_listening(self):
        """Connects to the Flask SSE stream."""
        #print ("VLCB Client - setting up stream")
        event_bus.broadcast(LogEvent( self._logentry_stream_status ("start") ))
        req = QNetworkRequest(QUrl(f"{self.url}/api/stream"))
        req.setRawHeader(b"Accept", b"text/event-stream")

        for key, value in self.headers.items():
            req.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))
        
        self.sse_reply = self.nam.get(req)
        self.sse_reply.readyRead.connect(self._on_sse_data)
        self.sse_reply.finished.connect(self._on_disconnected)

    @Slot()
    def _on_sse_data(self):
        chunk = self.sse_reply.readAll().data().decode("utf-8", errors="replace")
        self.buffer += chunk

        while "\n\n" in self.buffer:
            frame, self.buffer = self.buffer.split("\n\n", 1)
            self._route_event(frame)

    def _route_event(self, frame: str):
        """Parses incoming SSE events and pushes them to the event bus."""

        #print (f"API Handler Message received {frame}")

        event_type = "message"
        data_lines = []

        for line in frame.splitlines():
            if line.startswith("received : keepalive"):
                # Stream keepalive are ignored
                # Unlike CBUS keepalives which can be useful for debugging CBUS / loco issues
                # There is little benefit to seeing the API keep alives
                return

            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        if not data_lines:
            return

        try:
            payload = json.loads("\n".join(data_lines))
            # Add stream to payload to identify that it came from SSE event
            payload['stream'] = True
            
            # Map the SSE event to internal Event Bus
            match event_type:
                case "loco_speed":
                    loco_id = int(payload.get("loco_id", 0))
                    payload["status"] = "loco update" # Make it look like a REST response
                    self._handle_loco_updates(loco_id, payload)
                


        except ValueError:
            logger.warning("Failed to parse SSE JSON payload")



    ################################################
    # Helper functions eg. format for logging
    ################################################

    def _logentry_send_loco (self, data_dict):
        """ Format settings and description based on command type """
        cmd = data_dict.get('cmd', "")
        loco_id = data_dict.get('loco_id', "")
        # defaults in case not matched
        command = cmd       # May change string to user friendly
        settings = ""
        description = f"Unknown Loco command {command}"
        match cmd: 
            case "acquire":
                command = "Acquire"
                description = f"Acquire request for loco {loco_id}"
                # If using share etc. then could add to settings here, but that is 
                # currently handled by server
            case "set_speed":
                command = "Set Speed"
                # convert direction to word
                if data_dict.get("direction", 1) == 0:
                    direction = "Reverse"
                else:
                    direction = "Forward"
                settings = f"{direction} Speed: {data_dict.get("speed", 0)} "
                description = f"Setting loco speed for loco {loco_id}"
            case "get_status":
                command = "Status"
                description = f"Status update request for loco {loco_id}"

        log_dict = {'source': "Api",
                    'level': 5,     #Info
                    'api_direction': "o",
                    'api_type': 'Loco',
                    'api_command': command,
                    'api_device': loco_id,
                    'api_settings': settings,
                    'api_description': description}
        return log_dict

    def _logentry_recv_loco (self, data_dict):
        """ Used when receiving using either the new API or stream """
        # Is it inbound or stream - stream has that as a key
        if data_dict.get('stream'):
            io_dir = 's'
        else:
            io_dir = 'i'
        # Response does not have a command - instead a status value
        # we use that to create a face "command" reflecting the type of status update
        status = data_dict.get('status')
        loco_id = data_dict.get('loco_id', "")
        # defaults in case not matched
        command = status       # May change string to user friendly
        settings = ""
        description = f"Unknown Loco response {command}"
        match status: 
            case "loco acquired":
                command = "Acquired"
                description = f"Acquire successful for loco {loco_id}"
            case "acquiring":
                command = "Acquiring"
                description = f"Attempting acquire for loco {loco_id}"
            case "loco update":
                command = "Loco Update"
                # Typically a direction / speed change
                # convert direction to word
                if data_dict.get("direction", 1) == 0:
                    direction = "Reverse"
                else:
                    direction = "Forward"
                settings = f"{direction} Speed: {data_dict.get("speed", 0)} "
                description = f"Status update for loco {loco_id}"
            case "speed change success":
                command = "Speed changed"
            case _:
                print (f"Unknown incoming - empty log entry {data_dict}")

        log_dict = {'source': "Api",
                    'level': 5,     #Info
                    'api_direction': io_dir,
                    'api_type': 'Loco',
                    'api_command': command,
                    'api_device': loco_id,
                    'api_settings': settings,
                    'api_description': description}
        return log_dict

    def _logentry_stream_status (self, status):
        if status == "start":
            command = "Start stream"
            description = "Starting API stream"
        elif status == "disconnect":
            command = "Stream disconnect"
            description = "API stream disconnected"
        
        log_dict = {'source': "Api",
            'level': 4,     #Debug
            'api_direction': "#",
            'api_type': 'Api',
            'api_command': command,
            'api_device': "",
            'api_settings': "",
            'api_description': description}
        return log_dict