import time
import re
from flask import current_app, flash, request, session, redirect, render_template, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from strip_tags import strip_tags
import threading
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.models import User
from vlcbserver.utils import role_required

from . import api_blueprint, web_blueprint


@web_blueprint.after_request
@api_blueprint.after_request
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

# ==========================================
# API Routes (No CSRF, requires API Key)
# ==========================================



# ==========================================
# Shared Routes both web_blueprint and api_blueprint
# ==========================================


@web_blueprint.route("/vlcb", methods=['GET', 'POST'])
@api_blueprint.route("/vlcb", methods=['GET', 'POST'])
@login_required
def vlcb_request():
    return _process_vlcb_logic()

# ==========================================
# Web Routes (CSRF Protected, requires Session)
# ==========================================


#/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/vlcb?send=<string of send request>&format=txt

# @web_blueprint.route("/vlcb", methods=['GET', 'POST'])
# @login_required
# def vlcb_request():
#     return process_vlcb_logic()
    

@web_blueprint.route("/", methods=['GET', 'POST'])
@web_blueprint.route("/home", methods=['GET', 'POST'])
def home():
    return render_template('index.html')
    # login_status = 'logged_in'
    # #ip_address = get_ip_address()
    # #login_status = pixelserver.auth.auth_check(ip_address, session)
    # # not allowed even if logged in
    # if login_status == "invalid":
    #     return redirect('/invalid')
    # elif login_status == "network":
    #     return render_template('index.html', user="guest", admin=False)
    # elif login_status == "logged_in":
    #     # Also check if admin - to show settings button
    #     username = session['username']
    #     if (pixelserver.auth.check_admin(username)):
    #         admin = True
    #     else:
    #         admin = False
    #     return render_template('index.html', user=session['username'], admin=admin)
    # else:   # login required
    #     return redirect('/login')

@web_blueprint.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('profile.html', hello="Profile")

@web_blueprint.app_errorhandler(403)
def forbidden_error(error):
    return render_template('403.html', message="You do not have permission to view this page."), 403

@web_blueprint.route('/admin-dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    # Only users with role='admin' can see this
    return render_template('admin.html')

@web_blueprint.route("/login", methods=['GET', 'POST'])
def login():
    """User login page using Flask-SQLAlchemy."""
    # If the user is already logged in, skip the login page
    if current_user.is_authenticated:
        return redirect(url_for('web.home'))

    # Capture next argument to redirect (success) or pass with login attempt
    next_page = request.args.get('next')

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        ## If either username or password are blank then fail
        if (username != '' and password != ''):
            
            # Query the SQLAlchemy database for the user
            user = User.query.filter_by(username=username).first()
        
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                
                # Security Check: Ignore absolute URLs to prevent Open Redirect attacks
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('web.home')

                return redirect(next_page)
                
            flash("Invalid username or password.")
            return redirect(url_for('web.login', next=next_page))

    # Serve the HTML file from the template folder
    return render_template('login.html')


    
@web_blueprint.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('web.login'))
    

# ==========================================
# Helper methods - not routes
# ==========================================

def _process_vlcb_logic():
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

