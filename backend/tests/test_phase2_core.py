import time
import unittest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models.audit import OperationLog
from app.models.external import AIAnalysisLog, SMSLog
from app.models.questionnaire import Option, Question, Questionnaire
from app.models.risk import RiskAlert
from app.models.task import AnswerSheet, Task
from app.models.user import Class, Grade, School, TeacherClass, User


client = TestClient(app)


class Phase2CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        init_db()

    def setUp(self):
        self.db = SessionLocal()
        self.suffix = str(int(time.time() * 1000))[-8:]

    def tearDown(self):
        self.db.close()

    def _login(self, username: str, password: str) -> str:
        response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]["access_token"]

    def test_platform_can_open_school_admin_and_dashboard_has_rankings(self):
        token = self._login("padm", "padm123")
        code = f"P1S{self.suffix}"
        response = client.post(
            "/api/v1/platform/schools",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": f"P1学校{self.suffix}",
                "code": code,
                "admin_username": f"p1admin_{self.suffix}",
                "admin_password": "InitPass12345",
                "admin_name": "P1学校管理员",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        admin = self.db.query(User).filter(User.username == data["admin_username"]).first()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.school_id, data["id"])
        self.assertTrue(admin.must_change_password)

        dashboard = client.get("/api/v1/platform/dashboard", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        payload = dashboard.json()["data"]
        for key in ("school_total", "enabled_school_total", "disabled_school_total", "answer_sheet_total",
                    "ai_call_total", "sms_send_total", "completion_rankings", "risk_rankings",
                    "risk_handling_rankings", "recent_active_schools"):
            self.assertIn(key, payload)

    def test_school_admin_lifecycle_endpoints_audit_password_and_disable(self):
        platform_token = self._login("padm", "padm123")
        code = f"P1A{self.suffix}"
        created = client.post(
            "/api/v1/platform/schools",
            headers={"Authorization": f"Bearer {platform_token}"},
            json={"name": f"P1账号学校{self.suffix}", "code": code, "admin_password": "InitPass12345"},
        ).json()["data"]

        response = client.post(
            f"/api/v1/platform/schools/{created['id']}/admins",
            headers={"Authorization": f"Bearer {platform_token}"},
            json={"username": f"p1extra_{self.suffix}", "real_name": "备用管理员", "password": "InitPass12345"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        admin_id = response.json()["data"]["id"]

        reset = client.post(
            f"/api/v1/platform/schools/{created['id']}/admins/{admin_id}/reset-password",
            headers={"Authorization": f"Bearer {platform_token}"},
            json={"password": "ResetPass12345"},
        )
        self.assertEqual(reset.status_code, 200, reset.text)
        disabled = client.post(
            f"/api/v1/platform/schools/{created['id']}/admins/{admin_id}/disable",
            headers={"Authorization": f"Bearer {platform_token}"},
        )
        self.assertEqual(disabled.status_code, 200, disabled.text)

        admin = self.db.query(User).filter(User.id == admin_id).first()
        self.assertFalse(admin.status)
        self.assertTrue(admin.must_change_password)
        actions = [
            r.action
            for r in self.db.query(OperationLog).filter(
                OperationLog.module == "school_admin_account",
                OperationLog.object_id == str(admin_id),
            ).all()
        ]
        self.assertIn("create", actions)
        self.assertIn("reset_password", actions)
        self.assertIn("disable", actions)

    def test_task_lifecycle_prevents_closed_submission_and_keeps_school_on_sheet(self):
        school = School(name=f"P1流程学校{self.suffix}", code=f"P1F{self.suffix}")
        self.db.add(school)
        self.db.flush()
        grade = Grade(school_id=school.id, name="初一", sort_order=1)
        self.db.add(grade)
        self.db.flush()
        klass = Class(school_id=school.id, grade_id=grade.id, name="一班")
        self.db.add(klass)
        self.db.flush()
        student = User(school_id=school.id, username=f"p1stu_{self.suffix}", password_hash="", real_name="学生", role="student", grade_id=grade.id, class_id=klass.id)
        teacher = User(school_id=school.id, username=f"p1tea_{self.suffix}", password_hash="", real_name="教师", role="teacher")
        self.db.add_all([student, teacher])
        self.db.flush()
        self.db.add(TeacherClass(teacher_id=teacher.id, class_id=klass.id))
        questionnaire = Questionnaire(school_id=school.id, title="P1问卷", status="active", created_by=teacher.id)
        self.db.add(questionnaire)
        self.db.flush()
        question = Question(questionnaire_id=questionnaire.id, title="必填题", type="single_choice", required=True, sort_order=1, dimension="emotion")
        self.db.add(question)
        self.db.flush()
        self.db.add(Option(question_id=question.id, content="是", score=4, sort_order=1, is_risk_option=True))
        task = Task(school_id=school.id, questionnaire_id=questionnaire.id, name="P1任务", target_type="class",
                    target_ids=[klass.id], status="closed", published_at=datetime.now(), closed_at=datetime.now(), created_by=teacher.id)
        self.db.add(task)
        self.db.commit()

        from app.services.scoring_service import start_answer
        with self.assertRaisesRegex(ValueError, "任务已关闭"):
            start_answer(self.db, task.id, student.id)

        task.status = "in_progress"
        task.closed_at = None
        self.db.commit()
        sheet = start_answer(self.db, task.id, student.id)
        self.assertEqual(sheet.school_id, school.id)
        self.assertEqual(sheet.class_id, klass.id)

    def test_ai_and_sms_have_business_logs_when_unconfigured(self):
        school = School(name=f"P1日志学校{self.suffix}", code=f"P1L{self.suffix}")
        self.db.add(school)
        self.db.flush()
        admin = User(
            school_id=school.id,
            username=f"p1log_{self.suffix}",
            password_hash="",
            real_name="管理员",
            role="school_admin",
            status=True,
            phone="13800000000",
        )
        self.db.add(admin)
        self.db.commit()

        from app.utils.password import hash_password
        admin.password_hash = hash_password("InitPass12345")
        self.db.commit()
        token = self._login(admin.username, "InitPass12345")

        ai = client.post(
            "/api/v1/ai/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "overall_report", "object_id": school.id},
        )
        self.assertEqual(ai.status_code, 200, ai.text)
        self.assertIn("本分析仅作为学校教育管理和学生关怀参考", ai.json()["data"]["analysis"])
        self.assertIsNotNone(self.db.query(AIAnalysisLog).filter(AIAnalysisLog.user_id == admin.id).first())

        sms = client.post(
            "/api/v1/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            json={"recipient_user_id": admin.id, "sms_type": "task_publish", "template_code": "task_publish"},
        )
        self.assertEqual(sms.status_code, 200, sms.text)
        self.assertEqual(sms.json()["data"]["status"], "not_configured")
        self.assertIsNotNone(self.db.query(SMSLog).filter(SMSLog.recipient_user_id == admin.id).first())


if __name__ == "__main__":
    unittest.main()
