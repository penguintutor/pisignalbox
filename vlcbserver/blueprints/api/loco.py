from flask import Blueprint, send_from_directory, jsonify, request, current_app
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from pathlib import Path
from vlcbserver.settings import get_data_dirs
from vlcbserver.extensions import vlcb
from vlcbserver.vlcb_bridge import send_data
from vlcbserver.railway.loco import locomanager
from vlcbserver.railway.loco.locomanager import loco_manager


# No url_prefix, it is applied when registering (see __init__.py)
api_loco_bp = Blueprint('loco', __name__)

@api_loco_bp.before_request
def check_api_operator_access():
    # Check if the user is logged in
    if not current_user.is_authenticated:
        return jsonify({
            "status": "error",
            "message": "Authentication required to access this API endpoint."
        }), 401
    
    # Check if the user has operator permissions
    if not current_user.is_operator():
        return jsonify({
            "status": "error",
            "message": "Operator permission is required."
        }), 403

# ==========================================
# API loco methods
# ==========================================



@api_loco_bp.route('/', methods=['GET', 'POST'])
def get_locos():
    loco_list = loco_manager.get_list_loco_names()
    return jsonify({"status": "success", "data": loco_list})


@api_loco_bp.route('/details', methods=['GET', 'POST'])
def details():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to reque"/home/stewart/pisignalbox/guiclient/loco/ui_loco.py", line 37st.values (covers GET)
    loco_ref = data.get("loco_ref") or request.values.get("loco_ref")

    # get loco_details from_manager
    if loco_ref:
        loco_details = loco_manager.get_loco_details_dict(loco_ref)
    else:
        # Fall back if loco not found
        loco_details = {
            "name": "N/A", 
            "image_url": "/loco/image/notfound", 
            "title": "Loco Title",
            "summary": "About loco"
            }

    return jsonify(loco_details)


# Note changed to speed_dir to make it clear it's not the 
# same as speeddir used by cbus - this needs speed and direction separately
@api_loco_bp.route('/speed_dir', methods=['GET', 'POST'])
def speed_dir():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_ref = data.get("loco_ref") or request.values.get("loco_ref")
    speed_str = data.get("speed") or request.values.get("speed")
    # Convert to int and Sanitize the speed value
    speed = speed_int(speed_str)
    direction = data.get("direction") or request.values.get("direction")

    return set_speed_dir(loco_ref, speed, direction)


@api_loco_bp.route('/stop', methods=['GET', 'POST'])
def stop():
    # This is same as speeddir - but we know speed = 0
    # Use direction = forward
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_ref = data.get("loco_ref") or request.values.get("loco_ref")

    return set_speed_dir(loco_ref, 0, "forward")


# Todo implement this
@api_loco_bp.route('/stop_all', methods=['GET', 'POST'])
def stop_all():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it

    vlcb_cmd = vlcb.loco_stop_all()
    send_data(
        {
            'vlcb': vlcb_cmd,
            'dev_type': "loco",
            'action': "stop_all"
        }
    )
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/function', methods=['GET', 'POST'])
def function():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


@api_loco_bp.route('/status', methods=['GET', 'POST'])
def status():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_ref = data.get("loco_ref") or request.values.get("loco_ref")
    # Gets loco status such as session id & speed

    return get_loco_status(loco_ref)

