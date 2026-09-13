"""
The requests blueprint creates routes for this application
There is a separate blueprint for api requests (ie. client)
or web requests
"""
from flask import Blueprint

# The Web Blueprint (For human HTML pages)
home_blueprint = Blueprint(
    'home', 
    __name__, 
    template_folder='templates',    # Template files are processed by Jinja2 - allows {{ var_name }}
    static_folder='static'         # Files in the static directory are served as is - eg. CSS / JS
    #static_url_path='/resources'   # Uses a unique URL
)

# Import routes at the bottom so they attach to the blueprints above
from . import routes