class MockVLCBClient:
    """Simple mock VLCB client for GUI testing without a live server.

    - `send(request)` returns a canned acknowledgement (or None to simulate failure).
    - `read(last_packet)` returns the next queued response string or a "Read,0,0,0" empty result.
    - `queue_response(text)` appends a raw server response (exact text `ApiHandler` expects).
    """
    def __init__(self):
        self._responses = []
        self.sent_requests = []

    def send(self, request):
        self.sent_requests.append(request)
        return "OK"

    def read(self, last_packet):
        if self._responses:
            return self._responses.pop(0)
        # No data available
        return "Read,0,0,0"

    def queue_response(self, text):
        self._responses.append(text)

    def clear(self):
        self._responses.clear()
        self.sent_requests.clear()

    # Dummy method for var
    def set_variable (self, var_name, var_value):
        pass
