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
from . import api_blueprint

# Examples of types of request
#/vlcb?read=<id of first data packet>&format=txt&[&end=<id last packet to retrieve]
#/vlcb?send=<string of send request>&format=txt
    

# ==========================================
# API Routes (No CSRF, requires API Key)
# ==========================================


@api_blueprint.route("/vlcb", methods=['GET', 'POST'])
@login_required
def vlcb_request():
    return process_vlcb_logic()

