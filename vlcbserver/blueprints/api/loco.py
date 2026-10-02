from flask import Blueprint, jsonify, request
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user


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

#@api_loco_bp.route('/<int:loco_id>', methods=['POST'])
#def update_loco(loco_id):
#    pass

# Todo implement this
@api_loco_bp.route('/aquire', methods=['GET', 'POST'])
def aquire():
    print ("Aquire requested")
    return jsonify({"status": "acquired"})

# Todo implement this
@api_loco_bp.route('/details', methods=['GET'])
def details():
    return jsonify({"name": "Loconame"})


# Todo implement this
@api_loco_bp.route('/speeddir', methods=['GET'])
def speeddir():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/stop', methods=['GET'])
def stop():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/stop_all', methods=['GET'])
def stop_all():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})


# Todo implement this
@api_loco_bp.route('/function', methods=['GET'])
def function():
    # Return success just means successfully sent to the controller
    # Does not guarentee the loco received it
    return jsonify({"status": "success"})