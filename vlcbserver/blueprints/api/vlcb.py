import time
import re
from flask import Blueprint, current_app, flash, request, session, redirect, render_template, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user
from markupsafe import escape
from vlcbserver.core.utils import login_required
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from strip_tags import strip_tags
import threading
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.core.models import User
from vlcbserver.core.utils import role_required, process_vlcb_logic


# Examples of types of request
#/api/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/api/vlcb?send=<string of send request>&format=txt

# No url_prefix, it is applied when registering (see __init__.py)
api_vlcb_bp = Blueprint('vlcb', __name__)


""" VLCB Api provides raw access to anything on CANbus, so needs at least
operator permission"""
@api_vlcb_bp.before_request
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
# API Routes (No CSRF, requires API Key)
# ==========================================

# Original - returns plain text response
# Updated to allow get or post
@api_vlcb_bp.route("/", methods=['GET', 'POST'], strict_slashes=False)
@login_required
def vlcb_request():
    # If JSON is sent, use that; otherwise use request.values (which covers both GET args and POST form data)
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.values

    #print(f"{request.method} received: {dict(data)}")

    # Check if it's a 'send' action
    arg_value = data.get("send")
    if arg_value:
        arg_type = "send"
    else:
        arg_type = "read"
        try:
            arg_value = int(data.get("read", 0))
        except (ValueError, TypeError):
            arg_value = 0

    # Return plain text response
    return str(escape(process_vlcb_logic(arg_type, arg_value))), 200, {'Content-Type': 'text/plain; charset=utf-8'}
