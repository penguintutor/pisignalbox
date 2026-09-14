# models.py
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import case
from sqlalchemy.ext.hybrid import hybrid_property
from vlcbserver.constants import ROLES

db = SQLAlchemy()

""" Roles:

user - basic user view only
operator - control trains
manager - full railway config - not user admin
admin - full control useradmin
"""

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # API key - nulls for password based logins
    api_key = db.Column(db.String(128), unique=True, nullable=True)

    # Additional Fields
    # Email users NULL to enforce uniqueness - as can use that to login as well
    _email = db.Column('email', db.String(120), nullable=True, unique=True)
    full_name = db.Column(db.String(150), nullable=False, default="", server_default="")
    # short name uses a setter allowing replacement with username
    _short_name = db.Column('short_name', db.String(50), nullable=False, default="", server_default="")
    
    # Using a string for role with a default fallback
    role = db.Column(db.String(50), nullable=False, default='reader')

    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return self.role == role_name

    @property
    def role_display_name(self):
        # Fallback to the shortname if the key isn't found in ROLES
        return ROLES.get(self.role, {self.role})

    # Hybrid properties allow displaying a different string instead of None
    # If shortname is "" then replace with username

    @hybrid_property
    def email(self):
        # Python sees an empty string instead of None
        return self._email if self._email else ""

    @email.setter
    def email(self, value):
        # If the frontend passes an empty string (""), convert it to None for the DB
        # This prevents the unique=True constraint from crashing on multiple blanks
        self._email = None if not value else value.strip()

    @hybrid_property
    def short_name(self):
        return self._short_name if self._short_name is not None else self.username

    @short_name.setter
    def short_name(self, value):
        self._short_name = value if value is not None else ""

    @short_name.expression
    def short_name(cls):
        # SQL-level logic (used when filtering or sorting in database queries)
        return case(
            (cls._short_name == "", cls.username),
            else_=cls._short_name
        )

    def __repr__(self):
        return f'<User {self.username}>'


    # Used for self password reset - assuming user has entered email
    def get_reset_token(self):
        """Generates a secure, signed token for the user."""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        # The salt adds a specific context so this token can only be used for password resets
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=900):
        """Verifies the token and returns the User if valid (expires_sec=900 is 15 mins)."""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            # max_age enforces the expiration time
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
            user_id = data['user_id']
        except Exception:
            # Token is invalid, tampered with, or expired
            return None
            
        return User.query.get(user_id)


# System user used by API (no username)
class ApiUser(UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='reader')

    def __init__(self):
        # Flask-Login needs an ID as a string
        #self.id = "api_system_user" 
        #self.username = "Client App"
        pass
        

    # API users also have a role
    def has_role(self, role_name):
            """Check if the user has a specific role."""
            return self.role == role_name
    