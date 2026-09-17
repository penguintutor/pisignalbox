# tests/test_security.py

def test_all_routes_are_secure(app):
    """
    Ensures every route is either explicitly public, protected by a blueprint 
    before_request, or decorated with a security tag.
    """
    
    # Blueprints secured natively via before_request
    SECURE_BLUEPRINTS = ['admin']
    
    # Endpoints that are intentionally open to the public
    PUBLIC_ENDPOINTS = [
        'auth.login', 
        'auth.register', 
        'auth.logout',
        'auth.reset_request',
        'auth.reset_token',
        'home.home', 
        'static'  # Flask's default static file handler
    ]

    # Iterate over every route registered in the application
    for endpoint, view_func in app.view_functions.items():

        # Skip any static file handlers
        if endpoint == 'static' or endpoint.endswith('static'):
            continue
        
        # Skip explicitly public endpoints
        if endpoint in PUBLIC_ENDPOINTS:
            continue
            
        # Check if the route belongs to a blueprint secured by before_request
        blueprint_name = endpoint.split('.')[0] if '.' in endpoint else None
        if blueprint_name in SECURE_BLUEPRINTS:
            continue
            
        # For all remaining routes, check if our security tag was applied by the decorator
        is_secure = getattr(view_func, 'is_secure_route', False)
        
        assert is_secure, (
            f"SECURITY BREACH! The route '{endpoint}' is not marked as public, "
            f"is not in a secured blueprint, and is missing a security decorator."
        )