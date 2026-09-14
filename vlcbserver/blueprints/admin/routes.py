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
    username = request.form.get('username')
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role') 
    
    # Fallback to match your DB default in case of a malformed request
    if not role:
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

        # Only hash and update the password if the user actually typed a new one
        if password:
            user.password_hash = generate_password_hash(password)

    # Insert New User
    else:
        # Validate required fields for new users
        if not username or not password:
            flash("Username and password are required for new users.", "error")
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
            password_hash=generate_password_hash(password)  # type: ignore
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

@admin_blueprint.route('/settings', methods=['POST'])
def settings():
    # Todo implement this
    return redirect(url_for('admin.users'))
