import time
import re
from flask import current_app, flash, request, session, redirect, render_template, url_for, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from strip_tags import strip_tags
import threading
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.core.models import User, db
from vlcbserver.core.utils import role_required
from . import admin_blueprint


# Secure Admin Blueprint by default
# This means it doesn't need a @login_required / @role_required('admin')
# before each method. Note only applies to the admin blueprint
@admin_blueprint.before_request
def check_admin_access():
    # Check if the user is logged in
    if not current_user.is_authenticated:
        # Redirect to login page, passing the page they tried to access as a 'next' parameter
        return redirect(url_for('auth.login', next=request.url))
    
    # Check if the user has the admin role
    if not current_user.has_role('admin'):
        # Return a 403 Forbidden error if they are logged in but lack permissions
        abort(403)

@admin_blueprint.route('/dashboard')
def dashboard():
    # Only users with role='admin' can see this
    return render_template('admin.html')

# Todo implement
@admin_blueprint.route('/users')
def users():
    # SQLAlchemy 2.0 select query ordered alphabetically by username
    query = db.select(User).order_by(User.username.asc())
    users = db.session.execute(query).scalars().all()
# Replace this with your database or datastore query:
    # users = User.query.all()
    # users = [
    #     {
    #         "username": "admin",
    #         "fullname": "System Administrator",
    #         "email": "admin@pisignalbox.local",
    #         "role": "Admin",
    #     },
    #     {
    #         "username": "operator1",
    #         "fullname": "Signal Operator",
    #         "email": "operator@pisignalbox.local",
    #         "role": "Operator",
    #     },
    #     {
    #         "username": "guest_viewer",
    #         "fullname": "Track Monitor",
    #         "email": "guest@pisignalbox.local",
    #         "role": "Viewer",
    #     },
    # ]

    return render_template('admin-users.html', users=users)

# Todo implement
@admin_blueprint.route('/settings')
def settings():
    # Only users with role='admin' can see this
    return render_template('admin.html')
