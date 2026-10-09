import time
import re
import os, pwd
import secrets
from flask import current_app, flash, request, session, redirect, render_template, url_for, abort, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from strip_tags import strip_tags
from email_validator import validate_email, EmailNotValidError
import threading
from pathlib import Path
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.core.models import User, db
from vlcbserver.core.utils import role_required
from vlcbserver.constants import ROLES
from vlcbserver.settings import update_server_settings
from . import admin_blueprint


# ==========================================
# Enforce admin only
# ==========================================

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


# ==========================================
# User admin (default for admin)
# ==========================================

@admin_blueprint.route('/')
def dashboard():
    # Only users with role='admin' can see this
    return render_template('admin/index.html')

""" Debug - allows an admin to see what user the system is running under"""
@admin_blueprint.route("/debug-user")
def debug_user():
    uid = os.geteuid()
    return f"Running as: {pwd.getpwuid(uid).pw_name} (UID: {uid})"

@admin_blueprint.route('/users')
def users():
    # SQLAlchemy 2.0 select query ordered alphabetically by username
    query = db.select(User).order_by(User.username.asc())
    users = db.session.execute(query).scalars().all()

    return render_template('admin/users.html', users=users)


# SonarQube disabled for this function due to the cognitive complexity
# Uses additional validation checks for each variable
@admin_blueprint.route('/users/save', methods=['POST'])
def save_user():    # NOSONAR
    # Retrieve form data
    original_username = request.form.get('original_username')
    raw_username = request.form.get('username')
    # Enforce username as lower_case
    username = raw_username.lower().replace(" ", "_")
    username = re.sub(r'[^a-z0-9_]', '', username)
    if len(username) > User.MAX_LEN_USERNAME:
        flash(f"Username is too long. Maximum {User.MAX_LEN_USERNAME} characters.", "error")
        return redirect(url_for('admin.users'))

    raw_input_name = request.form.get('fullname')
    # Reject full name is too long
    if len(raw_input_name) > User.MAX_LEN_FULLNAME:
            flash(f"Full name is too long. Maximum {User.MAX_LEN_FULLNAME} characters.", "error")
            return redirect(url_for('admin.users'))
    # Just strip brackets from full name
    fullname = re.sub(r'[<>{}]', '', raw_input_name).strip()

    raw_email = request.form.get('email')
    if len(raw_email) > User.MAX_LEN_EMAIL:
                flash(f"Email address is too long. Maximum {User.MAX_LEN_EMAIL} characters.", "error")
                return redirect(url_for('admin.users'))
    if raw_email:
        email = clean_email(raw_email)
    else:
        email = ""
    raw_password = request.form.get('password')

    # Is a password supplied
    if raw_password and raw_password.strip():
        # also check lengths
        if len(raw_password) < User.MIN_LEN_PASSWORD:
                flash(f"Password is too short. Minimum {User.MIN_LEN_PASSWORD} characters.", "error")
                return redirect(url_for('admin.users'))
        elif len(raw_password) > User.MAX_LEN_PASSWORD:
                flash(f"Password is too long. Maximum {User.MAX_LEN_PASSWORD} characters.", "error")
                return redirect(url_for('admin.users'))
        password_hash = generate_password_hash(raw_password.strip())
    else:
        password_hash = None # API-only account
    
    role = request.form.get('role') 
    
    # Fallback to match your DB default in case of a malformed request
    if not role or role not in ROLES:
        role = 'reader'

    # This adds to the cognitive complexity, but again prefer to keep it 
    # simple rather than trying to combine add / update into a single code block
    # Update Existing User
    if original_username:
        user = User.query.filter_by(username=original_username).first()
        
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('admin.users')) # Replace with your actual redirect route
            
        # Update fields
        user.full_name = fullname
        user.email = email
        user.role = role
        
        # If the HTML removes 'readonly' to allow username changes, check for collisions
        if username and username != original_username:
            existing = User.query.filter_by(username=username).first()
            if existing:
                flash("Username is already taken.", "error")
                return redirect(url_for('admin.users'))
            user.username = username

        # Uses the new password hash - which is password or NOne
        user.password_hash = password_hash

    # Insert New User
    else:
        # Validate required fields for new users
        if not username:
            flash("Username is required for new users.", "error")
            return redirect(url_for('admin.users'))
            
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash("Username is already taken.", "error")
            return redirect(url_for('admin.users'))
            
        # Create new user instance
        user = User(
            username=username,      # type: ignore
            full_name=fullname,     # type: ignore
            email=email,            # type: ignore
            role=role,              # type: ignore
            password_hash=password_hash  # type: ignore
        ) 
        db.session.add(user)

    # Commit to Database
    try:
        db.session.commit()
        flash("User saved successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while saving to the database.", "error")
        print(f"Database error: {e}") # For debugging

    return redirect(url_for('admin.users'))

