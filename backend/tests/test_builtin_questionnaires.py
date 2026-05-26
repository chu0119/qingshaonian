import time
import unittest

from app.database import Base, SessionLocal, engine, init_db
from app.models.questionnaire import Questionnaire
from app.models.user import School, User
from app.services.questionnaire_service import create_questionnaire, update_questionnaire
from app.schemas.questionnaire import QuestionnaireCreate, QuestionnaireUpdate
from app.services.seed_service import initialize_seed_data


class BuiltinQuestionnaireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        init_db()

    def setUp(self):
        self.db = SessionLocal()
        self.suffix = str(int(time.time() * 1000))[-8:]

    def tearDown(self):
        self.db.close()

    def test_builtin_questionnaires_idempotent(self):
        class FakeSettings:
            APP_ENV = "demo"
            INIT_BUILTIN_QUESTIONNAIRES = True
            INIT_DEMO_DATA = False
            INIT_DEFAULT_SCHOOL = False

        initialize_seed_data(self.db, FakeSettings())
        first = {q.code: q.builtin_content_hash for q in self.db.query(Questionnaire).filter(Questionnaire.is_builtin == True).all()}
        initialize_seed_data(self.db, FakeSettings())
        second = {q.code: q.builtin_content_hash for q in self.db.query(Questionnaire).filter(Questionnaire.is_builtin == True).all()}
        self.assertEqual(first, second)

    def test_builtin_questionnaires_have_required_fields(self):
        class FakeSettings:
            APP_ENV = "demo"
            INIT_BUILTIN_QUESTIONNAIRES = True
            INIT_DEMO_DATA = False
            INIT_DEFAULT_SCHOOL = False

        initialize_seed_data(self.db, FakeSettings())
        builtins = self.db.query(Questionnaire).filter(
            Questionnaire.is_builtin == True,
            Questionnaire.code.is_not(None),
            Questionnaire.status == "active",
        ).all()
        self.assertGreater(len(builtins), 0)
        self.assertEqual(
            self.db.query(Questionnaire).filter(
                Questionnaire.is_builtin == True,
                Questionnaire.code.is_(None),
                Questionnaire.status == "active",
            ).count(),
            0,
        )
        seen = set()
        for q in builtins:
            self.assertTrue(q.code)
            self.assertNotIn(q.code, seen)
            seen.add(q.code)
            self.assertIsNotNone(q.disclaimer)
            self.assertIsInstance(q.dimensions or [], list)
            self.assertIsInstance(q.scoring_rule or {}, dict)
            self.assertIsInstance(q.risk_rules or {}, dict)
            self.assertTrue(q.builtin_content_hash is not None)

    def test_custom_questionnaire_create_update_persists_rule_fields(self):
        school = School(name=f"规则学校{self.suffix}", code=f"QR{self.suffix}")
        self.db.add(school)
        self.db.flush()
        teacher = User(school_id=school.id, username=f"teacher_{self.suffix}", password_hash="", real_name="教师", role="teacher")
        self.db.add(teacher)
        self.db.flush()

        created = create_questionnaire(self.db, QuestionnaireCreate(
            title="自建问卷",
            description="说明",
            category="custom",
            applicable_grades="初一,初二",
            disclaimer="仅供参考",
            dimensions=[{"code": "emotion", "title": "情绪状态"}],
            scoring_rule={"method": "sum", "score_types": ["single_choice"]},
            risk_rules={"total_score_ranges": [{"min": 0, "max": 10, "level": "low"}]},
            quality_rules={"same_option_ratio_high": 0.8},
            source_type="school_custom",
        ), teacher.id, school.id)

        self.assertEqual(created.disclaimer, "仅供参考")
        self.assertEqual(created.dimensions, [{"code": "emotion", "title": "情绪状态"}])
        self.assertEqual(created.scoring_rule["method"], "sum")
        self.assertEqual(created.risk_rules["total_score_ranges"][0]["level"], "low")
        self.assertEqual(created.quality_rules["same_option_ratio_high"], 0.8)
        self.assertEqual(created.source_type, "school_custom")

        updated = update_questionnaire(self.db, created.id, QuestionnaireUpdate(
            disclaimer="更新后的说明",
            dimensions=[{"code": "sleep", "title": "睡眠状态"}],
            scoring_rule={"method": "sum", "score_types": ["single_choice", "scale"]},
            risk_rules={"messages": {"low": "正常"}},
            quality_rules={"same_display_position_ratio": 0.8},
            source_type="school_custom",
        ))
        self.assertEqual(updated.disclaimer, "更新后的说明")
        self.assertEqual(updated.dimensions, [{"code": "sleep", "title": "睡眠状态"}])
        self.assertEqual(updated.scoring_rule["score_types"], ["single_choice", "scale"])
        self.assertEqual(updated.risk_rules["messages"]["low"], "正常")
        self.assertEqual(updated.quality_rules["same_display_position_ratio"], 0.8)


if __name__ == "__main__":
    unittest.main()
