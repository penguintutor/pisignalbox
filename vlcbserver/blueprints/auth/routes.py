import time
import re
from flask import current_app, flash, request, session, redirect, render_template, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from strip_tags import strip_tags
import threading
import logging, os
import vlcbserver
from vlcbserver.vlcb_bridge import send_data, get_data
from vlcbserver.models import User
from vlcbserver.utils import role_required
from vlcbserver.blueprints.web import api_blueprint, web_blueprint
from . import auth_blueprint

# Examples of types of request
#/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/vlcb?send=<string of send request>&format=txt
    

@auth_blueprint.route("/login", methods=['GET', 'POST'])
def login():
    """User login page using Flask-SQLAlchemy."""
    # If the user is already logged in, skip the login page
    if current_user.is_authenticated:
        return redirect(url_for('web.home'))

    # Capture next argument to redirect (success) or pass with login attempt
    next_page = request.args.get('next')

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        ## If either username or password are blank then fail
        if (username != '' and password != ''):
            
            # Query the SQLAlchemy database for the user
            user = User.query.filter_by(username=username).first()
        
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                
                # Security Check: Ignore absolute URLs to prevent Open Redirect attacks
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('web.home')

                return redirect(next_page)
                
            flash("Invalid username or password.")
            return redirect(url_for('web.login', next=next_page))

    # Serve the HTML file from the template folder
    return render_template('login.html')


    
@auth_blueprint.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('web.login'))
    
