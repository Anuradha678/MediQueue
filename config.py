import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base application configuration."""
    
    # Secret Key for Flask sessions and CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mediqueue_dev_secret_key_89748e85')
    
    # Session Configuration
    SESSION_COOKIE_NAME = 'mediqueue_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    
    # MySQL Database Configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'mediqueue_db')
    DB_BACKEND = os.environ.get('DB_BACKEND', 'mysql').strip().lower()
    SQLITE_DB_PATH = os.environ.get('SQLITE_DB_PATH', os.path.join(os.path.dirname(__file__), 'database', 'mediqueue.sqlite3'))
    # Keep MySQL as the single source of truth; opt in to SQLite only for isolated demos/tests.
    DB_ALLOW_SQLITE_FALLBACK = os.environ.get('DB_ALLOW_SQLITE_FALLBACK', '0').strip().lower() in ('1', 'true', 'yes')
    
    # Default Doctor Account (for setup / create_admin.py)
    DEFAULT_ADMIN_USER = os.environ.get('DEFAULT_ADMIN_USER', 'doctor')
    DEFAULT_ADMIN_PASS = os.environ.get('DEFAULT_ADMIN_PASS', 'Doctor@123')
    DEFAULT_ADMIN_NAME = os.environ.get('DEFAULT_ADMIN_NAME', 'Dr. Suraweera')
    
    # Clinic Details
    CLINIC_NAME = 'MediQueue Medical Centre'
    CLINIC_TAGLINE = 'Digital Patient Queue Management System'
    DOCTOR_NAME = 'Dr. Suraweera'
    CLINIC_PHONE = '0714460005'
    CLINIC_EMAIL = 'care@mediqueue-clinic.com'
    CLINIC_ADDRESS = 'Pollaththapitiya,Kurunegala'
    CLINIC_HOURS = 'Monday – Friday: 4:00PM – 9:00 PM Saturday-Sunday: 8:PM - 10PM and 4:00PM - 9:00PM '
