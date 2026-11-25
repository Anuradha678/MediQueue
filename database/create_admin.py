"""
MediQueue – Doctor Account Provisioning Script
Creates or updates the default doctor credentials in the database.
"""

import sys
import os
import argparse

# Add parent directory to path so config and database modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from werkzeug.security import generate_password_hash
from config import Config
from database import get_db, init_db

def create_or_update_doctor(username, password, full_name):
    """Create or update a doctor account."""
    print("=" * 60)
    print("MediQueue – Doctor Account Setup")
    print("=" * 60)
    
    # Ensure database tables exist
    init_db()
    
    password_hash = generate_password_hash(password)
    
    with get_db(auto_commit=True) as db:
        existing = db.fetchone("SELECT id, username FROM doctors WHERE username = %s", (username,))
        
        if existing:
            db.modify("""
                UPDATE doctors 
                SET password_hash = %s, full_name = %s
                WHERE username = %s
            """, (password_hash, full_name, username))
            print(f"[SUCCESS] Doctor account '{username}' updated successfully.")
        else:
            db.modify("""
                INSERT INTO doctors (username, password_hash, full_name)
                VALUES (%s, %s, %s)
            """, (username, password_hash, full_name))
            print(f"[SUCCESS] Doctor account '{username}' created successfully.")
            
    print(f"Doctor Name : {full_name}")
    print(f"Username    : {username}")
    print(f"Password    : {password}")
    print("=" * 60)
    print("You can now login at http://127.0.0.1:5000/login")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create or update doctor account for MediQueue")
    parser.add_argument('--username', default=Config.DEFAULT_ADMIN_USER, help='Doctor login username')
    parser.add_argument('--password', default=Config.DEFAULT_ADMIN_PASS, help='Doctor login password')
    parser.add_argument('--name', default=Config.DEFAULT_ADMIN_NAME, help='Doctor full name')
    
    args = parser.parse_args()
    create_or_update_doctor(args.username, args.password, args.name)
