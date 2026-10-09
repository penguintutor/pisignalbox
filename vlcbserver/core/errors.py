from flask import flash, redirect, url_for, make_response, request, render_template
from flask_wtf.csrf import CSRFError

# Import the home blueprint object
from vlcbserver.blueprints.home import home_blueprint

@home_blueprint.app_errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('Your session expired for security reasons. Please login again.', 'warning')

    # Check if the request was made by HTMX
    if request.headers.get('HX-Request'):
        # Return an empty response with the HTMX redirect header
        response = make_response()
        response.headers['HX-Redirect'] = url_for('auth.login')
        return response

    return redirect(url_for('auth.login'))

# 404 Not Found
@home_blueprint.app_errorhandler(404)
def page_not_found(e):
    if request.headers.get('HX-Request'):
        # Return 200 so HTMX completes the swap
        return """
        <div class="alert alert-warning p-2 m-0 text-center font-monospace small">
            ⚠️ Content not found.
        </div>
        """, 200
        
    # Standard browsers get the true 404 code
    return render_template('errors/404.html'), 404


# 500 Internal Server Error
@home_blueprint.app_errorhandler(500)
def internal_error(e):
    if request.headers.get('HX-Request'):
        return """
        <div class="alert alert-danger p-2 m-0 text-center font-monospace small">
            💥 Server error. Please try again.
        </div>
        """, 200
        
    return render_template('errors/500.html'), 500


# 403 Forbidden 
@home_blueprint.app_errorhandler(403)
def forbidden_error(e):
    if request.headers.get('HX-Request'):
        return """
        <div class="alert alert-danger p-2 m-0 text-center font-monospace small">
            🚫 Access denied.
        </div>
        """, 200
        
    return render_template('errors/403.html'), 403