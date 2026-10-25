import unittest
import json
import os
import tempfile
from pathlib import Path

# Configure environment before importing app
os.environ["SECRET_KEY"] = "test-secret-key-12345"
temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"

from app import app
from db import init_db, Session, engine
from models import Base, Service, Token, AdminUser, QueueEvent
from services.queue_service import QueueService

class QueueLessTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    @classmethod
    def tearDownClass(cls):
        try:
            os.close(temp_db_fd)
            os.remove(temp_db_path)
        except Exception:
            pass

    def setUp(self):
        self.client = app.test_client()
        self.session = Session()

    def tearDown(self):
        self.session.close()
        Session.remove()

    def test_01_database_seeded(self):
        """Verify default services and admin account are seeded"""
        services = self.session.query(Service).all()
        self.assertGreaterEqual(len(services), 4)
        
        admin = self.session.query(AdminUser).filter_by(username="admin").first()
        self.assertIsNotNone(admin)

    def test_02_visitor_get_services(self):
        """Verify visitor can view active services"""
        res = self.client.get("/api/services")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["services"]), 4)

    def test_03_visitor_generate_token(self):
        """Verify visitor can generate a token with sequential number and ref code"""
        payload = {
            "service_id": 1,
            "visitor_name": "Test Student",
            "student_id": "CS101",
            "notes": "Testing token creation",
            "idempotency_key": "test-key-001"
        }
        res = self.client.post("/api/token/generate", json=payload)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("ADM-", data["token"]["token_number"])
        self.assertTrue(data["token"]["reference_code"].startswith("QL-"))
        self.assertEqual(data["token"]["status"], "WAITING")

    def test_04_idempotency_prevents_duplicate_token(self):
        """Verify submitting with same idempotency key returns existing token"""
        payload = {
            "service_id": 1,
            "visitor_name": "Test Duplicate",
            "idempotency_key": "duplicate-prevention-key-123"
        }
        res1 = self.client.post("/api/token/generate", json=payload)
        self.assertEqual(res1.status_code, 201)
        data1 = json.loads(res1.data)
        token_num1 = data1["token"]["token_number"]

        # Resubmit identical request
        res2 = self.client.post("/api/token/generate", json=payload)
        self.assertEqual(res2.status_code, 201)
        data2 = json.loads(res2.data)
        token_num2 = data2["token"]["token_number"]

        self.assertEqual(token_num1, token_num2)
        self.assertTrue(data2.get("is_duplicate"))

    def test_05_visitor_retrieve_token_status(self):
        """Verify visitor can retrieve their live status by reference code"""
        # Create token
        t_res = self.client.post("/api/token/generate", json={"service_id": 2, "visitor_name": "Status Visitor"})
        t_data = json.loads(t_res.data)["token"]
        ref_code = t_data["reference_code"]

        res = self.client.get(f"/api/token/status/{ref_code}")
        self.assertEqual(res.status_code, 200)
        status = json.loads(res.data)["data"]
        self.assertEqual(status["token_number"], t_data["token_number"])
        self.assertIn(status["status"], ["WAITING", "APPROACHING"])
        self.assertIn("people_ahead", status)
        self.assertIn("estimated_wait_mins", status)

    def test_06_admin_login(self):
        """Verify secure administrator authentication"""
        # Bad login
        res_bad = self.client.post("/admin/login", data={"username": "admin", "password": "wrongpassword"})
        self.assertIn(b"Invalid username or password", res_bad.data)

        # Good login
        res_good = self.client.post("/admin/login", data={"username": "admin", "password": "QueueLessAdmin2026!"}, follow_redirects=True)
        self.assertEqual(res_good.status_code, 200)
        self.assertIn(b"Queue Management Dashboard", res_good.data)

    def test_07_admin_call_next_and_complete(self):
        """Verify administrator can call next token and complete it"""
        # Ensure at least one token is in service 1
        self.client.post("/api/token/generate", json={"service_id": 1, "visitor_name": "Call Next Test"})

        # Log in as admin
        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_id"] = 1
            sess["admin_username"] = "admin"

        # Call next token
        call_res = self.client.post("/api/admin/call-next", json={"service_id": 1})
        self.assertEqual(call_res.status_code, 200)
        call_data = json.loads(call_res.data)
        self.assertTrue(call_data["success"])
        called_token = call_data["called_token"]
        self.assertEqual(called_token["status"], "SERVING")

        # Mark completed
        comp_res = self.client.post("/api/admin/complete", json={"token_id": called_token["id"]})
        self.assertEqual(comp_res.status_code, 200)
        comp_data = json.loads(comp_res.data)
        self.assertTrue(comp_data["success"])

    def test_08_admin_skip_token(self):
        """Verify administrator can skip an absent visitor"""
        # Generate token
        gen_res = self.client.post("/api/token/generate", json={"service_id": 3, "visitor_name": "Skip Test"})
        token_id = json.loads(gen_res.data)["token"]["id"]

        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_id"] = 1

        skip_res = self.client.post("/api/admin/skip", json={"token_id": token_id, "reason": "No response"})
        self.assertEqual(skip_res.status_code, 200)
        skip_data = json.loads(skip_res.data)
        self.assertTrue(skip_data["success"])

    def test_09_visitor_cancel_token(self):
        """Verify visitor can voluntarily cancel their token"""
        gen_res = self.client.post("/api/token/generate", json={"service_id": 4, "visitor_name": "Cancel Test"})
        ref_code = json.loads(gen_res.data)["token"]["reference_code"]

        cancel_res = self.client.post("/api/token/cancel", json={"reference_code": ref_code})
        self.assertEqual(cancel_res.status_code, 200)
        cancel_data = json.loads(cancel_res.data)
        self.assertTrue(cancel_data["success"])

        # Check status is CANCELLED
        status_res = self.client.get(f"/api/token/status/{ref_code}")
        status_data = json.loads(status_res.data)["data"]
        self.assertEqual(status_data["raw_status"], "CANCELLED")

    def test_10_empty_queue_handling(self):
        """Verify system handles calling next when queue is empty gracefully"""
        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_id"] = 1

        # Reset service 4 queue first
        self.client.post("/api/admin/reset", json={"service_id": 4})

        # Try to call next when queue is empty
        res = self.client.post("/api/admin/call-next", json={"service_id": 4})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get("queue_empty"))
        self.assertIn("No visitors waiting", data.get("message"))

    def test_11_health_and_display_endpoints(self):
        """Verify health check and public kiosk display data endpoints"""
        h_res = self.client.get("/health")
        self.assertEqual(h_res.status_code, 200)
        h_data = json.loads(h_res.data)
        self.assertEqual(h_data["status"], "healthy")
        self.assertEqual(h_data["database"], "connected")

        d_res = self.client.get("/api/display")
        self.assertEqual(d_res.status_code, 200)
        d_data = json.loads(d_res.data)
        self.assertTrue(d_data["success"])
        self.assertIn("counters", d_data["data"])

if __name__ == "__main__":
    unittest.main()
