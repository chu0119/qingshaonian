"""Security and permission hardening tests."""
import unittest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models.user import User, School
from app.utils.jwt import create_access_token


class SecurityHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.database import Base, engine, init_db
        Base.metadata.create_all(bind=engine)
        init_db()

    def setUp(self):
        from app.main import app
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def _login(self, username: str, password: str) -> dict:
        r = self.client.post("/api/v1/auth/login", json={"username": username, "password": password})
        self.assertEqual(r.status_code, 200, r.text)
        return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}

    # ---- 1. 平台管理员代入审计 ----
    def test_platform_enter_school_returns_impersonation_token(self):
        headers = self._login("padm", "padm123")
        db = SessionLocal()
        school = db.query(School).first()
        self.assertIsNotNone(school)
        school_id = school.id
        db.close()

        r = self.client.post(f"/api/v1/platform/schools/{school_id}/enter", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()["data"]
        # 返回平台管理员身份 + school_context
        self.assertEqual(data["user"]["role"], "platform_admin")
        self.assertIn("school_context", data)
        self.assertEqual(data["school_context"]["id"], school_id)
        self.assertIn("access_token", data)

    # ---- 2. get_current_user 不修改 ORM school_id ----
    def test_impersonation_does_not_mutate_user_school_id(self):
        headers = self._login("padm", "padm123")
        db = SessionLocal()
        padm = db.query(User).filter(User.username == "padm").first()
        original_school_id = padm.school_id
        db.close()

        # 用代入 token 调用学校级接口
        school = db.query(School).first()
        enter_r = self.client.post(f"/api/v1/platform/schools/{school.id}/enter", headers=headers)
        enter_token = enter_r.json()["data"]["access_token"]
        enter_headers = {"Authorization": f"Bearer {enter_token}"}
        self.client.get("/api/v1/dashboard/", headers=enter_headers)

        # 确认 platform admin 的 school_id 没被修改
        db2 = SessionLocal()
        padm2 = db2.query(User).filter(User.username == "padm").first()
        self.assertEqual(padm2.school_id, original_school_id)
        db2.close()

    # ---- 3. 学校管理员不能跨校重置密码 ----
    def test_school_admin_cannot_reset_other_school_password(self):
        db = SessionLocal()
        schools = db.query(School).all()
        if len(schools) < 2:
            # 创建第二个学校测试
            from app.models.user import School as SchoolModel
            s2 = SchoolModel(name="OtherSchool", code="OTHER", status=True)
            db.add(s2)
            db.flush()
            other_user = User(
                school_id=s2.id, username="other_user",
                password_hash="x", real_name="Other", role="teacher", status=True,
            )
            db.add(other_user)
            db.commit()
            other_user_id = other_user.id
            db.close()
        else:
            other_user = db.query(User).filter(
                User.school_id != 1, User.role == "student"
            ).first()
            if not other_user:
                db.close()
                return
            other_user_id = other_user.id
            db.close()

        headers = self._login("admin", "admin123")
        r = self.client.put(
            f"/api/v1/auth/reset-password/{other_user_id}",
            headers=headers,
            json={"new_password": "Hacked12345"},
        )
        self.assertEqual(r.status_code, 403)

    # ---- 4. 教师创建接口防 role 污染 ----
    def test_create_teacher_rejects_school_admin_role(self):
        headers = self._login("admin", "admin123")
        r = self.client.post(
            "/api/v1/users/teachers",
            headers=headers,
            json={
                "username": "fake_admin_test",
                "password": "Test@123456",
                "real_name": "Fake Admin",
                "role": "school_admin",
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("teacher", r.json()["detail"])

    def test_create_teacher_rejects_platform_admin_role(self):
        headers = self._login("admin", "admin123")
        r = self.client.post(
            "/api/v1/users/teachers",
            headers=headers,
            json={
                "username": "fake_padm_test",
                "password": "Test@123456",
                "real_name": "Fake Padm",
                "role": "platform_admin",
            },
        )
        self.assertEqual(r.status_code, 400)

    # ---- 5. 学校管理员不能重置 platform_admin 密码 ----
    def test_school_admin_cannot_reset_platform_admin_password(self):
        db = SessionLocal()
        padm = db.query(User).filter(User.username == "padm").first()
        padm_id = padm.id
        db.close()

        headers = self._login("admin", "admin123")
        r = self.client.put(
            f"/api/v1/auth/reset-password/{padm_id}",
            headers=headers,
            json={"new_password": "Hacked@123"},
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("平台管理员", r.json()["detail"])

    # ---- 6. 平台管理员代入后 require_role 放行 ----
    def test_platform_admin_with_context_can_access_school_routes(self):
        headers = self._login("padm", "padm123")
        db = SessionLocal()
        school = db.query(School).first()
        school_id = school.id
        db.close()

        enter_r = self.client.post(f"/api/v1/platform/schools/{school_id}/enter", headers=headers)
        token = enter_r.json()["data"]["access_token"]
        school_headers = {"Authorization": f"Bearer {token}"}

        # 应该能访问 school-admin 路由（dashboard）
        r = self.client.get("/api/v1/dashboard/", headers=school_headers)
        self.assertIn(r.status_code, (200, 404, 422))  # 不应返回 403


if __name__ == "__main__":
    unittest.main()