@admin_blueprint.route('/users/delete', methods=['POST'])
def delete_user():
    # Retrieve the username of the user to delete
    username = request.form.get('username')
    
    if not username:
        flash("No username provided.", "error")
        return redirect(url_for('admin.users')) # Replace with your actual redirect route
        
    # Find the user in the database
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('admin.users'))
        
    # Prevent admins from deleting themselves
    # current_user = ... # (logic to get currently logged in user)
    if current_user.username == user.username:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('admin.users'))

    # Delete the user and commit
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{username}' was successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting the user.", "error")
        print(f"Database error: {e}") # For debugging

    return redirect(url_for('admin.users'))

@admin_blueprint.route('/save_password', methods=['POST'])
def save_password():  
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    revoke_web = request.form.get('revoke_web') == 'true'

    user = User.query.filter_by(username=username).first()
    if not user:
        flash(f"Error: User '{username}' not found.", "danger")
        return redirect(url_for('admin.users'))

    # Handle revocation
    if revoke_web:
        user.password_hash = None
        flash(f"Web login disabled for {username}.", "info")
    
    # Handle password creation / update
    elif new_password and new_password.strip():
        # Check that the password meets the min / max length
        # This should be blocked by JavaScript already
        if len(new_password) < User.MIN_LEN_PASSWORD:
            flash("Password is too short", "error")
            return redirect(url_for('admin.users'))
        elif len(new_password) > User.MAX_LEN_PASSWORD:
            flash("Password is too long", "error")
            return redirect(url_for('admin.users'))
        # Reach here then password has passed the basic length checks - create hash
        user.password_hash = generate_password_hash(new_password.strip())
        flash(f"Password successfully updated for {username}.", "success")
    else:
        flash("No password provided; changes not applied to web login.", "warning")
        return redirect(url_for('admin.users'))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Database error saving password: {e}")
        flash("An error occurred while saving to the database.", "danger")

    return redirect(url_for('admin.users'))

@admin_blueprint.route('/save_key', methods=['POST'])
def save_key():
    username = request.form.get('username')
    new_api_key = request.form.get('api_key')

    user = User.query.filter_by(username=username).first()
    if not user:
        flash(f"Error: User '{username}' not found.", "danger")
        return redirect(url_for('admin.users'))

    # If the text box has a key, hash it via the model's static method
    if new_api_key and new_api_key.strip():
        user.api_key = User.api_to_hash(new_api_key.strip())
        flash(f"API key successfully updated for {username}.", "success")
    else:
        # Cleared text box - remove API access
        user.api_key = None
        flash(f"API key removed for {username}. Access revoked.", "info")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Database error saving API key: {e}")
        flash("An error occurred while saving to the database.", "danger")

    return redirect(url_for('admin.users'))

