"""
MediQueue – Queue Tracking Module
Provides real-time queue lookup, patients-ahead calculations, and privacy-safe responses.
"""

from datetime import date
from flask import Blueprint, request, jsonify
from database import get_db

queue_bp = Blueprint('queue', __name__)


@queue_bp.route('/api/queue/<token>', methods=['GET'])
def get_queue_status(token):
    """
    Fetch queue status for a specific patient token.
    Ensures private information (like phone numbers) of other patients is never exposed.
    """
    token_clean = str(token).strip().upper()
    if not token_clean:
        return jsonify({'success': False, 'error': 'Invalid token number.'}), 400

    today = date.today().isoformat()

    try:
        with get_db() as db:
            # First look for today's token
            patient = db.fetchone(
                """
                SELECT id, token_number, patient_name, status, queue_date, created_at 
                FROM patients 
                WHERE token_number = %s AND queue_date = %s
                """,
                (token_clean, today)
            )

            # If not found today, check if token existed on another day for helpful feedback
            if not patient:
                older_patient = db.fetchone(
                    """
                    SELECT id, token_number, patient_name, status, queue_date, created_at 
                    FROM patients 
                    WHERE token_number = %s 
                    ORDER BY id DESC LIMIT 1
                    """,
                    (token_clean,)
                )
                if older_patient:
                    patient = older_patient
                else:
                    return jsonify({
                        'success': False,
                        'error': f"Token '{token_clean}' not found. Please verify your token number."
                    }), 404

            # Determine currently serving patient for this queue date
            serving_patient = db.fetchone(
                """
                SELECT token_number, patient_name 
                FROM patients 
                WHERE queue_date = %s AND status = 'Serving' 
                LIMIT 1
                """,
                (patient['queue_date'],)
            )

            current_serving_token = serving_patient['token_number'] if serving_patient else "None (Waiting to start)"

            # Calculate number of patients ahead
            patients_ahead = 0
            if patient['status'] == 'Waiting':
                ahead_row = db.fetchone(
                    """
                    SELECT COUNT(*) as count 
                    FROM patients 
                    WHERE queue_date = %s AND status = 'Waiting' AND id < %s
                    """,
                    (patient['queue_date'], patient['id'])
                )
                patients_ahead = ahead_row['count'] if ahead_row else 0

            # Approximate estimated waiting time (e.g. 10 minutes per patient ahead)
            est_wait_minutes = patients_ahead * 10

            return jsonify({
                'success': True,
                'data': {
                    'token_number': patient['token_number'],
                    'patient_name': patient['patient_name'],
                    'status': patient['status'],
                    'queue_date': str(patient['queue_date']),
                    'created_at': str(patient['created_at']),
                    'current_serving': current_serving_token,
                    'patients_ahead': patients_ahead,
                    'estimated_wait_minutes': est_wait_minutes,
                    'is_now_serving': (patient['status'] == 'Serving')
                }
            }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve queue information: {str(e)}'
        }), 500


@queue_bp.route('/api/public-queue', methods=['GET'])
def get_public_queue():
    """Return anonymized public queue statistics for the home page banner."""
    today = date.today().isoformat()
    try:
        with get_db() as db:
            serving = db.fetchone(
                "SELECT token_number FROM patients WHERE queue_date = %s AND status = 'Serving' LIMIT 1",
                (today,)
            )
            waiting_row = db.fetchone(
                "SELECT COUNT(*) as count FROM patients WHERE queue_date = %s AND status = 'Waiting'",
                (today,)
            )
            total_row = db.fetchone(
                "SELECT COUNT(*) as count FROM patients WHERE queue_date = %s",
                (today,)
            )

        return jsonify({
            'success': True,
            'data': {
                'today': today,
                'current_serving': serving['token_number'] if serving else 'None',
                'waiting_count': waiting_row['count'] if waiting_row else 0,
                'total_today': total_row['count'] if total_row else 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
