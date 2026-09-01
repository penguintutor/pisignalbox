from flask import Flask, current_app, request, jsonify, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
import time
import logging, os
import random
import string
import secrets
from .models import db, User

# Create App and enable login manager for user authentication

# The login_manager is used as a decorator for requests for login
# This allows the decorator to be used anywhere in this file.
login_manager = LoginManager()



# Callback function from LoginManager
@login_manager.request_loader
def load_user_from_request(request):
    api_key = request.headers.get('X-API-Key')
    #API key moved to DB
    #server_api_key = current_app.config.get("api_key")

    # If no api_key received then ignore request
    if not api_key:
        # Don't print due to possible false requests
        return None
    # get database user based on API key
    user = db.session.execute(
            db.select(User).filter_by(api_key=api_key)
        ).scalar_one_or_none()

    if user != None:
        return user
    else:
        # if API key included but invalid print a warning
        print ("Client connected with invalid API key")
    return None

@login_manager.user_loader
def load_user(user_id):
    # Flask-Login passes the user_id as a string from the session cookie.
    # We cast it to an int because our database primary key is an Integer.
    # db.session.get() is the modern SQLAlchemy way to fetch by primary key.
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """Routes unauthenticated traffic based on what they asked for."""
    
    # Path A: The automated script forgot its API key
    if request.path.startswith('/api/'):
        # Return a strict machine-readable HTTP 401 error
        return jsonify({"error": "Unauthorized. Missing or invalid X-API-Key."}), 401
    
    # Path B: A human tried to access /dashboard without logging in
    # Redirect them to the HTML login page, and remember where they were trying to go
    return redirect(url_for('web.login', next=request.path))



# Should always run with csrf=True
# csrf_enable=False is only included for testing purposes (disables CSRF)
# debug = True (include debug messages in log - eg Testing)
# debug = False - minimum INFO messages are logged
def create_app(config):
   
    #if csrf_enable:
    csrf = CSRFProtect()
    app = Flask(
        __name__,
        template_folder="www"
        )

    app.config.update(config)

    # Bind the SQLAlchemy object to this app instance
    db.init_app(app)

#    # If first run then create the db
#    # if they don't exist yet before processing the first request.
#    with app.app_context():
#        db.create_all()
# DB creation handled by setup_auth.py


## This can be used for debugging if required
    # @app.before_request
    # def log_raw_request():
    #     # Only print if it's hitting the API to avoid spamming the console
    #     if request.path.startswith('/api'):
    #         print("\n--- INCOMING API REQUEST ---")
    #         print(f"Path:    {request.path}")
    #         print(f"Method:  {request.method}")
    #         print(f"API Key: {request.headers.get('X-API-Key', 'MISSING')}")
    #         print("----------------------------\n")
    
    # If there is a secret_key in the config then use that
    # which will allow persistance across server restarts
    # If not then generate a dynamic one 
    secret_key = app.config.get("secret_key")
    # If secret_key is included and sufficient length then use that
    if secret_key and len(secret_key) >= 32:
        app.secret_key = secret_key
    # otherwise create a dynamic one
    else:
        # Create a secret_key to last whilst the program is running
        # Generates a cryptographically secure random token in hexadecimal format
        print("WARNING: Using a temporary dynamic secret key.\n User sessions will drop on server restart.")
        app.secret_key = secrets.token_hex(32)  

    # Initialise extensions
    csrf.init_app(app)
    login_manager.init_app(app)

    #Register routes as @requests
    from vlcbserver.requests import api_blueprint, web_blueprint
    app.register_blueprint(api_blueprint)
    app.register_blueprint(web_blueprint)

    # Exempt the API blueprint from CSRF API calls can POST to it
    # without needing a web session token
    # Only allowed where api key is used where csrf protection not required
    csrf.exempt(api_blueprint) # NOSONAR

    with app.app_context():
        db.create_all()

    return app
    

