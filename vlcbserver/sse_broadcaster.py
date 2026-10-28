import queue
import threading
import json


class SSEAnnouncer:
    """Thread-safe megaphone for pushing SSE events to clients."""
    def __init__(self):
        self._listeners: list[queue.Queue] = []
        self._lock = threading.Lock()  # This lock ONLY protects the listeners list

    def listen(self) -> queue.Queue:
        client_queue = queue.Queue(maxsize=30)
        with self._lock:
            self._listeners.append(client_queue)
        return client_queue

    def remove(self, client_queue: queue.Queue):
        with self._lock:
            if client_queue in self._listeners:
                self._listeners.remove(client_queue)

    def announce(self, event_type: str, data: dict):
        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        with self._lock:
            for q in self._listeners:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    self._listeners.remove(q)

# The single shared megaphone everyone will use
announcer = SSEAnnouncer()