"""
MediQueue – Doctor Dashboard Module
Manages queue transitions, next-patient calls, completions, missed statuses, and statistics.
Uses database transactions to ensure consistency and single-serving-patient enforcement.
"""

from datetime import date
from flask import Blueprint, request, jsonify, session
from database import get_db
from backend.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/api/dashboard', methods=['GET'])
@login_required
def get_dashboard_data():
    """Retrieve all real-time stats and patient queue list for today."""
    today = date.today().isoformat()
    
    try:
        with get_db() as db:
            # 1. Compute today's top statistic counters
            stats_raw = db.fetchone("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Waiting' THEN 1 ELSE 0 END) as waiting,
                    SUM(CASE WHEN status = 'Serving' THEN 1 ELSE 0 END) as serving,
                    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'Missed' THEN 1 ELSE 0 END) as missed
                FROM patients 
                WHERE queue_date = %s
            """, (today,))
            
            stats = {
                'total': stats_raw['total'] or 0,
                'waiting': int(stats_raw['waiting'] or 0),
                'serving': int(stats_raw['serving'] or 0),
                'completed': int(stats_raw['completed'] or 0),
                'missed': int(stats_raw['missed'] or 0)
            }
            
            # 2. Retrieve the currently serving patient
            current_serving = db.fetchone("""
                SELECT id, token_number, patient_name, phone, status, created_at
                FROM patients
                WHERE queue_date = %s AND status = 'Serving'
                LIMIT 1
            """, (today,))
            
            # 3. Retrieve all patients for today
            patients = db.fetchall("""
                SELECT id, token_number, patient_name, phone, status, queue_date, created_at
                FROM patients
                WHERE queue_date = %s
                ORDER BY id ASC
            """, (today,))

        return jsonify({
            'success': True,
            'data': {
                'today': today,
                'stats': stats,
                'current_serving': current_serving,
                'patients': patients,
                'doctor': {
                    'username': session.get('username'),
                    'full_name': session.get('full_name')
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to load dashboard data: {str(e)}'
        }), 500


@dashboard_bp.route('/api/next-patient', methods=['POST'])
@login_required
def call_next_patient():
    """
    Queue transition rule:
    1. Mark currently Serving patient as Completed.
    2. Find the earliest Waiting patient for today.
    3. Change that patient to Serving.
    4. Protected by a transaction.
    """
    today = date.today().isoformat()
    
    try:
        with get_db(auto_commit=False) as db:
            # Step 1: Complete any currently serving patient
            serving_patient = db.fetchone("""
                SELECT id, token_number, patient_name 
                FROM patients 
                WHERE queue_date = %s AND status = 'Serving' 
                LIMIT 1 FOR UPDATE
            """, (today,))
            
            if serving_patient:
                db.modify("""
                    UPDATE patients 
                    SET status = 'Completed' 
                    WHERE id = %s
                """, (serving_patient['id'],), auto_commit=False)

            # Step 2: Find earliest waiting patient
            next_patient = db.fetchone("""
                SELECT id, token_number, patient_name, phone, created_at 
                FROM patients 
                WHERE queue_date = %s AND status = 'Waiting' 
                ORDER BY id ASC 
                LIMIT 1 FOR UPDATE
            """, (today,))
            
            if next_patient:
                # Step 3: Change earliest waiting to Serving
                db.modify("""
                    UPDATE patients 
                    SET status = 'Serving' 
                    WHERE id = %s
                """, (next_patient['id'],), auto_commit=False)
                
                db.commit()
                return jsonify({
                    'success': True,
                    'message': f"Now serving {next_patient['token_number']} ({next_patient['patient_name']}).",
                    'current_serving': next_patient
                }), 200
            else:
                db.commit()
                return jsonify({
                    'success': True,
                    'message': 'No Waiting Patients remaining in queue.',
                    'current_serving': None
                }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to advance queue: {str(e)}'
        }), 500


@dashboard_bp.route('/api/mark-missed', methods=['POST'])
@login_required
def mark_patient_missed():
    """Mark a patient as Missed."""
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    token_number = data.get('token_number')
    today = date.today().isoformat()

    if not patient_id and not token_number:
        return jsonify({'success': False, 'error': 'Patient identifier required.'}), 400

    try:
        with get_db(auto_commit=False) as db:
            if patient_id:
                patient = db.fetchone("SELECT id, token_number, status FROM patients WHERE id = %s", (patient_id,))
            else:
                patient = db.fetchone("SELECT id, token_number, status FROM patients WHERE token_number = %s AND queue_date = %s", (token_number, today))

            if not patient:
                return jsonify({'success': False, 'error': 'Patient not found.'}), 404

            if patient['status'] == 'Completed':
                return jsonify({'success': False, 'error': 'Cannot mark a completed consultation as missed.'}), 400

            db.modify("UPDATE patients SET status = 'Missed' WHERE id = %s", (patient['id'],), auto_commit=False)
            db.commit()

        return jsonify({
            'success': True,
            'message': f"Token {patient['token_number']} marked as Missed."
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to update status: {str(e)}'}), 500


@dashboard_bp.route('/api/complete-patient', methods=['POST'])
@login_required
def complete_patient_consultation():
    """Mark a patient consultation as Completed."""
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    token_number = data.get('token_number')
    today = date.today().isoformat()

    if not patient_id and not token_number:
        return jsonify({'success': False, 'error': 'Patient identifier required.'}), 400

    try:
        with get_db(auto_commit=False) as db:
            if patient_id:
                patient = db.fetchone("SELECT id, token_number, status FROM patients WHERE id = %s", (patient_id,))
            else:
                patient = db.fetchone("SELECT id, token_number, status FROM patients WHERE token_number = %s AND queue_date = %s", (token_number, today))

            if not patient:
                return jsonify({'success': False, 'error': 'Patient not found.'}), 404

            db.modify("UPDATE patients SET status = 'Completed' WHERE id = %s", (patient['id'],), auto_commit=False)
            db.commit()

        return jsonify({
            'success': True,
            'message': f"Token {patient['token_number']} marked as Completed."
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to complete patient: {str(e)}'}), 500


@dashboard_bp.route('/api/requeue-patient', methods=['POST'])
@login_required
def requeue_patient():
    """Re-queue a Missed patient back into the Waiting queue."""
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    token_number = data.get('token_number')
    today = date.today().isoformat()

    if not patient_id and not token_number:
        return jsonify({'success': False, 'error': 'Patient identifier required.'}), 400

    try:
        with get_db(auto_commit=False) as db:
            if patient_id:
                patient = db.fetchone("SELECT id, token_number, status FROM patients WHERE id = %s", (patient_id,))
            else:
                patient = db.fetchone("SELECT id, token_number, status FROM patients WHERE token_number = %s AND queue_date = %s", (token_number, today))

            if not patient:
                return jsonify({'success': False, 'error': 'Patient not found.'}), 404

            db.modify("UPDATE patients SET status = 'Waiting' WHERE id = %s", (patient['id'],), auto_commit=False)
            db.commit()

        return jsonify({
            'success': True,
            'message': f"Token {patient['token_number']} restored to Waiting queue."
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to re-queue patient: {str(e)}'}), 500
