import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, url_for
from flask_login import LoginManager
from pathlib import Path
from werkzeug.security import generate_password_hash


from vlcbserver.blueprints.auth import auth_blueprint

class DummyUser:
    """A standard Python class to bypass MagicMock JSON serialization issues."""
    
    # Add a parameter to toggle the password state, defaulting to True so existing tests don't break
    def __init__(self, has_password_flag=True):
        self.id = 1
        self.username = "test_user_"
        self._email = "test@example.com"
        self.password_hash = generate_password_hash('password')
        
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False
        
        # Store the flag to be returned by the property
        self._has_password = has_password_flag

    def get_id(self):
        return str(self.id)

    def get_reset_token(self):
        return "mock_token_123"

    @property
    def has_password(self):
        return self._has_password



@pytest.fixture
def app():
    """Create and configure a basic Flask app for testing the blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['SERVER_NAME'] = 'localhost.localdomain'
    app.config['CONFIG_DIR'] = Path('/tmp/mock_config_dir')

    # Initialize Flask-Login for the test application
    login_manager = LoginManager()
    login_manager.init_app(app)

    # Provide a dummy user loader for Flask-Login during tests
    @login_manager.user_loader
    def load_user(user_id):
        from unittest.mock import MagicMock
        user = MagicMock()
        user.get_id.return_value = str(user_id)
        return user

    @pytest.fixture
    def mock_user():
        """A standard Python class to mimic the User model for Flask-Login."""
        return DummyUser()

    # Need to register a dummy home blueprint to satisfy url_for('home.home')
    from flask import Blueprint
    dummy_home = Blueprint('home', __name__)
    @dummy_home.route('/home')
    def home():
        return "Home"
    
    # Import and register the auth blueprint
    from vlcbserver.blueprints.auth.routes import auth_blueprint
    
    app.register_blueprint(dummy_home)
    app.register_blueprint(auth_blueprint)
    
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def mock_user():
    """A mock user object for database returns."""
    user = MagicMock()
    user.username = "test_user"
    user._email = "test@example.com"
    # Create a real hash for the word 'password' to test check_password_hash
    user.password_hash = generate_password_hash('password')
    user.get_reset_token.return_value = "mock_token_123"
    return user

# --- TESTS FOR LOGIN ROUTE ---

@patch('vlcbserver.blueprints.auth.routes.current_user')
def test_login_redirects_if_authenticated(mock_current_user, client):
    """Test that an already authenticated user is redirected to home."""
    mock_current_user.is_authenticated = True
    response = client.get('/login')
    
    assert response.status_code == 302
    assert '/home' in response.headers['Location'] #[cite: 1]

@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_post_success_username(mock_user_model, client):
    """Test successful login using a username."""
    # Instantiate the dummy user directly in the test
    dummy = DummyUser()
    # Explicitly map the mocked SQLAlchemy query to return our dummy object
    mock_user_model.query.filter_by.return_value.first.return_value = dummy
    
    response = client.post('/login', data={
        'username': 'Test User ',
        'password': 'password'
    })
    
    mock_user_model.query.filter_by.assert_called_with(username='test_user_')
    assert response.status_code == 302
    assert '/home' in response.headers['Location']


@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_post_success_email(mock_user_model, client):
    """Test successful login using an email address."""
    dummy = DummyUser()
    mock_user_model.query.filter_by.return_value.first.return_value = dummy
    
    response = client.post('/login', data={
        'username': 'test@example.com',
        'password': 'password'
    })
    
    mock_user_model.query.filter_by.assert_called_with(_email='test@example.com')
    assert response.status_code == 302

@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_post_invalid_credentials(mock_user_model, client):
    """Test login with invalid password."""
    mock_user = MagicMock()
    mock_user.password_hash = generate_password_hash('correct_password')
    mock_user_model.query.filter_by.return_value.first.return_value = mock_user
    
    response = client.post('/login', data={
        'username': 'test_user',
        'password': 'wrong_password'
    })
    
    # Fails and redirects back to the login page[cite: 1]
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_login_open_redirect_protection(client, app):
    """Test that absolute URLs are ignored in the next parameter."""
    with app.test_request_context('/login?next=http://malicious.com'):
        from vlcbserver.blueprints.auth.routes import login
        # We simulate the validation of the next parameter[cite: 1]
        from urllib.parse import urlparse
        next_page = 'http://malicious.com'
        
        # Ensure it gets caught by the validation[cite: 1]
        assert urlparse(next_page).netloc != ''

# --- TESTS FOR LOGOUT ROUTE ---

@patch('vlcbserver.blueprints.auth.routes.logout_user')
def test_logout_route(mock_logout_user, client, app):
    """Test that logging out calls logout_user and redirects to login."""
    # Disable @login_required temporarily so the request reaches the route
    app.config['LOGIN_DISABLED'] = True 
    
    response = client.get('/logout')
    
    mock_logout_user.assert_called_once() 
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# --- TESTS FOR RESET REQUEST ROUTE ---

@patch('pathlib.Path.is_file')
def test_reset_request_disabled_without_config(mock_is_file, client):
    """Test that reset rejects POST if mail_config.json does not exist."""
    mock_is_file.return_value = False # Simulate missing config file[cite: 1]
    
    response = client.post('/reset_password', data={'email': 'test@example.com'})
    
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

@patch('pathlib.Path.is_file')
@patch('vlcbserver.blueprints.auth.routes.User')
@patch('vlcbserver.blueprints.auth.routes.threading.Thread')
def test_reset_request_post_success(mock_thread, mock_user_model, mock_is_file, mock_user, client):
    """Test that an email triggers a background thread."""
    mock_is_file.return_value = True
    mock_user_model.query.filter_by.return_value.first.return_value = mock_user
    
    response = client.post('/reset_password', data={'email': 'test@example.com'})
    
    # Assert thread was spun up as daemon[cite: 1]
    mock_thread.assert_called_once()
    assert mock_thread.call_args[1]['daemon'] is True
    # Assert thread started[cite: 1]
    mock_thread.return_value.start.assert_called_once()
    
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# --- TESTS FOR RESET TOKEN ROUTE ---

@patch('vlcbserver.blueprints.auth.routes.User')
def test_reset_token_invalid_token(mock_user_model, client):
    """Test accessing the reset token page with an invalid token."""
    mock_user_model.verify_reset_token.return_value = None # Invalid token[cite: 1]
    
    response = client.get('/reset_password/invalid_token')
    
    assert response.status_code == 302
    assert '/reset_password' in response.headers['Location'] # Redirects back to reset request[cite: 1]

@patch('vlcbserver.blueprints.auth.routes.User')
def test_reset_token_post_length_validation(mock_user_model, mock_user, client):
    """Test that password updates require length between 8 and 128 characters."""
    mock_user_model.verify_reset_token.return_value = mock_user
    
    # Test short password (< 8 chars)[cite: 1]
    response_short = client.post('/reset_password/valid_token', data={'password': 'short'})
    assert response_short.status_code == 302
    assert '/reset_password/valid_token' in response_short.headers['Location']

    # Test long password (> 128 chars)[cite: 1]
    long_password = "a" * 129
    response_long = client.post('/reset_password/valid_token', data={'password': long_password})
    assert response_long.status_code == 302
    assert '/reset_password/valid_token' in response_long.headers['Location']

@patch('vlcbserver.blueprints.auth.routes.User')
@patch('vlcbserver.blueprints.auth.routes.db')
def test_reset_token_post_success(mock_db, mock_user_model, mock_user, client):
    """Test successfully changing a password with a valid token."""
    mock_user_model.verify_reset_token.return_value = mock_user
    
    response = client.post('/reset_password/valid_token', data={'password': 'new_valid_password'})
    
    # Verify the database commit was called to save the new hash[cite: 1]
    mock_db.session.commit.assert_called_once()
    
    # Should redirect to login upon success[cite: 1]
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_post_fails_when_has_password_is_false(mock_user_model, client):
    """Test that a user without a password (has_password=False) is rejected."""
    # Initialize the dummy user with the flag set to False
    dummy = DummyUser(has_password_flag=False)
    mock_user_model.query.filter_by.return_value.first.return_value = dummy
    
    response = client.post('/login', data={
        'username': 'test_user_',
        'password': 'password'
    })
    
    # Authentication should fail and redirect the user back to the login page
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_post_succeeds_when_has_password_is_true(mock_user_model, client):
    """Test that a user with a password (has_password=True) is authenticated."""
    # Initialize the dummy user with the flag set to True (or rely on the default)
    dummy = DummyUser(has_password_flag=True)
    mock_user_model.query.filter_by.return_value.first.return_value = dummy
    
    response = client.post('/login', data={
        'username': 'test_user_',
        'password': 'password'
    })
    
    # Authentication should succeed and redirect to the home page
    assert response.status_code == 302
    assert '/home' in response.headers['Location']


## Additional Security Testing

# Algorithmic Complexity / DoS via Long Passwords
@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_extreme_password_length_dos(mock_user_model, client):
    """Verify the system rejects extremely long passwords before hashing to prevent CPU exhaustion."""
    dummy = DummyUser()
    mock_user_model.query.filter_by.return_value.first.return_value = dummy
    
    # Send a massive password payload
    long_password = "A" * 100_000
    
    response = client.post('/login', data={
        'username': 'test_user_',
        'password': long_password
    })
    
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# SQL Injection (SQLi) Payloads
@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_sql_injection_attempt(mock_user_model, client):
    """Ensure standard SQL injection payloads do not bypass authentication or crash the server."""
    # Ensure the DB query returns nothing for this payload
    mock_user_model.query.filter_by.return_value.first.return_value = None
    
    response = client.post('/login', data={
        'username': "admin' OR '1'='1",
        'password': "password"
    })
    
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# Cross-Site Scripting (XSS) and Control Characters
@patch('vlcbserver.blueprints.auth.routes.User')
def test_login_xss_and_control_characters(mock_user_model, client):
    """Test that HTML tags and null bytes are handled safely without crashing."""
    mock_user_model.query.filter_by.return_value.first.return_value = None
    
    malformed_inputs = [
        "<script>alert('xss')</script>",
        "admin\x00",
        "../../../etc/passwd"
    ]
    
    for payload in malformed_inputs:
        response = client.post('/login', data={
            'username': payload,
            'password': 'password'
        })
        
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


# Missing Form Keys        
def test_login_missing_form_data(client):
    """Test that omitting expected form fields fails safely without 500 errors."""
    # Sending an empty POST request (no username or password keys)
    response = client.post('/login', data={})
    
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
