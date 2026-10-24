import time
import re
import secrets
import hashlib
import json
from flask import current_app, flash, request, session, redirect, render_template, url_for, abort, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from strip_tags import strip_tags
from email_validator import validate_email, EmailNotValidError
import threading
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.core.models import User, db
from vlcbserver.core.utils import role_required
from vlcbserver.constants import ROLES
from vlcbserver.railway.loco import locomanager
from vlcbserver.railway.loco.locomanager import loco_manager
from . import loco_blueprint


# Secure Admin Blueprint by default
# This means it doesn't need a @login_required / @role_required('operator')
# before each method. Note only applies to the loco blueprint
@loco_blueprint.before_request
def check_operator_access():
    # Check if the user is logged in
    if not current_user.is_authenticated:
        # Redirect to login page, passing the page they tried to access as a 'next' parameter
        return redirect(url_for('auth.login', next=request.url))
    
    # Check if the user has the operator permissions
    if not current_user.is_operator():
        # Redirect to home page with permission error message
        flash ("<p>You require operator permission to be able to access this feature.</p><p>Please contact an administrator to request additional permissions.</p>")
        return redirect(url_for('home.index'))

# Currently the default page is straight to the controller
@loco_blueprint.route('/')
def dashboard():
    locos = loco_manager.get_list_loco_names()
    return render_template('loco/controller.html', locomotives=locos)



""" Display - holds hash of page sent to only refresh when there are changes """
def get_loco_context():
    """Fetches loco lists and calculates a deterministic state hash."""
    available_locos = loco_manager.get_locos_status_web()

    api_locos = loco_manager.get_locos_status_basic()

    # Convert to JSON string to hash the current state
    # (If using objects/dataclasses, convert to dicts or tuples first)
    state_str = json.dumps({"avail": available_locos, "api": api_locos}, sort_keys=True)
    # The hash is just used to check whether to refresh the page - not for security
    state_hash = hashlib.md5(state_str.encode('utf-8'), usedforsecurity=False).hexdigest()

    return {
        "available_locos": available_locos,
        "api_locos": api_locos,
        "state_hash": state_hash
    }



@loco_blueprint.route('/displaylocos')
def list_locos():
    """Initial full page load."""
    context = get_loco_context()
    return render_template('loco/locos.html', **context)


@loco_blueprint.route('/refreshlocos')
def refresh_locos():
    """HTMX polling and manual refresh endpoint."""
    context = get_loco_context()
    
    # Compare client's current DOM hash with the server's current state hash
    client_hash = request.args.get('state_hash')
    if client_hash and client_hash == context['state_hash']:
        return '', 204  # No changes -> HTMX leaves DOM completely untouched

    return render_template('loco/locos_display.html', **context)

