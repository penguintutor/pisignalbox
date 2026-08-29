from flask import Flask
from flask_wtf.csrf import CSRFProtect
import time
import logging, os
import random
import string
import secrets

# Globals for passing information between threads
# needs default settings
debug = True

# Should always run with csrf=True
# csrf_enable=False is only included for testing purposes (disables CSRF)
# debug = True (include debug messages in log - eg Testing)
# debug = False - minimum INFO messages are logged
def create_app():
   
    #if csrf_enable:
    csrf = CSRFProtect()
    app = Flask(
        __name__,
        template_folder="www"
        )
    # Create a secret_key to last whilst the program is running
    # Generates a cryptographically secure random token in hexadecimal format
    app.secret_key = secrets.token_hex(16)  # e.g., 'ca978112ca1bbdcafac231b39a23dc4d'
    csrf.init_app(app)
    register_blueprints(app)
    return app
    
#Register routes as @requests
def register_blueprints(app):
    from vlcbserver.requests import requests_blueprint
    app.register_blueprint(requests_blueprint)