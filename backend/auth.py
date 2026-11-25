"""
MediQueue – Doctor Authentication Module
Handles login, session persistence, secure password verification, and route protection.
"""

from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash
from database import get_db

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator to protect doctor dashboard routes and APIs."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'doctor_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required. Please log in.'
                }), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """Authenticate doctor credentials and establish session."""
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()

    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Please provide both username and password.'
        }), 400

    try:
        with get_db() as db:
            doctor = db.fetchone(
                "SELECT id, username, password_hash, full_name FROM doctors WHERE username = %s",
                (username,)
            )

        if not doctor or not check_password_hash(doctor['password_hash'], password):
            return jsonify({
                'success': False,
                'error': 'Invalid username or password.'
            }), 401

        # Establish secure doctor session
        session.clear()
        session['doctor_id'] = doctor['id']
        session['username'] = doctor['username']
        session['full_name'] = doctor['full_name']
        session.permanent = True

        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'doctor': {
                'id': doctor['id'],
                'username': doctor['username'],
                'full_name': doctor['full_name']
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An unexpected error occurred during login: {str(e)}'
        }), 500


@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """Clear doctor session and log out."""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully.'
    }), 200


@auth_bp.route('/api/auth-status', methods=['GET'])
def api_auth_status():
    """Return current doctor login status for UI state synchronization."""
    if 'doctor_id' in session:
        return jsonify({
            'authenticated': True,
            'doctor': {
                'id': session.get('doctor_id'),
                'username': session.get('username'),
                'full_name': session.get('full_name')
            }
        })
    return jsonify({
        'authenticated': False,
        'doctor': None
    })
