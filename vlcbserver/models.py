# models.py
from flask_login import UserMixin

# Mock database (or connect to a real database later)
USER_DB = {
    "admin": {"password_hash": "scrypt:32768:8:1$..."}
}

class User(UserMixin):
    def __init__(self, user_id, username=None, email=None, profile_data = None):
        self.id = user_id
        self.username = username or "System"
        self.email = email or "API"
        # Profile is a dict
        self.profile_data = profile_data or {}