""" api functions used for AJAX real time updates """
@admin_blueprint.route('/api/generate-key', methods=['POST'])
def api_generate_key():
    data = request.get_json()
    username = data.get('username')

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Generate a cryptographically secure 32-character hex key
    raw_api_key = secrets.token_hex(User.REQ_LEN_APIKEY)

    # Hash it using your model's static method and save to the DB
    user.api_key = User.api_to_hash(raw_api_key)

    try:
        db.session.commit()
        # Return the plaintext key ONCE so the JS can display it for copying
        return jsonify({'api_key': raw_api_key}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error generating API key: {e}")
        return jsonify({'error': 'Database error occurred'}), 500


@admin_blueprint.route('/api/revoke-key', methods=['POST'])
def api_revoke_key():
    data = request.get_json()
    username = data.get('username')

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Revoke access by wiping the hash
    user.api_key = None

    try:
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error revoking API key: {e}")
        return jsonify({'error': 'Database error occurred'}), 500

@admin_blueprint.route('/api/save-password', methods=['POST'])
def api_save_password():
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('new_password')

    if not new_password or not new_password.strip():
        return jsonify({'error': 'No password provided'}), 400

    # Checks for minimum password length
    if len(new_password) < User.MIN_LEN_PASSWORD: 
        return jsonify({'error': 'Password is too short'}), 400
    elif len(new_password) > User.MAX_LEN_PASSWORD: 
        return jsonify({'error': 'Password is too long'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.password_hash = generate_password_hash(new_password.strip())

    try:
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error saving password: {e}")
        return jsonify({'error': 'Database error occurred'}), 500


@admin_blueprint.route('/api/revoke-password', methods=['POST'])
def api_revoke_password():
    data = request.get_json()
    username = data.get('username')

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.password_hash = None

    try:
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error revoking web access: {e}")
        return jsonify({'error': 'Database error occurred'}), 500



# ==========================================
# Settings - eg. config file location
# ==========================================

@admin_blueprint.route('/settings', methods=['GET'])
def settings():
    return render_template('admin/settings.html', settings=get_app_settings())

@admin_blueprint.route('/settings/edit', methods=['GET', 'POST'])
def edit_settings():
    app_settings = get_app_settings()

    return render_template('admin/settings_form.html', settings=app_settings)

@admin_blueprint.route('/settings/details', methods=['POST', 'GET'])
def view_save_settings():
    app_settings = get_app_settings()
    # If post then it's a save request
    if request.method == 'POST':
        # Handle the toggle checkbox
        app_settings['use_gui_settings'] = 'use_gui_settings' in request.form
        app_settings['gui_settings_path'] = request.form.get('gui_settings_path', '')
        app_settings['use_server_settings'] = 'use_server_settings' in request.form

        #print (f"Add dir {current_app.config.get('BASE_DIR')} type {type(current_app.config.get('BASE_DIR'))}")

        # Check for a valid path
        # If not valid then doesn't allow save
        # Note that the browser is relative based but may includes a / - if that's the case then strip it
        #full_path = current_app.config.get('BASE_DIR') / app_settings['gui_settings_path'].lstrip('/')
        full_path, relative_path = resolve_directory_paths(current_app.config.get('BASE_DIR'), app_settings['gui_settings_path'])
        if not full_path.is_dir():
            #print (f"Invalid path {full_path}")
            flash("Invalid path entered. It must be relative to the install directory. Use the browser to find a suitable path", "danger")
            return render_template('admin/settings_form.html', settings=app_settings)
        # replace the relative_path with our known safe relative path
        app_settings['gui_settings_path'] = str(relative_path)

        # Update current_app settings and save 
        success = update_server_settings(app_settings)
        if success == False:
            flash("Error trying to save the server config file - updates will not persist. See the setup instructions for permissions.", "danger")
            return render_template('admin/settings_form.html', settings=app_settings)
    
    return render_template('admin/settings_display.html', settings=app_settings)


@admin_blueprint.route('/browse-dir', methods=['GET'])
def browse_dir():
    """Secure, jail-rooted directory browser returning an HTMX fragment."""
    base_dir = Path(current_app.config.get('BASE_DIR')).resolve()
    
    req_path = request.args.get('path', '').strip('/')
    target_path = (base_dir / req_path).resolve()
    
    if not target_path.is_relative_to(base_dir):
        abort(403) 
        
    try:
        dirs = [d.name for d in target_path.iterdir() if d.is_dir()]
        dirs.sort()
    except Exception:
        dirs = []
        
    # FIX: Ensure parent_path returns '' instead of '.' for first-level directories
    # to prevent CSS selector syntax errors in HTMX targets.
    parent_path = str(Path(req_path).parent) if req_path else ''
    if parent_path == '.':
        parent_path = ''
    
    return render_template('admin/_dir_browser.html', 
                           current_rel_path=req_path, 
                           parent_path=parent_path, 
                           dirs=dirs,
                           is_root=(target_path == base_dir))


# *******************
# Helper functions 
# *******************

def clean_email(raw_email):
    try:
        # Validates syntax and normalizes the email
        valid = validate_email(raw_email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError:
        # Handle the error (e.g., flash a message to the user)
        flash("Email included invalid characters, left blank", "warning")
        return ""

# Creates a dict by pulling the relevant details from the current_app config
# Instead of having all settings - only provides the ones relevant to these settings
def get_app_settings():
    app_settings = {}
    # GUI settings is default to off (ie. until configured)
    app_settings['use_gui_settings'] = current_app.config.get("use_gui_settings", False)
    # Keep the path from the config - even if disabled (so it exists when enabled)
    app_settings['gui_settings_path'] = current_app.config.get("gui_settings_path", "")
    # Server settings defaults to True - and if GUI settings is set to False then this will become true
    if app_settings['use_gui_settings'] == False:
        app_settings['use_server_settings'] = True
    else:
        app_settings['use_server_settings'] = current_app.config.get("use_server_settings", True)
    return app_settings

""" Join a path safely to the base directory 
Allows beginning / (stipped) and full path (stripped before joining)"""
def resolve_directory_paths(base_path: Path, requested_path_str: str) -> tuple[Path, Path]:
    base_str = str(base_path)
    
    # Strip the base path if it was passed in completely
    if requested_path_str == base_str or requested_path_str.startswith(base_str + '/'):
        requested_path_str = requested_path_str[len(base_str):]
        
    # Join and resolve() to calculate the true absolute path (evaluates any '../')
    full_path = (base_path / requested_path_str.lstrip('/')).resolve()
    
    # Security check: Ensure the resolved path didn't escape the base directory
    if not full_path.is_relative_to(base_path):
        raise ValueError("Security Error: Path traversal attempt outside base directory.")
        
    # Calculate the clean relative path for your database/storage
    relative_path = full_path.relative_to(base_path)
    
    return full_path, relative_path