import time
import re
import secrets
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

@loco_blueprint.route('/')
def dashboard():
    return render_template('loco/index.html', )

