"""
MediQueue Backend Package
"""
from backend.auth import auth_bp, login_required
from backend.patients import patients_bp
from backend.queue import queue_bp
from backend.dashboard import dashboard_bp

__all__ = ['auth_bp', 'patients_bp', 'queue_bp', 'dashboard_bp', 'login_required']
