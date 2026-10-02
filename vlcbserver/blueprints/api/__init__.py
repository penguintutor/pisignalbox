"""
The requests blueprint creates routes for this application
There is a separate blueprint for api requests (ie. client)
or web requests
"""
from flask import Blueprint, request, jsonify
from flask_wtf.csrf import validate_csrf, CSRFError
from .vlcb import api_vlcb_bp
from .loco import api_loco_bp

# The API Blueprint (For the client app or other clients)
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

api_blueprint.register_blueprint(api_vlcb_bp, url_prefix='/vlcb')
api_blueprint.register_blueprint(api_loco_bp, url_prefix='/loco')

""" The before request will apply to the sub blueprints """
@api_blueprint.before_request
def enforce_csrf_for_sessions():
    # Skip CSRF check for safe read-only methods
    if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
        return

    # If an API key is present, we trust it (machine-to-machine needs no CSRF)
    if request.headers.get('X-API-Key'):
        return

    # Otherwise, this is a web session. We MUST verify the CSRF token.
    csrf_token = request.headers.get('X-CSRFToken')
    
    if not csrf_token:
        return jsonify({"error": "CSRF token missing"}), 400
    
    try:
        validate_csrf(csrf_token)
    except CSRFError:
        return jsonify({"error": "CSRF token invalid or expired"}), 400