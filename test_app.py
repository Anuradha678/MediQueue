"""
MediQueue – Automated Integration Test Suite
Validates all user requirements and API endpoints.
"""

import os
import tempfile
import unittest
from datetime import date

# Tests must never touch the user's real MySQL database or local SQLite data.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="mediqueue_test_")
os.environ["DB_BACKEND"] = "sqlite"
os.environ["SQLITE_DB_PATH"] = os.path.join(_TEST_DB_DIR, "test_mediqueue.sqlite3")

from app import app
from database import get_db, init_db

class MediQueueTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        init_db()

        # Clean patient table for fresh daily testing
        today = date.today().isoformat()
        with get_db(auto_commit=True) as db:
            db.modify("DELETE FROM patients WHERE queue_date = %s", (today,))

    def test_01_public_pages_load(self):
        """Verify all HTML public pages render with HTTP 200."""
        routes = ['/', '/about', '/contact', '/patient', '/login', '/track-queue']
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed with {response.status_code}")
            self.assertIn(b'MediQueue', response.data)

    def test_02_404_page(self):
        """Verify 404 handler returns friendly error page."""
        response = self.client.get('/non-existent-page-xyz')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.data)

    def test_03_patient_registration_and_token_generation(self):
        """Verify patient registration generates sequential daily tokens."""
        # Patient 1
        res1 = self.client.post('/api/register-patient', json={
            'patient_name': 'Alice Smith',
            'phone': '+1 555-0101'
        })
        self.assertEqual(res1.status_code, 201)
        data1 = res1.get_json()
        self.assertTrue(data1['success'])
        self.assertEqual(data1['data']['token_number'], 'MQ-001')
        self.assertEqual(data1['data']['patients_ahead'], 0)

        # Patient 2
        res2 = self.client.post('/api/register-patient', json={
            'patient_name': 'Bob Johnson',
            'phone': '+1 555-0102'
        })
        self.assertEqual(res2.status_code, 201)
        data2 = res2.get_json()
        self.assertEqual(data2['data']['token_number'], 'MQ-002')
        self.assertEqual(data2['data']['patients_ahead'], 1)

        # Patient 3
        res3 = self.client.post('/api/register-patient', json={
            'patient_name': 'Charlie Brown',
            'phone': '+1 555-0103'
        })
        self.assertEqual(res3.status_code, 201)
        data3 = res3.get_json()
        self.assertEqual(data3['data']['token_number'], 'MQ-003')
        self.assertEqual(data3['data']['patients_ahead'], 2)

    def test_04_patient_input_validation(self):
        """Verify validation errors on invalid inputs."""
        # Empty name
        res = self.client.post('/api/register-patient', json={
            'patient_name': '',
            'phone': '1234567890'
        })
        self.assertEqual(res.status_code, 400)

        # Invalid phone
        res = self.client.post('/api/register-patient', json={
            'patient_name': 'Valid Name',
            'phone': 'abc'
        })
        self.assertEqual(res.status_code, 400)

    def test_05_queue_tracking_api(self):
        """Verify queue tracking returns correct info and hides other patients' data."""
        self.client.post('/api/register-patient', json={'patient_name': 'David Miller', 'phone': '555-1234'})
        res = self.client.get('/api/queue/MQ-001')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()['data']
        self.assertEqual(data['token_number'], 'MQ-001')
        self.assertEqual(data['patient_name'], 'David Miller')
        self.assertEqual(data['status'], 'Waiting')
        self.assertNotIn('phone', data)  # Privacy check!

    def test_06_unauthorized_access_protection(self):
        """Verify dashboard is protected from unauthorized users."""
        # HTML route redirects to login
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # API route returns 401 Unauthorized
        res_api = self.client.get('/api/dashboard')
        self.assertEqual(res_api.status_code, 401)

    def test_07_doctor_login_and_logout(self):
        """Verify doctor authentication flow."""
        # Failed login
        res_fail = self.client.post('/api/login', json={'username': 'doctor', 'password': 'wrongpassword'})
        self.assertEqual(res_fail.status_code, 401)

        # Successful login
        res_success = self.client.post('/api/login', json={'username': 'doctor', 'password': 'Doctor@123'})
        self.assertEqual(res_success.status_code, 200)
        self.assertTrue(res_success.get_json()['success'])

        # Now dashboard API is accessible
        res_dash = self.client.get('/api/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Logout
        res_logout = self.client.post('/api/logout')
        self.assertEqual(res_logout.status_code, 200)

        # Now dashboard API is blocked again
        res_dash_after = self.client.get('/api/dashboard')
        self.assertEqual(res_dash_after.status_code, 401)

    def test_08_queue_progression_logic(self):
        """
        Verify doctor queue actions:
        - Next Patient moves earliest Waiting to Serving
        - Next Patient moves current Serving to Completed
        - Mark as Missed works
        - Completed cannot be served again
        """
        # Register 3 patients
        self.client.post('/api/register-patient', json={'patient_name': 'Patient One', 'phone': '111-1111'})
        self.client.post('/api/register-patient', json={'patient_name': 'Patient Two', 'phone': '222-2222'})
        self.client.post('/api/register-patient', json={'patient_name': 'Patient Three', 'phone': '333-3333'})

        # Log in doctor
        self.client.post('/api/login', json={'username': 'doctor', 'password': 'Doctor@123'})

        # Check initial stats
        res = self.client.get('/api/dashboard')
        stats = res.get_json()['data']['stats']
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['waiting'], 3)
        self.assertEqual(stats['serving'], 0)

        # Call Next Patient -> MQ-001 should become Serving
        res_next1 = self.client.post('/api/next-patient')
        self.assertEqual(res_next1.status_code, 200)
        serving1 = res_next1.get_json()['current_serving']
        self.assertIsNotNone(serving1)
        self.assertEqual(serving1['token_number'], 'MQ-001')

        # Check queue status for MQ-001 (should be Serving)
        q1 = self.client.get('/api/queue/MQ-001').get_json()['data']
        self.assertEqual(q1['status'], 'Serving')
        self.assertTrue(q1['is_now_serving'])

        # Check queue status for MQ-002 (should be Waiting, 0 patients ahead of him among waiting)
        q2 = self.client.get('/api/queue/MQ-002').get_json()['data']
        self.assertEqual(q2['status'], 'Waiting')
        self.assertEqual(q2['current_serving'], 'MQ-001')
        self.assertEqual(q2['patients_ahead'], 0)

        # Call Next Patient again -> MQ-001 becomes Completed, MQ-002 becomes Serving
        res_next2 = self.client.post('/api/next-patient')
        serving2 = res_next2.get_json()['current_serving']
        self.assertEqual(serving2['token_number'], 'MQ-002')

        # Verify MQ-001 is Completed
        q1_after = self.client.get('/api/queue/MQ-001').get_json()['data']
        self.assertEqual(q1_after['status'], 'Completed')

        # Mark MQ-003 as Missed
        res_missed = self.client.post('/api/mark-missed', json={'token_number': 'MQ-003'})
        self.assertEqual(res_missed.status_code, 200)

        q3_after = self.client.get('/api/queue/MQ-003').get_json()['data']
        self.assertEqual(q3_after['status'], 'Missed')

        # Re-queue MQ-003 back to Waiting
        res_requeue = self.client.post('/api/requeue-patient', json={'token_number': 'MQ-003'})
        self.assertEqual(res_requeue.status_code, 200)
        q3_requeued = self.client.get('/api/queue/MQ-003').get_json()['data']
        self.assertEqual(q3_requeued['status'], 'Waiting')

        # Complete MQ-002
        res_comp = self.client.post('/api/complete-patient', json={'token_number': 'MQ-002'})
        self.assertEqual(res_comp.status_code, 200)
        q2_comp = self.client.get('/api/queue/MQ-002').get_json()['data']
        self.assertEqual(q2_comp['status'], 'Completed')

if __name__ == '__main__':
    unittest.main()
