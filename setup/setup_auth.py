import sys
import json
import getpass
import secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

# Resolve paths relative to this script's location in setup/
SETUP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SETUP_DIR.parent

# Add the project root to sys.path so Python can find 'vlcbserver'
sys.path.insert(0, str(PROJECT_ROOT))

# Now we can safely import the app factory and database models
from vlcbserver import create_app
from vlcbserver.models import db, User

# Update our file paths to start from the PROJECT_ROOT instead of BASE_DIR
SETTINGS_FILE = PROJECT_ROOT / 'guiclient' / 'data' / 'settings.json'

def create_user():
    print("\n--- Create New User ---")
    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return

    # Check for duplicate username
    existing_user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    if existing_user:
        print(f"Error: User '{username}' already exists in the database.")
        return

    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")

    if password != confirm_password:
        print("Error: Passwords do not match.")
        return

    password_hash = generate_password_hash(password)
    new_user = User(username=username, password_hash=password_hash) # type: ignore
    
    db.session.add(new_user)
    db.session.commit()
    print(f"Success: User '{username}' added to the database.")

def create_api_key():
    print("\n--- Create API Key ---")
    
    username = input("Enter username to attach this API key to (e.g., 'GUI Api'): ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    
    if not user:
        print(f"User '{username}' not found. Creating as an API-only system user...")
        user = User(username=username, password_hash="SYSTEM_API_USER_NO_PASSWORD") # type: ignore
        db.session.add(user)

    custom_key = input("Enter API key (leave blank to auto-generate securely): ").strip()
    api_key = custom_key if custom_key else secrets.token_urlsafe(32)

    existing_key = db.session.execute(db.select(User).filter_by(api_key=api_key)).scalar_one_or_none()
    if existing_key and existing_key.username != username:
        print("Error: This exact API key is already assigned to a different user.")
        return

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

def main():
    print("Initializing setup...")

    # Define the instances directory
    INSTANCE_DIR = PROJECT_ROOT / 'instances'
    # CREATE the directory if it doesn't exist (This fixes the error)
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    
    # We pass the minimal config needed to initialize the DB connection,
    # ensuring the database is created in the main project's instances folder
    config = {
'SQLALCHEMY_DATABASE_URI': f"sqlite:///{INSTANCE_DIR / 'users.db'}",
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    
    app = create_app(config)
    
    with app.app_context():
        # This creates instances/users.db and the tables if they don't exist yet
        db.create_all()
        print("Database connection verified.")

        while True:
            ans = input("\nWould you like to create a new user? [y/N]: ").strip().lower()
            if ans == 'y':
                create_user()
            else:
                break
                
        while True:
            ans = input("\nWould you like to create/update an API key? [y/N]: ").strip().lower()
            if ans == 'y':
                create_api_key()
            else:
                break
                
        print("\nSetup complete. Exiting.")

if __name__ == '__main__':
    main()