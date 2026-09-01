# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # API key - nulls for password based logins
    api_key = db.Column(db.String(128), unique=True, nullable=True)

    

    def __repr__(self):
        return f'<User {self.username}>'

# System user used by API (no username)
class ApiUser(UserMixin):
    def __init__(self):
        # Flask-Login needs an ID as a string
        self.id = "api_system_user" 
        self.username = "Client App"