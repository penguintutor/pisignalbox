from flask import flash, redirect, url_for
from flask_wtf.csrf import CSRFError

# Import the home blueprint object
from vlcbserver.blueprints.home import home_blueprint

@home_blueprint.app_errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('Your session expired for security reasons. Please try again.', 'warning')
    return redirect(url_for('auth.login'))