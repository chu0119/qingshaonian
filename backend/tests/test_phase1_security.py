import unittest

from fastapi.testclient import TestClient


class Phase1SecurityTests(unittest.TestCase):
    def setUp(self):
        from app.config import settings

        self._old_debug = settings.DEBUG
        self.client = TestClient(self._load_app())
        self.client.__enter__()

    def tearDown(self):
        from app.config import settings

        settings.DEBUG = self._old_debug
        self.client.__exit__(None, None, None)

    @staticmethod
    def _load_app():
        from app.main import app

        return app

    def _login(self, username: str, password: str) -> dict:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_production_config_validation_rejects_unsafe_defaults(self):
        from app.config import Settings, validate_production_settings

        unsafe = Settings(
            APP_ENV="production",
            DEBUG=True,
            JWT_SECRET_KEY="change-me-to-a-random-secret-key-in-production",
            ADMIN_USERNAME="admin",
            ADMIN_PASSWORD="admin123",
            PLATFORM_ADMIN_USERNAME="padm",
            PLATFORM_ADMIN_PASSWORD="padm123",
        )

        with self.assertRaises(RuntimeError) as ctx:
            validate_production_settings(unsafe)

        message = str(ctx.exception)
        self.assertIn("DEBUG", message)
        self.assertIn("JWT_SECRET_KEY", message)
        self.assertIn("ADMIN_PASSWORD", message)

    def test_production_sms_without_provider_never_leaks_code(self):
        from app.config import settings

        settings.DEBUG = False
        response = self.client.post(
            "/api/v1/auth/send-sms-code",
            json={"phone": "13900000001", "purpose": "reset_password"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertNotIn("code", payload)
        self.assertEqual(payload["message"], "短信服务暂未配置")
        self.assertFalse(payload["sms_sent"])

    def test_login_attempts_are_written_to_login_logs(self):
        from app.database import SessionLocal
        from app.models.audit import LoginLog

        self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        self._login("admin", "admin123")

        db = SessionLocal()
        try:
            success = (
                db.query(LoginLog)
                .filter(LoginLog.username == "admin", LoginLog.result == "success")
                .order_by(LoginLog.id.desc())
                .first()
            )
            failure = (
                db.query(LoginLog)
                .filter(LoginLog.username == "admin", LoginLog.result == "failure")
                .order_by(LoginLog.id.desc())
                .first()
            )
            self.assertIsNotNone(success)
            self.assertEqual(success.user_role, "school_admin")
            self.assertIsNotNone(failure)
            self.assertTrue(failure.failure_reason)
        finally:
            db.close()

    def test_critical_operations_are_written_to_operation_logs(self):
        from app.database import SessionLocal
        from app.models.audit import OperationLog

        headers = self._login("padm", "padm123")
        code = "AUDIT_TEST_SCHOOL"
        existing = self.client.get(
            "/api/v1/platform/schools",
            headers=headers,
            params={"keyword": code},
        ).json()["data"]["items"]
        for school in existing:
            self.client.delete(f"/api/v1/platform/schools/{school['id']}/force", headers=headers)

        response = self.client.post(
            "/api/v1/platform/schools",
            headers=headers,
            json={
                "name": "审计测试学校",
                "code": code,
                "admin_username": "audit_school_admin",
                "admin_password": "audit123456",
                "admin_name": "审计管理员",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

        db = SessionLocal()
        try:
            log = (
                db.query(OperationLog)
                .filter(
                    OperationLog.module == "platform_school",
                    OperationLog.action == "create",
                    OperationLog.object_type == "school",
                    OperationLog.object_id == str(response.json()["data"]["id"]),
                )
                .order_by(OperationLog.id.desc())
                .first()
            )
            self.assertIsNotNone(log)
            self.assertEqual(log.operator_role, "platform_admin")
            self.assertEqual(log.result, "success")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
