import json
from .models import User

class UserManager:
    def __init__(self, storage_path):
        self.storage_path = storage_path

    def get_user(self, user_id):
        # Example: Load from a JSON file
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
        
        user_data = data.get(user_id)
        if user_data:
            return User(
                user_id=user_id,
                username=user_data['username'],
                email=user_data['email'],
                profile_data=user_data.get('profile_data')
            )
        return None

    def save_user(self, user):
        # Logic to write back to JSON or execute an SQLite INSERT/UPDATE
        pass