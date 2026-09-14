# Used when setting up new users through the CLI
# Needs to be run once from vlcbserver.py, then not required

import sys
import json
import getpass
import secrets
import logging
from pathlib import Path
from werkzeug.security import generate_password_hash


# Now we can safely import the app factory and database models
from vlcbserver import create_app
from vlcbserver.core.models import db, User



def create_user(db):
    print("\n--- Create New User ---")
    # Keep asking for a username until valid
    while True:
        raw_input = input("Username: ").strip()
        if not raw_input:
            print("Error: Username cannot be empty.")
            continue

        full_name, username = _handle_username_spaces(raw_input)

        # Check for duplicate username
        existing_user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if existing_user:
            print(f"Error: User '{username}' already exists in the database.")
        else:
            break

        # If user was not valid then keep looping until it is 
        
    # Keep asking for a password until valid
    while True:
        password = getpass.getpass("Password: ")
        confirm_password = getpass.getpass("Confirm Password: ")

        if password == confirm_password:
            break
        else:
            print("Error: Passwords do not match.")
            continue # NOSONAR - explicit guard for future loop expansions 

        # Future: Check for valid password here - eg. min chars?

    password_hash = generate_password_hash(password)
    # User is added as an admin so can manage other users
    new_user = User(username=username, password_hash=password_hash, role="admin", full_name=full_name) # type: ignore
    
    db.session.add(new_user)
    db.session.commit()
    print(f"Success: User '{username}' added to the database.")

def create_api_key(db, base_dir):
    print("\n--- Create API Key ---")

    # Also need to update the guiclient settings.json file
    # Update our file paths to start from the BASE_DIR instead of BASE_DIR
    SETTINGS_FILE = base_dir / 'guiclient' / 'data' / 'settings.json'

    while True:
        raw_input = input("Enter username to attach this API key to (e.g., 'GUI Api'): ").strip()
        if not raw_input:
            print("Error: Username cannot be empty.")
            continue

        full_name, username = _handle_username_spaces(raw_input)
 

        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        
        if not user:
            print(f"User '{username}' not found. Creating as an API-only system user...")
            user = User(username=username, password_hash="SYSTEM_API_USER_NO_PASSWORD", role="update", full_name=full_name) # type: ignore
            db.session.add(user)

        custom_key = input("Enter API key (leave blank to auto-generate securely): ").strip()
        api_key = custom_key if custom_key else secrets.token_urlsafe(32)

        existing_key = db.session.execute(db.select(User).filter_by(api_key=api_key)).scalar_one_or_none()
        if existing_key and existing_key.username != username:
            print("Error: This exact API key is already assigned to a different user.")
        else:
            break

    user.api_key = api_key
    db.session.commit()
    print(f"Success: API key for '{username}' saved to the database.")

    # Save API key to guiclient/data/settings.json
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    data = {}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass
            
    if "server" not in data or not isinstance(data["server"], dict):
        data["server"] = {}
        
    data["server"]["api_key"] = api_key
    
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print(f"Success: API key written to {SETTINGS_FILE}")

def _handle_username_spaces(raw_input):
    # Check if there is at least one space in the input
    if " " in raw_input:
        full_name = raw_input
        username = raw_input.lower().replace(" ", "_")
    else:
            # No spaces, use it directly as the username
        full_name = ""  # Uses the empty string default you set up earlier
        # still make it lower case
        username = raw_input.lower()
    return full_name,username

def new_auth(config):
    print("Initializing setup...")
   
    app = create_app(config)
    
    with app.app_context():
        # This creates instances/users.db and the tables if they don't exist yet
        db.create_all()
        
        print("Database connection verified.")

        # Create up to 1 user and 1 api key
        ans = input("\nWould you like to create a new user? [y/N]: ").strip().lower()
        if ans == 'y':
            create_user(db)
                
        ans = input("\nWould you like to create/update an API key? [y/N]: ").strip().lower()
        if ans == 'y':
            create_api_key(db, config['BASE_DIR'])
                
        print("\nSetup complete. Exiting.")

