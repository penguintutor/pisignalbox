from flask import Blueprint, send_from_directory, jsonify, request, current_app, stream_with_context, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from pathlib import Path
import queue
from vlcbserver.core.utils import to_binary
from vlcbserver.settings import get_data_dirs
from vlcbserver.extensions import vlcb
from vlcbserver.vlcb_bridge import send_data
from vlcbserver.railway.loco import locomanager
from vlcbserver.railway.loco.locomanager import loco_manager
from vlcbserver.sse_broadcaster import announcer


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


@api_loco_bp.route('/client/function', methods=['GET', 'POST'])
def client_function():    # Takes loco_id as though basic API, but also update any web app controlled locos
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_id = data.get("loco_id") or request.values.get("loco_id")
    # func index = index (from 0) - eg. F0 = 0,
    # func value is required 
    func_index = data.get("function_index") or request.values.get("function_index", None)
    # value default to 0 = off
    func_value = data.get("function_value") or request.values.get("function_value", 0)

    # Basic initial check
    if func_index < 0 or func_index > 28:
        return jsonify({"status": "error", "message": "Function Index is out of range"})
    # Convert value to a binary 1 or 0
    try:
        func_binary = to_binary(func_value)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid function value"})
    
    # Update the loco with the function value
    return basic_set_function (loco_id, func_index, func_binary)



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
    return jsonify({"status": "speed change success", "message": "Speed change requested"})


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

def basic_set_function(loco_id, func_index, value):
    """ Sets a function signal. Sets the value to the controller
    and the controller then performs any resends 
    (eg. periodic resend if loco loses signal)
    
    If it's a trigger rather than latch then this needs 
    to be called twice. Once to set and again to unset. 
    That is handled by the client based on how long the
    button is pressed. """
    # Checks loco_ref is valid and gets the active session
    session_dict = basic_loco_to_session(loco_id)
    # If there is no valid session then return with error message
    # If session is < 1 then it's invalid - so return json data and error code
    if "session_id" not in session_dict or session_dict["session_id"] < 1:
        return jsonify(session_dict.get("message_dict")), session_dict.get("http_code")
    session_id = session_dict["session_id"] 

    all_functions = loco_manager.get_functions_basic (loco_id)
    # Check we got a valid functions and that it includes current index
    if all_functions == None or len(all_functions) < func_index:
        return jsonify({"status": "error", "message": "Functions not found"})
    # Update the all_functions with the updated value
    # Note this is a copy - update actual value in loco through
    # main thread
    all_functions[func_index] = value

    #vlcb_cmd = vlcb.loco_set_dfun (session_id, *bytes)
    # using loco_set_function - already handles the byte generation
    vlcb_cmd = vlcb.loco_set_function (session_id, func_index, all_functions)
    send_data(
        {
            'vlcb': vlcb_cmd,
            'dev_type': "loco",
            'action': "dfun",
            'session_id': session_id,
            'loco_id': loco_id,
            'func_index': func_index,
            'value': value
        }
    )
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "function send success", "message": "Function change sent"})

# # Returns bytes required for DFUN command
# # DFUN sends a block of status at a time, based on which group
# # hence the function_num is needed to determine which block to return
# # The function_status is a list with all the settings using 
# # an entry for each status
# # First byte is group (1 = F1 to F4, 2 = F5 to F8, 3 = F9 to F12)
# # 4 = F13 to 20, 5 = F21 to F27
# # Second byte is 1 bit per function - set 1 for on, 0 for off, lsb to right
# # eg. 1 = 0001, 2 = 0010
# # function = function number, on_off = 1 or 0
# # If on_off = None then return current status
# # function is always required as it only returns the related block
# def get_function_dfun_bytes (function, all_functions):
#     #print (f"Loco set_function_dfun - {function}, {on_off}, {all_functions}")
#     if function  > len (all_functions):
#         return None

#     if function <= 4:
#         byte1 = 1
#         byte2 = (0b10000 * all_functions[0] +  # fn0 is higher nibble (bit 5)
#                     0b0001 * all_functions[1] +
#                     0b0010 * all_functions[2] +
#                     0b0100 * all_functions[3] +
#                     0b1000 * all_functions[4]
#                     )
#     elif function <= 8:
#         byte1 = 2
#         byte2 = (0b0001 * all_functions[5] +
#                     0b0010 * all_functions[6] +
#                     0b0100 * all_functions[7] +
#                     0b1000 * all_functions[8]
#                     )
#     elif function <= 12:
#         byte1 = 3
#         byte2 = (0b0001 * all_functions[9] +
#                     0b0010 * all_functions[10] +
#                     0b0100 * all_functions[11] +
#                     0b1000 * all_functions[12]
#                     )
#     elif function <= 20:
#         byte1 = 4
#         byte2 = (0b0001 * all_functions[13] +
#                     0b0010 * all_functions[14] +
#                     0b0100 * all_functions[15] +
#                     0b1000 * all_functions[16] +
#                     0b10000 * all_functions[17] +
#                     0b100000 * all_functions[18] +
#                     0b1000000 * all_functions[19] +
#                     0b10000000 * all_functions[20]
#                     )
#     elif function <= 28:
#         byte1 = 5
#         byte2 = (0b0001 * all_functions[21] +
#                     0b0010 * all_functions[22] +
#                     0b0100 * all_functions[23] +
#                     0b1000 * all_functions[24] +
#                     0b10000 * all_functions[25] +
#                     0b100000 * all_functions[26] +
#                     0b1000000 * all_functions[27] +
#                     0b10000000 * all_functions[28]
#                     )
#     # Do not support above 28 using DFUN - would need to use DFNON / DFNOF instead
#     else:
#         print ("Functions above 28 are not supported")
#         return None
#     #print (f"Returning {byte1}, {byte2}")
#     return [byte1, byte2]