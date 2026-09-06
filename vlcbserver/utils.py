from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    Checks if the current user has the necessary role.
    Accepts multiple roles, e.g., @role_required('admin', 'operator')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Safe check in case your ApiUser hits this and doesn't have a role attribute
            user_role = getattr(current_user, 'role', None)
            
            if user_role not in roles:
                abort(403)  # HTTP 403 Forbidden
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator