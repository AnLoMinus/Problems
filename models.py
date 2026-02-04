from datetime import datetime
import json
import os

class User:
    def __init__(self, username, email, password_hash, role='user'):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.last_login = None
        self.settings = {}

    @staticmethod
    def load_users():
        if not os.path.exists('data/users.json'):
            return {}
        with open('data/users.json', 'r') as f:
            return json.load(f)

    @staticmethod
    def save_users(users):
        with open('data/users.json', 'w') as f:
            json.dump(users, f, indent=4)

class Permission:
    def __init__(self, user_id, resource_id, permission_type):
        self.user_id = user_id
        self.resource_id = resource_id
        self.permission_type = permission_type  # read, write, admin
        self.granted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def load_permissions():
        if not os.path.exists('data/permissions.json'):
            return {}
        with open('data/permissions.json', 'r') as f:
            return json.load(f)

    @staticmethod
    def save_permissions(permissions):
        with open('data/permissions.json', 'w') as f:
            json.dump(permissions, f, indent=4) 

class Group:
    def __init__(self, name, description, creator_id):
        self.name = name
        self.description = description
        self.creator_id = creator_id
        self.members = [creator_id]
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def load_groups():
        if not os.path.exists('data/groups.json'):
            return {'groups': []}
        with open('data/groups.json', 'r') as f:
            return json.load(f)

    @staticmethod
    def save_groups(groups):
        with open('data/groups.json', 'w') as f:
            json.dump(groups, f, indent=4)
            
    @staticmethod
    def load_user_groups(user_id):
        groups = Group.load_groups()
        return [g for g in groups['groups'] 
                if user_id in g['members'] or g['creator_id'] == user_id] 