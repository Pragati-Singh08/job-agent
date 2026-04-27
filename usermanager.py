import json
import os
import hashlib

USERS_FILE = "./data/users.json"

class UserManager:
    def __init__(self):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w") as f:
                json.dump({}, f)
        
    def _load_users(self):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
            
    def _save_users(self, users):
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
            
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
        
    def signup(self, username, password):
        users = self._load_users()
        if username in users:
            return False, "User already exists"
        users[username] = self._hash_password(password)
        self._save_users(users)
        return True, "Signup successful"
        
    def login(self, username, password):
        users = self._load_users()
        if username not in users:
            return False, "User not found"
        if users[username] == self._hash_password(password):
            return True, "Login successful"
        return False, "Invalid password"
