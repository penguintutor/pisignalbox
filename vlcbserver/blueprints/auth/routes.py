import time
import re
import threading
from flask import current_app, flash, request, session, redirect, render_template, url_for
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
from vlcbserver.blueprints.home import home_blueprint
from vlcbserver.core.email import send_reset_email
from . import auth_blueprint

# Examples of types of request
#/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/vlcb?send=<string of send request>&format=txt
    

@auth_blueprint.route("/login", methods=['GET', 'POST'])
def login():
    """User login page using Flask-SQLAlchemy."""
    # If the user is already logged in, skip the login page
    if current_user.is_authenticated:
        return redirect(url_for('home.home'))

    # Capture next argument to redirect (success) or pass with login attempt
    next_page = request.args.get('next')

    if request.method == 'POST':
        login_input = request.form.get('username', '')
        password = request.form.get('password', '')

        ## If either username or password are blank then fail
        if (login_input != '' and password != ''):

            # Determine if the input is an email or username
            if "@" in login_input:
                # Query the hidden _email column
                user = User.query.filter_by(_email=login_input).first()
            else:
                # Convert to lowercase just in case they typed uppercase
                clean_username = login_input.lower().replace(" ", "_")
                user = User.query.filter_by(username=clean_username).first()

            # If password_hash is None then password logins disabled
            # Still gives the same password invalid message - don't tell them why
            if not user.has_password:
                flash("Invalid username or password.", "error")
                return redirect(url_for('auth.login', next=next_page))
                    
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                
                # Security Check: Ignore absolute URLs to prevent Open Redirect attacks
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('home.home')

                return redirect(next_page)
                
            flash("Invalid username or password.", "error")
            return redirect(url_for('auth.login', next=next_page))
        

    # Serve the HTML file from the template folder
    return render_template('auth/login.html')


    
@auth_blueprint.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# Self service pasword reset using email 
@auth_blueprint.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    # Check if the config file exists
    config_dir = current_app.config.get('CONFIG_DIR')
    config_path = config_dir / "mail_config.json"
    config_exists = config_path.is_file()
    
    if request.method == 'POST':
        # If get a POST request with password reset then reject
        if not config_exists:
            flash('Password reset is not enabled.', 'danger')
            return redirect(url_for('auth.login'))

        
        # Use your hidden _email column to query, since 'email' is a hybrid property
        email = request.form.get('email').strip()
        user = User.query.filter_by(_email=email).first()

        # Don't allow password reset if password login is disabled
        # ie. if password is currently None
        if user and user.has_password:
            token = user.get_reset_token()
            
            # _external=True is CRITICAL. It ensures the URL includes your full domain 
            # (e.g., https://yoursite.com/auth/reset/token) instead of just the relative path (/reset/token)
            reset_url = url_for('auth.reset_token', token=token, _external=True)
            
            # Spin up a background thread to send the email
            email_thread = threading.Thread(
                target=send_reset_email, 
                args=(config_path, user.email, reset_url),
                daemon=True  # Ensure the thread dies if the main app shuts down
            )
            email_thread.start()
            
        # ALWAYS show the same success message to prevent attackers from using 
        # this form to guess which emails are registered in the database.
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_request.html', reset_enabled=config_exists)

@auth_blueprint.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    # Verify the token is valid and hasn't expired
    user = User.verify_reset_token(token)
    
    if not user:
        flash('That is an invalid or expired token. Please try again.', 'warning')
        return redirect(url_for('auth.reset_request'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        
        # Enforce your backend length limits here before hashing
        if len(new_password) < 8 or len(new_password) > 128:
            flash('Password must be between 8 and 128 characters.', 'danger')
            return redirect(url_for('auth.reset_token', token=token))
            
        # Hash the new password and update the database
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_token.html')
