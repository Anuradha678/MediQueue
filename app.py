"""
MediQueue – Digital Patient Queue Management System
Main Flask Application Server
"""

import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, session, request, jsonify

from config import Config
from database import init_db, get_db, get_backend
from backend.auth import auth_bp
from backend.patients import patients_bp
from backend.queue import queue_bp
from backend.dashboard import dashboard_bp

# Initialize Flask application with custom template and static folders
base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'frontend', 'templates'),
    static_folder=os.path.join(base_dir, 'frontend', 'static')
)

# Load configuration
app.config.from_object(Config)

# Register API blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(queue_bp)
app.register_blueprint(dashboard_bp)


@app.context_processor
def inject_global_template_context():
    """Make clinic configuration parameters available across all templates."""
    return {
        'clinic_name': Config.CLINIC_NAME,
        'clinic_tagline': Config.CLINIC_TAGLINE,
        'doctor_name': Config.DOCTOR_NAME,
        'clinic_phone': Config.CLINIC_PHONE,
        'clinic_email': Config.CLINIC_EMAIL,
        'clinic_address': Config.CLINIC_ADDRESS,
        'clinic_hours': Config.CLINIC_HOURS,
        'current_year': datetime.now().year,
        'is_doctor_logged_in': 'doctor_id' in session,
        'logged_doctor_name': session.get('full_name', 'Doctor')
    }


# ========================================================
# Frontend Page Routes
# ========================================================



@app.route('/api/health', methods=['GET'])
def api_health():
    """Small local diagnostic endpoint for checking the active database connection."""
    try:
        backend = get_backend()
        with get_db() as db:
            db.fetchone("SELECT 1 AS connection_ok")
        return jsonify({
            'success': True,
            'application': 'MediQueue',
            'database_backend': backend,
            'database_name': Config.DB_NAME if backend == 'mysql' else 'database/mediqueue.sqlite3',
            'message': 'Application and database are responding.'
        }), 200
    except Exception:
        app.logger.exception('Health check failed')
        return jsonify({
            'success': False,
            'message': 'Database connection check failed. See the Flask terminal.'
        }), 503


@app.route('/')
def index():
    """Home landing page."""
    return render_template('index.html', active_page='home')


@app.route('/about')
def about():
    """About clinic page."""
    return render_template('about.html', active_page='about')


@app.route('/contact')
def contact():
    """Contact & inquiries page."""
    return render_template('contact.html', active_page='contact')


@app.route('/patient')
def patient():
    """Patient registration page."""
    return render_template('patient.html', active_page='patient')


@app.route('/track-queue')
def track_queue():
    """Patient live queue tracking page."""
    token = request.args.get('token', '').strip().upper()
    return render_template('track_queue.html', active_page='track_queue', initial_token=token)


@app.route('/login')
def login():
    """Doctor login page."""
    if 'doctor_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html', active_page='login')


@app.route('/dashboard')
def dashboard():
    """Doctor dashboard (staff.html). Protected by session check."""
    if 'doctor_id' not in session:
        return redirect(url_for('login'))
    return render_template('staff.html', active_page='dashboard')


# ========================================================
# Error Handlers
# ========================================================

@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Internal server error handler."""
    return render_template('404.html', error_title="Server Error", error_message="An internal server error occurred."), 500


# Ensure database tables and initial admin are ready upon launch
try:
    init_db()
except Exception as err:
    print(f"[MediQueue Warning] Initial DB bootstrap notice: {err}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 65)
    print(f" MediQueue – Digital Patient Queue Management System")
    print(f" Running on http://127.0.0.1:{port}")
    print("=" * 65)
    app.run(host='0.0.0.0', port=port, debug=True)
