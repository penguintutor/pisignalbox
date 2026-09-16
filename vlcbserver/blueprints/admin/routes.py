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

@admin_blueprint.route('/')
def dashboard():
    # Only users with role='admin' can see this
    return render_template('admin/index.html')

@admin_blueprint.route('/users')
def users():
    # SQLAlchemy 2.0 select query ordered alphabetically by username
    query = db.select(User).order_by(User.username.asc())
    users = db.session.execute(query).scalars().all()

    return render_template('admin/users.html', users=users)


@admin_blueprint.route('/users/save', methods=['POST'])
def save_user():
    # Retrieve form data
    original_username = request.form.get('original_username')
    raw_username = request.form.get('username')
    # Enforce username as lower_case
    username = raw_username.lower().replace(" ", "_")
    username = re.sub(r'[^a-z0-9_]', '', username)
    raw_input_name = request.form.get('fullname')
    # Just strip brackets from full name
    fullname = re.sub(r'[<>{}]', '', raw_input_name).strip()
    raw_email = request.form.get('email')
    if raw_email:
        email = clean_email(raw_email)
    else:
        email = ""
    raw_password = request.form.get('password')

    # Is a pssword supplied
    if raw_password and raw_password.strip():
        # also check lengths
        if len(raw_password) < 8:
                flash("Password is too short. Minimum 8 characters.", "error")
                return redirect(url_for('admin.users'))
        elif len(raw_password) > 128:
                flash("Password is too long. Maximum 128 characters.", "error")
                return redirect(url_for('admin.users'))
        password_hash = generate_password_hash(raw_password.strip())
    else:
        password_hash = None # API-only account
    
    role = request.form.get('role') 
    
    # Fallback to match your DB default in case of a malformed request
    if not role or role not in ROLES:
        role = 'reader'
    
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
        if len(new_password) < 8:
            flash("Password is too short", "error")
            return redirect(url_for('admin.users'))
        elif len(new_password) > 128:
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
    raw_api_key = secrets.token_hex(16)

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
    if len(new_password) < 8: 
        return jsonify({'error': 'Password is too short'}), 400
    elif len(new_password) > 128: 
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

@admin_blueprint.route('/settings', methods=['POST'])
def settings():
    # Todo implement this
    return redirect(url_for('admin.users'))

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