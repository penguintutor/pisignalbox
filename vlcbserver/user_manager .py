from .models import db, User

def create_user(username, password_hash):
    """Add a new user to the database."""
    # Create a Python object representing the row
    new_user = User(username=username, password_hash=password_hash) # type: ignore
    
    # Add it to the current transaction
    db.session.add(new_user)
    
    # Commit the transaction to write it to the file
    db.session.commit()
    
    return new_user

def get_user_by_username(username):
    """Fetch a user by their username."""
    # Modern SQLAlchemy 2.0 syntax (which Flask-SQLAlchemy v3+ uses)
    user = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar_one_or_none()
    
    return user

def delete_user(username):
    """Delete a user."""
    user = get_user_by_username(username)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False