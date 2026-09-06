"""
The requests blueprint creates routes for this application
This is specifically for admin requests
"""
from flask import Blueprint

# The Web Blueprint (For human HTML pages)
auth_blueprint = Blueprint(
    'auth', 
    __name__, 
    template_folder='templates',    # Template files are processed by Jinja2 - allows {{ var_name }}
    static_folder='static'         # Files in the static directory are served as is - eg. CSS / JS
    #static_url_path='/resources'   # Uses a unique URL
)

# Import routes at the bottom so they attach to the blueprints above
from . import routes