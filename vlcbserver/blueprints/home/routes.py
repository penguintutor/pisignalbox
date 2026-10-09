import time
import re
import secrets
from flask import current_app, flash, request, session, redirect, render_template, url_for, jsonify
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

# Replaced by API
#@home_blueprint.route("/vlcb", methods=['GET', 'POST'])
#@login_required
#def vlcb_request():
#    return process_vlcb_logic()


# Home page does not require authentication
@home_blueprint.route("/", methods=['GET', 'POST'])
@home_blueprint.route("/home", methods=['GET', 'POST'])
def home():
    return render_template('home/index.html', user=current_user)



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
    print ("edit profile")
    return render_template('home/profile/details_form.html', user=current_user)

# Handles both the 'Cancel' button (GET) and 'Save' button (POST)
@home_blueprint.route('/profile/details', methods=['GET', 'POST'])
@login_required
def view_save_profile():
    print ("view save profile")
    if request.method == 'POST':

        ## Handle email address
        new_email = request.form.get('email', '').strip() or None
        # First check if it's not changing as we can then just use the current details without further checks
        if new_email and new_email == current_user.email:
            checked_email = current_user.email
        # Validation: Check if email is changing AND if it's already taken
        elif new_email:
            # Make sure max length not exceeded
            if len(new_email) > User.MAX_LEN_EMAIL:
                flash (f"Email address is too long. Maximum of {User.MAX_LEN_EMAIL} characters.", "danger")
                return render_template('home/profile/details_form.html', user=current_user)
            # validate using validator
            try:
                # Validates syntax and normalizes the email
                valid = validate_email(new_email, check_deliverability=False)
                checked_email = valid.normalized
            except EmailNotValidError:
                flash ("Invalid email address provided.", "danger")
                return render_template('home/profile/details_form.html', user=current_user)
            existing_user = User.query.filter_by(_email=checked_email).first()
            if existing_user:
                flash ("That email address is already in use.", "danger")
                return render_template('home/profile/details_form.html', user=current_user)
        # Whilst email can be blank when setup by admin 
        # Don't allow email to be blank after a profile edit
        else:
            flash ("Email address is required.", "danger")
            return render_template('home/profile/details_form.html', user=current_user)
        
        # Update Full name
        # Restricts to MAX_LEN_FULLNAME - this is handled by html5 validation already
        raw_input_name = request.form.get('full_name', '').strip()
        if len(raw_input_name) > User.MAX_LEN_FULLNAME:
            flash (f"Full name is too long. Maximum of {User.MAX_LEN_FULLNAME} characters.", "danger")
            return render_template('home/profile/details_form.html', user=current_user)
        full_name = re.sub(r'[<>{}]', '', raw_input_name).strip()
        current_user.full_name = full_name

        raw_input_short_name = request.form.get('short_name', '').strip()
        if len(raw_input_short_name) > User.MAX_LEN_SHORTNAME:
            flash (f"Short name is too long. Maximum of {User.MAX_LEN_SHORTNAME} characters.", "danger")
            return render_template('home/profile/details_form.html', user=current_user)
        short_name = re.sub(r'[<>{}]', '', raw_input_short_name).strip()
        current_user.short_name = short_name
        current_user.email = checked_email

        try:
            db.session.commit()
        except IntegrityError:
            print ("Fail to update - roll back change")
            db.session.rollback()
            flash ("A database error occurred saving your details.", "danger")
            return render_template('home/profile/details_form.html', user=current_user)

    # Returns the read-only view on GET or successful POST
    return render_template('home/profile/details_display.html', user=current_user)

# Allows user to change their own password
@home_blueprint.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify the current password is correct
        if not check_password_hash(current_user.password_hash, current_password):
            flash('Incorrect current password.', 'danger')
            return redirect(url_for('home.change_password'))

        # Make sure not trying to reuse existing password
        if new_password == current_password:
            flash('Existing password not allowed. Choose a new password.', 'danger')
            return redirect(url_for('home.change_password'))
        
        # Ensure new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('home.change_password'))

        # Check password meets requirements
        # check length
        if len(new_password) < User.MIN_LEN_PASSWORD:
                flash(f"Password is too short. Minimum {User.MIN_LEN_PASSWORD} characters.", "error")
                return redirect(url_for('home.change_password'))
        elif len(new_password) > User.MAX_LEN_PASSWORD:
                flash(f"Password is too long. Maximum {User.MAX_LEN_PASSWORD} characters.", "error")
                return redirect(url_for('home.change_password'))
        # NOTE could add additional checks for requirements here
        # already "enforced" by UI, but user could bypass
        # would involve deliberately trying to bypass security
        # just to enter a weaker password

        password_hash = generate_password_hash(new_password.strip())

        # Update the password
        current_user.password_hash = password_hash

        # Save to db
        db.session.commit()
        
        flash('Your password has been successfully updated.', 'success')
        # Adjust 'home.profile' to the name of the route that renders the profile card
        return redirect(url_for('home.profile')) 

    # Handle GET request: render the form
    return render_template('home/profile/change_password.html')

# Returns the API key page for user
@home_blueprint.route('/profile/new_api_key', methods=['GET', 'POST'])
@login_required
def new_api_key():
    return render_template('home/profile/generate_api_key.html', user=current_user)

# Changes the API key via ajax
@home_blueprint.route('/profile/generate-api-key', methods=['POST'])
@login_required
def generate_api_key():
    # Ensure the user already has API access enabled by an admin
    # Adjust this check based on how your User model defines 'has_api_key'
    if not current_user.has_api_key: 
        return jsonify({'error': 'API authentication is not enabled for your account. Please contact an admin.'}), 403

    # Generate a cryptographically secure 32-character hex key
    raw_api_key = secrets.token_hex(User.REQ_LEN_APIKEY)

    # Hash it using your model's static method
    current_user.api_key = User.api_to_hash(raw_api_key)

    # Save to the database
    try:
        db.session.commit()
        # Return the plaintext key ONCE so the JS can display it for copying
        return jsonify({'api_key': raw_api_key}), 200
    except Exception as e:
        db.session.rollback()
        # Log the error securely
        print(f"Error generating API key for {current_user.username}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500