# loco_ref is the shortname from the filename
@api_loco_bp.route('/acquire', methods=['GET', 'POST'])
def acquire():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_ref = data.get("loco_ref") or request.values.get("loco_ref")
    # mode defaults to acquire if not specified (allow acquire / steal / share)
    # Possible future - but now changed so automatically share
    #mode = data.get("mode") or request.values.get("mode", "acquire")

    if not loco_ref:
        return jsonify({"error": "Missing loco ref"}), 400

    # Get the loco object
    loco = loco_manager.get_loco_by_ref(loco_ref)
    if not loco:
        return jsonify({"error": "Invalid loco ref"}), 400

    # If already acquired then no action required
    # This is returned on subsequent requests
    if loco.is_acquired():
        return jsonify({"status": "acquired"})

    # Also check if the loco is already in use / "on track"
    # Just need to check for a "inuse" as send command will put it
    # on track if not already
    loco_status = loco_manager.on_track(loco.loco_id, loco_ref) 

    # Build the send_data request - as likely need to issue acquire
    # No vlcb string - that's only added if needed
    acquire_data = {
        'dev_type': "loco",
        'action': "acquire",
        'loco_id': loco.loco_id,
        'loco_ref': loco_ref
    }
    
    if loco_status == "inuse":
        # It's in use through web app so cannot use this loco
        return jsonify({"status": "duplicate"})
    elif loco_status == "basic":
        # if it's already acquired as a basic then we send request without vlcb to allocate internally
        if loco_manager.is_acquired_basic(loco.loco_id):
            send_data (acquire_data)

    # Reach here then it's not aquired and should send the actual vlcb acquire command

    #print (f"Acquiring loco {loco_ref}, {mode}")
    # Create an acquire request
    vlcb_cmd = vlcb.allocate_loco(loco.loco_id)
    acquire_data['vlcb'] = vlcb_cmd
    send_data(acquire_data)

    return jsonify({"status": "acquiring"})


@api_loco_bp.route('/image', methods=['GET', 'POST'])
def image():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    filename = data.get("filename") or request.values.get("filename")

    if filename:
        # Filename is local ref - but could be in any data directory
        # cycle through the directories until find one (reverse direction as 
        # later override earlier)
        for dir in reversed(get_data_dirs()):
            # Add this dir to the filename - if it exists then immediately return
            loco_dir = dir / "locos"
            full_path = loco_dir / filename
            if full_path.is_file():
                # Send from dictionary ensures that the filename doesn't perform
                # any path traversal
                return send_from_directory(loco_dir, filename)
    # Reach here - either no filename supplied, or not found, so use default
    filename = "default-loco-image.png"
    static_dir = Path(current_app.config.get('BASE_DIR')).resolve() / "static"
    return send_from_directory(static_dir, filename)




################################################
# Unmanaged Locos - no loco_ref / name - just loco_id
# uses client
# return json format - txt response to be deprecated
# ##############################################


# Acquire a basic loco
@api_loco_bp.route('/client/acquire', methods=['GET', 'POST'])
def client_acquire():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_id_str = data.get("loco_id") or request.values.get("loco_id")
    #print (f"Api loco Client acquire request {loco_id_str}")
    try:
        loco_id = int(loco_id_str)
    except Exception:
        return "Error - Invalid loco_id", 400
    # format defaults to json 
    ret_format = data.get("format") or request.values.get("format", "json")
    #print (f"Api loco client_acquire Client ID {loco_id} ")

    if not loco_id:
        #print (f"Api loco client_acquire Loco ID not found {loco_id}")
        if ret_format == "json":
            return jsonify({"error": "Missing loco ID"}), 400
        else:
            return "Error Missing Loco ID", 400

    # Does the loco object exist? If not it is created when we send later
    loco = loco_manager.get_loco_basic(loco_id)
    if loco:
        #print (f"Api loco client_acquire found loco {loco_id}")
        # If already acquired then no action required
        if loco.is_acquired():
            #print (f"Api loco client_acquire Loco ID is acquired {loco_id}")
            if ret_format=="json":
                loco_status = loco.get_status_dict()
                loco_status["status"] = "loco acquired"
                return jsonify(loco_status)    
            else: 
                return "Loco acquired"

    # Skip check for loco on track - as we can have duplicates when managed by client
    
    # Create an acquire request
    vlcb_cmd = vlcb.allocate_loco(loco_id)
    #print (f"Api loco client_acquire sending {vlcb_cmd}")
    send_data(
        {
            'vlcb': vlcb_cmd,
            'dev_type': "loco",
            'action': "acquire_basic",
            'loco_id': loco_id
        }
    )

    if ret_format == "json":
        return jsonify({"status": "acquiring", "loco_id": loco_id})
    else:
        return "Acquiring loco"


