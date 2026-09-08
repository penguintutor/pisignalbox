import time
import re
from flask import current_app, flash, request, session, redirect, render_template, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user
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
from . import web_blueprint

# Examples of types of request
#/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/vlcb?send=<string of send request>&format=txt
    

# ==========================================
# Web Routes (CSRF Protected, requires Session)
# ==========================================


@web_blueprint.route("/vlcb", methods=['GET', 'POST'])
@login_required
def vlcb_request():
    return process_vlcb_logic()


@web_blueprint.route("/", methods=['GET', 'POST'])
@web_blueprint.route("/home", methods=['GET', 'POST'])
def home():
    return render_template('index.html')

@web_blueprint.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('profile.html', hello="Profile")

    
@web_blueprint.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
    

