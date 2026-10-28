
import queue
from flask import Blueprint, Response, stream_with_context
from vlcbserver.sse_broadcaster import SSEAnnouncer, announcer


################################################
# Shared SSE Stream - use for real-time response
# back to the client / web browser
# ##############################################

api_stream_bp = Blueprint('stream', __name__)

@api_stream_bp.route("/stream", methods=['GET'])
def sse_stream():
    def event_generator():
        client_queue = announcer.listen()
        try:
            # (Optional) Grab state_lock briefly here just to read the 
            # current speeds and send them as the initial connection message
            
            while True:
                try:
                    msg = client_queue.get(timeout=10.0)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            announcer.remove(client_queue)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    }
    return Response(stream_with_context(event_generator()), headers=headers)