@api_loco_bp.route('/client/speed_dir', methods=['GET', 'POST'])
def client_speed_dir():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_id = data.get("loco_id") or request.values.get("loco_id")
    speed_str = data.get("speed") or request.values.get("speed")
    # Convert to int and Sanitize the speed value
    speed = speed_int(speed_str)
    direction = data.get("direction") or request.values.get("direction")

    #print (f"Api loco client_speed_dir  {loco_id} speed str {speed_str}, speed int {speed}, direction {direction}")

    return basic_set_speed_dir(loco_id, speed, direction)


@api_loco_bp.route('/client/status', methods=['GET', 'POST'])
def client_status():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_id = data.get("loco_id") or request.values.get("loco_id")
    # Gets loco status such as session id & speed

    return get_loco_status_basic(loco_id)


################################################
# helper functions
# ##############################################

# helper - avoid duplicate code as used by multiple methods
def set_speed_dir(loco_ref, speed, direction):

    # Checks loco_ref is valid and gets the active session
    session_dict = loco_ref_to_session(loco_ref)
    # If there is no valid session then return with error message
    # If session is < 1 then it's invalid - so return json data and error code
    if "session_id" not in session_dict or session_dict["session_id"] < 1:
        return jsonify(session_dict.get("message_dict")), session_dict.get("http_code")
    session_id = session_dict["session_id"] 

    #
    speeddir = to_speeddir(speed, direction)

    vlcb_cmd = vlcb.loco_speeddir(session_id, speeddir)
    send_data(
        {
            'vlcb': vlcb_cmd,
            'dev_type': "loco",
            'action': "speeddir",
            'loco_ref': loco_ref,
            'speeddir': speeddir
        }
    )
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})

def basic_set_speed_dir(loco_id, speed, direction):

    # Checks loco_ref is valid and gets the active session
    session_dict = basic_loco_to_session(loco_id)
    # If there is no valid session then return with error message
    # If session is < 1 then it's invalid - so return json data and error code
    if "session_id" not in session_dict or session_dict["session_id"] < 1:
        return jsonify(session_dict.get("message_dict")), session_dict.get("http_code")
    session_id = session_dict["session_id"] 

    speeddir = to_speeddir(speed, direction)

    vlcb_cmd = vlcb.loco_speeddir(session_id, speeddir)
    send_data(
        {
            'vlcb': vlcb_cmd,
            'dev_type': "loco",
            'action': "speeddir",
            'loco_id': loco_id,
            'speeddir': speeddir
        }
    )
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Converts speed and direction to byte for speeddir command
# speed should be int, direction is string eg. "forward" / "reverse"
# Note this takes the normalised speed input and converts to the raw byte 
# used by CBUS (which has skipped the emergency stop)
def to_speeddir (speed, dir):

    # default to forward
    direction = 1
    
    # Dir is a string - so convert to a number
    if isinstance (dir, str):
        match dir:
            case "forward":
                direction = 1
            case "reverse":
                direction = 0
            case "1":
                direction = 1
            case "0":
                direction = 0
            case _: 
                print (f"api loco - direction value not valid - stopping {dir}")
                direction = 1
                speed = 0
    elif isinstance (dir, int):
        match dir:
            case 1:
                direction = 1
            case 0:
                direction = 0
            case _:  
                print (f"api loco - direction value not valid - stopping {dir}")
                direction = 1
                speed = 0      
    # default to stop
    else:
        print (f"api loco - direction value not valid - stopping {dir}")
        direction = 1
        speed = 0

    if speed == 0:
        cbus_speed = 0
    else:
        cbus_speed = min(speed +1, 127)
    return (direction * 0x80) + cbus_speed


