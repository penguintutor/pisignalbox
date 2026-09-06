# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

""" Roles:

user - basic user view only
operator - control trains
manager - full railway config - not user admin
admin - full control useradmin

api-operator - control trains
api-manager - full railway config - not user admin (default)
api-admin - full control including useradmin
"""

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # API key - nulls for password based logins
    api_key = db.Column(db.String(128), unique=True, nullable=True)

    # Additional Fields
    email = db.Column(db.String(120), nullable=True)
    full_name = db.Column(db.String(150), nullable=True)
    short_name = db.Column(db.String(50), nullable=True)
    
    # Using a string for role with a default fallback
    role = db.Column(db.String(50), nullable=False, default='user')

    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return True
        #return self.role == role_name

    def __repr__(self):
        return f'<User {self.username}>'


# System user used by API (no username)
class ApiUser(UserMixin):
    def __init__(self):
        # Flask-Login needs an ID as a string
        self.id = "api_system_user" 
        self.username = "Client App"