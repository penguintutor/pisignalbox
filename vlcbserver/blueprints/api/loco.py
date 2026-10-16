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



# Todo implement the loco list
@api_loco_bp.route('/', methods=['GET', 'POST'])
def get_locos():
    return jsonify({"status": "success", "data": "loco list"})



# Todo implement this
@api_loco_bp.route('/details', methods=['GET', 'POST'])
def details():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
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


# Todo implement this
@api_loco_bp.route('/speeddir', methods=['GET', 'POST'])
def speeddir():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/stop', methods=['GET', 'POST'])
def stop():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/stop_all', methods=['GET', 'POST'])
def stop_all():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/function', methods=['GET', 'POST'])
def function():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# loco_id is the shortname from he filename
@api_loco_bp.route('/acquire', methods=['GET', 'POST'])
def acquire():
    # Try JSON body first (for POST fetch requests)
    data = request.get_json(silent=True) or {}
    # Check JSON first, then fall back to request.values (covers GET)
    loco_ref = data.get("loco_ref") or request.values.get("loco_ref")
    # mode defaults to acquire if not specified (allow acquire / steal / share)
    mode = data.get("mode") or request.values.get("mode", "acquire")

    if not loco_ref:
        return jsonify({"error": "Missing loco ref"}), 400

    # Get the loco object
    loco = loco_manager.get_loco_by_ref(loco_ref)
    if not loco:
        return jsonify({"error": "Invalid loco ref"}), 400

    # If already acquired then no action required
    if loco.is_acquired():
        return jsonify({"status": "acquired"})

    # Also check if the loco is already in use / "on track"
    # Just need to check for a "inuse" as send command will put it
    # on track if not already
    if loco_manager.on_track(loco.loco_id, loco_ref) == "inuse":
        # It's in use so cannot use this loco
        return jsonify({"status": "duplicate"})
    
    #print (f"Acquiring loco {loco_ref}, {mode}")
    # Create an acquire request
    vlcb_cmd = vlcb.allocate_loco(loco.loco_id)
    send_data(
        {
            'vlcb': vlcb_cmd,
            'dev_type': "loco",
            'action': "acquire",
            'loco_id': loco.loco_id,
            'loco_ref': loco_ref
        }
    )

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


    