def speed_int(val):
    """ convert string to an int. Check it's within the allowed range
    Anything unexpected return 0"""
    try:
        value = int(val)
    except (ValueError, TypeError):
        return 0

    if value < 0:
        return 0
    if value > 126:
        return 126
    return value


def get_loco_status(loco_ref):
    # Checks loco_ref is valid and gets the active session
    session_dict = loco_ref_to_session(loco_ref)
    # If there is no valid session then return with error message
    # If session is < 1 then it's invalid - so return json data and error code
    if "session_id" not in session_dict or session_dict["session_id"] < 1:
        return jsonify(session_dict.get("message_dict")), session_dict.get("http_code")

    # No need to use .get as above would have failed if not valid
    session_id = session_dict["session_id"]
    loco = session_dict["loco"]

    return jsonify ({
        "status": "loco update",
        "loco_ref": loco_ref,
        "loco_id": loco.get_id(),
        "session_id": session_id,
        "direction": loco.get_direction(),
        "speed": loco.get_speed(),
        "message": loco.get_message(),
        "e_stop": loco.e_stop
    })


def get_loco_status_basic(loco_id):
    # Checks loco_ref is valid and gets the active session
    session_dict = basic_loco_to_session(loco_id)
    # If there is no valid session then return with error message
    # If session is < 1 then it's invalid - so return json data and error code
    if "session_id" not in session_dict or session_dict["session_id"] < 1:
        return jsonify(session_dict.get("message_dict")), session_dict.get("http_code")

    # No need to use .get as above would have failed if not valid
    session_id = session_dict["session_id"]
    loco = session_dict["loco"]

    return jsonify ({
        "status": "loco update",
        "loco_id": loco.get_id(),
        "session_id": session_id,
        "direction": loco.get_direction(),
        "speed": loco.get_speed(),
        "message": loco.get_message(),
        "e_stop": loco.e_stop
    })

def loco_ref_to_session (loco_ref):
    """ Takes a loco_ref and returns a dict with
    * session_id # always > 1
    * loco

    or if an error 
    * message_dict
    * http_code
    """
    if not loco_ref:
        return {
            "message_dict": {
                "status": "missing_loco_ref",
                "error": "Missing loco ref"
                },
            "http_code": 400
            }

    # Get the loco object
    loco = loco_manager.get_loco_by_ref(loco_ref)
    if not loco:
        return {
            "message_dict": {
                "status": "invalid_loco_ref",
                "error": "Invalid loco reference"
                },
            "http_code": 400
            }

    # Make sure we have a session - and that's needed for the command
    # Note uses a 200 as this is still a valid request but likely
    # that the session ended before the command was issued
    session = loco.get_session()
    if session == 0:
        return {
            "message_dict": {
                "status": "session_cancelled",
                "message": "Session cancelled"
                },
            "http_code": 200
            }

    # Third value is ignored If session > 0 then this is valid
    return {
        "session_id": session,
        "loco": loco
        }


def basic_loco_to_session (loco_id):
    """ Takes a loco_id and returns a dict with
    * session_id # always > 1
    * loco

    or if an error 
    * message_dict
    * http_code
    """
    if not loco_id:
        return {
            "message_dict": {
                "status": "missing_loco_id",
                "error": "Missing loco id"
                },
            "http_code": 400
            }

    # Get the loco object
    loco = loco_manager.get_loco_basic(loco_id)
    if not loco:
        return {
            "message_dict": {
                "status": "invalid_loco_id",
                "error": "Invalid loco ID"
                },
            "http_code": 400
            }

    # Make sure we have a session - and that's needed for the command
    # Note uses a 200 as this is still a valid request but likely
    # that the session ended before the command was issued
    session = loco.get_session()
    if session == 0:
        return {
            "message_dict": {
                "status": "session_cancelled",
                "message": "Session cancelled"
                },
            "http_code": 200
            }

    # Third value is ignored If session > 0 then this is valid
    return {
        "session_id": session,
        "loco": loco
        }
