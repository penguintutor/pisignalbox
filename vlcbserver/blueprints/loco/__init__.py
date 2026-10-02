"""
The requests blueprint creates routes for this application
There is a separate blueprint for api requests (ie. client)
or web requests
"""
from flask import Blueprint
from vlcbserver.constants import ROLES

# The Web Blueprint (For human HTML pages)
loco_blueprint = Blueprint(
    'loco', 
    __name__, 
    template_folder='templates',    # Template files are processed by Jinja2 - allows {{ var_name }}
    static_folder='static',         # Files in the static directory are served as is - eg. CSS / JS
    url_prefix='/loco'
)

# Import routes at the bottom so they attach to the blueprints above
from . import routes