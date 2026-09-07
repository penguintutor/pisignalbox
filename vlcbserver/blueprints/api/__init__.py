"""
The requests blueprint creates routes for this application
There is a separate blueprint for api requests (ie. client)
or web requests
"""
from flask import Blueprint

# The API Blueprint (For the client app or other clients)
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

# Import routes at the bottom so they attach to the blueprints above
from . import routes