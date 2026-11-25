"""
MediQueue – Patient Registration Module
Handles patient validation, transactional daily token generation, and queue entry.
"""

import re
import logging
from datetime import date
from flask import Blueprint, request, jsonify
from database import get_db

patients_bp = Blueprint('patients', __name__)
logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(r'^\+?[0-9\s\-()]{7,20}$')
NAME_REGEX = re.compile(r"^[^\W\d_][\w\s.'’\-]{1,99}$", re.UNICODE)


def generate_next_token(db, today_date):
    """
    Generate the next sequential token for today (e.g. MQ-001, MQ-002).
    Uses row-level locking / transaction isolation to prevent race conditions.
    """
    row = db.fetchone(
        "SELECT token_number FROM patients WHERE queue_date = %s ORDER BY id DESC LIMIT 1 FOR UPDATE",
        (today_date,)
    )
    if not row or not row.get('token_number'):
        return "MQ-001"
    
    last_token = str(row['token_number']).strip()
    match = re.search(r'(\d+)$', last_token)
    if match:
        next_num = int(match.group(1)) + 1
        return f"MQ-{next_num:03d}"
    return "MQ-001"


@patients_bp.route('/api/register-patient', methods=['POST'])
def register_patient():
    """Register a new patient and issue a daily queue token."""
    data = request.get_json(silent=True) or {}
    patient_name = str(data.get('patient_name', '')).strip()
    phone = str(data.get('phone', '')).strip()

    # Validation
    if not patient_name:
        return jsonify({'success': False, 'error': 'Patient full name is required.'}), 400

    if not NAME_REGEX.fullmatch(patient_name):
        return jsonify({
            'success': False,
            'error': 'Please enter a valid patient name (2-100 characters, letters only).'
        }), 400

    if not phone:
        return jsonify({'success': False, 'error': 'Phone number is required.'}), 400

    if not PHONE_REGEX.fullmatch(phone) or sum(ch.isdigit() for ch in phone) < 7:
        return jsonify({
            'success': False,
            'error': 'Please enter a valid phone number containing at least 7 digits.'
        }), 400

    today = date.today().isoformat()

    try:
        # Transaction block to protect token generation
        with get_db(auto_commit=False) as db:
            token_number = generate_next_token(db, today)
            
            # Insert patient record
            new_id, _ = db.modify(
                """
                INSERT INTO patients (token_number, patient_name, phone, status, queue_date)
                VALUES (%s, %s, %s, 'Waiting', %s)
                """,
                (token_number, patient_name, phone, today),
                auto_commit=False
            )
            
            # Count waiting patients ahead of this newly registered patient
            ahead_row = db.fetchone(
                """
                SELECT COUNT(*) as count 
                FROM patients 
                WHERE queue_date = %s AND status = 'Waiting' AND id < %s
                """,
                (today, new_id)
            )
            patients_ahead = ahead_row['count'] if ahead_row else 0
            
            # Get current serving token if any
            serving_row = db.fetchone(
                "SELECT token_number FROM patients WHERE queue_date = %s AND status = 'Serving' LIMIT 1",
                (today,)
            )
            current_serving = serving_row['token_number'] if serving_row else None
            
            # Commit the transaction atomically
            db.commit()

        return jsonify({
            'success': True,
            'message': f'Patient registered successfully. Your token is {token_number}.',
            'data': {
                'id': new_id,
                'token_number': token_number,
                'patient_name': patient_name,
                'phone': phone,
                'queue_date': today,
                'status': 'Waiting',
                'patients_ahead': patients_ahead,
                'current_serving': current_serving
            }
        }), 201

    except Exception as e:
        logger.exception('Patient registration failed')
        # Return a readable error so the frontend can show the actual cause during local development.
        return jsonify({
            'success': False,
            'error': f'Failed to register patient: {str(e)}'
        }), 500
