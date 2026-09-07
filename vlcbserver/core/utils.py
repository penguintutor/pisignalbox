import re
from functools import wraps
from flask import abort, request, render_template
from flask_login import current_user
from flask_login import login_required as original_login_required
from vlcbserver.vlcb_bridge import send_data, get_data
import logging, os

def role_required(*roles):
    """
    Checks if the current user has the necessary role.
    Accepts multiple roles, e.g., @role_required('admin', 'operator')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Safe check in case your ApiUser hits this and doesn't have a role attribute
            user_role = getattr(current_user, 'role', None)
            
            if user_role not in roles:
                abort(403)  # HTTP 403 Forbidden
                
            return f(*args, **kwargs)
        setattr(decorated_function, 'is_secure_route', True)
        return decorated_function
    return decorator


def login_required(func):
    """
    Wraps Flask-Login's default login_required to add our testing tag.
    """
    # Apply the standard Flask-Login protection
    decorated_view = original_login_required(func)
    
    # Add the tag so test_security.py knows it is safe
    setattr(decorated_view, 'is_secure_route', True)
    
    return decorated_view


def process_vlcb_logic():
    # If there is a send argument then it's a send
    this_arg = request.args.get('send', default='none', type=str)
    if this_arg != "none":
        valid = _validate_vlcb_request(this_arg)
        if valid:
            send_data(this_arg)
        else:
            # Print this as we want to know when developing if we are getting 
            # invalid requests - or if our regex is too strict
            print(f"routes vlcb_request - this is invalid request {this_arg}")
        # Return null data regardless of whether success or not
        # we've only added to the queue so don't know
        # Client can watch to see if it's been went from the api read
        return "0,0,0"
        
    else:
        this_arg = request.args.get('read', default=0, type=int)        
        entries = get_data(this_arg)
        if not entries:
            return ""
        return "\n".join(str(e) for e in entries)

def _validate_vlcb_request (request_string):
    """ Simple check if the request is in a recognised format
    It doesn't actual check if the command is valid, or if it's
    appropriate to send this command. """
    if not isinstance(request_string, str):
        return False
        
    # Regex pattern breakdown:
    # ^:                  - Begins with a colon
    # [a-zA-Z0-9]{2}      - Exactly 2 alphanumeric characters
    # [a-fA-F0-9]{3}      - Exactly 3 hex characters
    # [a-zA-Z0-9]         - Exactly 1 alphanumeric character
    # [a-zA-Z0-9]{2,12}   - Between 2 and 12 alphanumeric characters
    # ;$                  - Ends with a semicolon
    pattern = r'^:[a-zA-Z0-9]{2}[a-fA-F0-9]{3}[a-zA-Z0-9][a-zA-Z0-9]{2,12};$'
    
    return bool(re.match(pattern, request_string))

#@app.after_request
def log_http_request(response):
    # Determine the user identity if they are logged in
    if current_user.is_authenticated:
        user_identity = current_user.username
    else:
        user_identity = "Guest"

    # Format: IP_Address - User - METHOD /path - STATUS
    path_with_args = request.full_path.rstrip('?')
    log_message = f"{request.remote_addr} - {user_identity} - {request.method} {path_with_args} - {response.status_code}"

    # Log 4xx and 5xx errors as warnings/errors, and 2xx/3xx as info
    if response.status_code >= 400:
        logging.warning(log_message)
    else:
        logging.info(log_message)

    # You MUST return the response object in an after_request callback
    return response


#@app.app_errorhandler(403)
def forbidden_error():
    return render_template('403.html', message="You do not have permission to view this page."), 403
