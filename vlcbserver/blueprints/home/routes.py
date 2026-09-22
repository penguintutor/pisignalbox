import time
import re
from flask import current_app, flash, request, session, redirect, render_template, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user
from vlcbserver.core.utils import login_required
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError
from strip_tags import strip_tags
import threading
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.core.models import User, db
from vlcbserver.core.utils import role_required, process_vlcb_logic
from . import home_blueprint

# Examples of types of request
#/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/vlcb?send=<string of send request>&format=txt
    

# ==========================================
# Web Routes (CSRF Protected, requires Session)
# ==========================================


@home_blueprint.route("/vlcb", methods=['GET', 'POST'])
@login_required
def vlcb_request():
    return process_vlcb_logic()


# Home page does not require authentication
@home_blueprint.route("/", methods=['GET', 'POST'])
@home_blueprint.route("/home", methods=['GET', 'POST'])
def home():
    return render_template('home/index.html')

    
@home_blueprint.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
    

##### Profile Page ######

# Main profile page
@home_blueprint.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('home/profile.html', user=current_user)

# Provides the form so the user can edit
@home_blueprint.route("/profile/edit", methods=['GET', 'POST'])
@login_required
def edit_profile():
    return render_template('home/profile/details_form.html', user=current_user)

# Handles both the 'Cancel' button (GET) and 'Save' button (POST)
@home_blueprint.route('/profile/details', methods=['GET', 'POST'])
@login_required
def view_save_profile():
    if request.method == 'POST':
        new_email = request.form.get('email', '').strip() or None
        
        # Validation: Check if email is changing AND if it's already taken
        if new_email and new_email != current_user.email:
            # validate using validator
            try:
                # Validates syntax and normalizes the email
                valid = validate_email(new_email, check_deliverability=False)
                checked_email = valid.normalized
            except EmailNotValidError:
                error_msg = "Invalid email address provided."
                return render_template('home/profile/details_form.html', 
                    user=current_user, 
                    error=error_msg)
            existing_user = User.query.filter_by(_email=checked_email).first()
            if existing_user:
                error_msg = "That email address is already in use."
                return render_template('home/profile/details_form.html', 
                    user=current_user, 
                    error=error_msg)
        # Whilst email can be blank when setup by admin 
        # Don't allow email to be blank after a profile edit
        else:
            error_msg = "Email address is required."
            return render_template('home/profile/details_form.html', 
                user=current_user, 
                error=error_msg)
        # Update properties
        raw_input_name = request.form.get('full_name', '').strip()
        full_name = re.sub(r'[<>{}]', '', raw_input_name).strip()
        current_user.full_name = full_name
        raw_input_short_name = request.form.get('short_name', '').strip()
        short_name = re.sub(r'[<>{}]', '', raw_input_short_name).strip()
        current_user.short_name = short_name
        current_user.email = checked_email

        try:
            db.session.commit()
        except IntegrityError:
            print ("Fail to update - reoll back change")
            db.session.rollback()
            return render_template('home/profile/details_form.html', 
                user=current_user, 
                error="A database error occurred saving your details.")

    # Returns the read-only view on GET or successful POST
    return render_template('home/profile/details_display.html', user=current_user)

# Todo - not yet implemented
@home_blueprint.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    return render_template('home/profile/details_display.html', user=current_user)

# Todo - not yet implemented
@home_blueprint.route('/profile/new_api_key', methods=['GET', 'POST'])
@login_required
def generate_api_key():
    # Todo check that there is already an API key - can only update
    # if already enabled by an admin user
    return render_template('home/profile/details_display.html', user=current_user)
