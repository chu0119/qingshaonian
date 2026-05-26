import time
import unittest
from dataclasses import dataclass

from app.database import Base, SessionLocal, engine, init_db
from app.models.questionnaire import ContradictionGroup, Option, Question, Questionnaire
from app.models.task import AnswerRecord, AnswerSheet, Task
from app.models.user import School, User


@dataclass
class FakeSettings:
    APP_ENV: str = "demo"
    INIT_BUILTIN_QUESTIONNAIRES: bool = True
    INIT_DEMO_DATA: bool = False


class QuestionnaireBankAndScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        init_db()

    def setUp(self):
        self.db = SessionLocal()
        self.suffix = str(int(time.time() * 1000))[-8:]

    def tearDown(self):
        self.db.close()

    def test_builtin_questionnaires_are_system_level_and_idempotent(self):
        from app.services.seed_service import initialize_seed_data

        initialize_seed_data(self.db, FakeSettings(APP_ENV="demo", INIT_BUILTIN_QUESTIONNAIRES=True, INIT_DEMO_DATA=False))
        first = {
            row.code: row.id
            for row in self.db.query(Questionnaire).filter(
                Questionnaire.is_builtin == True,
                Questionnaire.code.is_not(None),
                Questionnaire.status == "active",
            ).all()
        }
        initialize_seed_data(self.db, FakeSettings(APP_ENV="demo", INIT_BUILTIN_QUESTIONNAIRES=True, INIT_DEMO_DATA=False))
        second = {
            row.code: row.id
            for row in self.db.query(Questionnaire).filter(
                Questionnaire.is_builtin == True,
                Questionnaire.code.is_not(None),
                Questionnaire.status == "active",
            ).all()
        }

        self.assertGreaterEqual(len(first), 8)
        self.assertEqual(first, second)
        self.assertTrue(all(row is not None for row in first.keys()))
        self.assertEqual(
            self.db.query(Questionnaire).filter(Questionnaire.is_builtin == True, Questionnaire.school_id.is_not(None)).count(),
            0,
        )

    def test_production_never_seeds_demo_students_or_answers(self):
        from app.services.seed_service import initialize_seed_data

        before_students = self.db.query(User).filter(User.username.like("S2024%")).count()
        before_sheets = self.db.query(AnswerSheet).count()

        initialize_seed_data(self.db, FakeSettings(APP_ENV="production", INIT_BUILTIN_QUESTIONNAIRES=False, INIT_DEMO_DATA=True))

        after_students = self.db.query(User).filter(User.username.like("S2024%")).count()
        after_sheets = self.db.query(AnswerSheet).count()
        self.assertEqual(before_students, after_students)
        self.assertEqual(before_sheets, after_sheets)

    def test_calculate_scores_uses_per_question_max_and_single_reverse(self):
        from app.services.scoring_service import calculate_scores

        school = School(name=f"评分学校{self.suffix}", code=f"SC{self.suffix}")
        self.db.add(school)
        self.db.flush()
        questionnaire = Questionnaire(
            school_id=school.id,
            title="评分测试问卷",
            category="custom",
            status="active",
            scoring_rule={"score_types": ["single_choice", "scale"]},
            risk_rules={"total_score_ranges": [{"min": 0, "max": 100, "level": "low"}]},
        )
        self.db.add(questionnaire)
        self.db.flush()

        q1 = Question(questionnaire_id=questionnaire.id, title="正向题", type="single_choice", sort_order=1, dimension="emotion")
        q2 = Question(questionnaire_id=questionnaire.id, title="反向题", type="single_choice", sort_order=2, dimension="emotion", is_reverse=True)
        q3 = Question(questionnaire_id=questionnaire.id, title="注意力题", type="single_choice", sort_order=3, dimension="emotion", is_attention_check=True, attention_correct_answer="总是")
        q4 = Question(questionnaire_id=questionnaire.id, title="简答题", type="short_answer", sort_order=4, dimension="sleep")
        self.db.add_all([q1, q2, q3, q4])
        self.db.flush()

        for question in (q1, q2):
            for idx, score in enumerate([0, 1, 2, 3, 4], start=1):
                self.db.add(Option(question_id=question.id, content=f"选项{idx}", score=score, sort_order=idx))
        for idx, label in enumerate(["从不", "偶尔", "经常", "总是"], start=1):
            self.db.add(Option(question_id=q3.id, content=label, score=0, sort_order=idx))
        self.db.flush()

        student = User(school_id=school.id, username=f"score_{self.suffix}", password_hash="", real_name="学生", role="student")
        self.db.add(student)
        self.db.flush()
        task = Task(school_id=school.id, questionnaire_id=questionnaire.id, name="评分任务", target_type="student", target_ids=[student.id], status="in_progress")
        self.db.add(task)
        self.db.flush()
        sheet = AnswerSheet(school_id=school.id, task_id=task.id, student_id=student.id, questionnaire_id=questionnaire.id, status="submitted")
        self.db.add(sheet)
        self.db.flush()

        q1_high = self.db.query(Option).filter(Option.question_id == q1.id, Option.score == 4).first()
        q2_low = self.db.query(Option).filter(Option.question_id == q2.id, Option.score == 0).first()
        q3_ok = self.db.query(Option).filter(Option.question_id == q3.id, Option.content == "总是").first()
        self.db.add_all([
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q1.id, question_type=q1.type, answer_content={"selected_option_id": q1_high.id}, displayed_order=1),
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q2.id, question_type=q2.type, answer_content={"selected_option_id": q2_low.id}, displayed_order=2),
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q3.id, question_type=q3.type, answer_content={"selected_option_id": q3_ok.id}, displayed_order=3),
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q4.id, question_type=q4.type, answer_content={"text": "测试"}, displayed_order=4),
        ])
        self.db.commit()

        result = calculate_scores(self.db, sheet.id)
        self.assertEqual(result["total_score"], 8)
        self.assertEqual(result["total_max_score"], 8)
        self.assertEqual(result["total_score_pct"], 100.0)
        reverse_record = self.db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet.id, AnswerRecord.question_id == q2.id).first()
        self.assertEqual(reverse_record.score, 4)

    def test_dimension_percentages_use_dimension_max_score(self):
        from app.services.scoring_service import calculate_scores

        school = School(name=f"维度学校{self.suffix}", code=f"DM{self.suffix}")
        self.db.add(school)
        self.db.flush()
        questionnaire = Questionnaire(
            school_id=school.id,
            title="维度测试问卷",
            category="custom",
            status="active",
            scoring_rule={"score_types": ["single_choice"]},
            risk_rules={"total_score_ranges": [{"min": 0, "max": 100, "level": "low"}]},
        )
        self.db.add(questionnaire)
        self.db.flush()
        q1 = Question(questionnaire_id=questionnaire.id, title="情绪题", type="single_choice", sort_order=1, dimension="emotion")
        q2 = Question(questionnaire_id=questionnaire.id, title="睡眠题1", type="single_choice", sort_order=2, dimension="sleep")
        q3 = Question(questionnaire_id=questionnaire.id, title="睡眠题2", type="single_choice", sort_order=3, dimension="sleep")
        self.db.add_all([q1, q2, q3])
        self.db.flush()
        for question in (q1, q2, q3):
            for idx, score in enumerate([0, 2, 4], start=1):
                self.db.add(Option(question_id=question.id, content=f"选项{idx}", score=score, sort_order=idx))
        self.db.flush()

        student = User(school_id=school.id, username=f"dim_{self.suffix}", password_hash="", real_name="学生", role="student")
        self.db.add(student)
        self.db.flush()
        task = Task(school_id=school.id, questionnaire_id=questionnaire.id, name="维度任务", target_type="student", target_ids=[student.id], status="in_progress")
        self.db.add(task)
        self.db.flush()
        sheet = AnswerSheet(school_id=school.id, task_id=task.id, student_id=student.id, questionnaire_id=questionnaire.id, status="submitted")
        self.db.add(sheet)
        self.db.flush()
        pick = lambda q, score: self.db.query(Option).filter(Option.question_id == q.id, Option.score == score).first().id
        self.db.add_all([
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q1.id, question_type=q1.type, answer_content={"selected_option_id": pick(q1, 4)}, displayed_order=1),
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q2.id, question_type=q2.type, answer_content={"selected_option_id": pick(q2, 2)}, displayed_order=2),
            AnswerRecord(answer_sheet_id=sheet.id, question_id=q3.id, question_type=q3.type, answer_content={"selected_option_id": pick(q3, 0)}, displayed_order=3),
        ])
        self.db.commit()

        result = calculate_scores(self.db, sheet.id)
        self.assertEqual(result["dimension_breakdown"]["emotion"]["pct"], 100.0)
        self.assertEqual(result["dimension_breakdown"]["sleep"]["pct"], 25.0)

    def test_phq_like_builtin_uses_0_to_27_ranges(self):
        from app.services.scoring_service import calculate_scores
        from app.services.seed_service import initialize_seed_data

        initialize_seed_data(self.db, FakeSettings(APP_ENV="demo", INIT_BUILTIN_QUESTIONNAIRES=True, INIT_DEMO_DATA=False))
        questionnaire = self.db.query(Questionnaire).filter(Questionnaire.code == "builtin-emotion-phq-like-v1").first()
        self.assertIsNotNone(questionnaire)

        school = School(name=f"PHQ学校{self.suffix}", code=f"PHQ{self.suffix}")
        self.db.add(school)
        self.db.flush()
        student = User(school_id=school.id, username=f"phq_{self.suffix}", password_hash="", real_name="学生", role="student")
        self.db.add(student)
        self.db.flush()
        task = Task(school_id=school.id, questionnaire_id=questionnaire.id, name="PHQ任务", target_type="student", target_ids=[student.id], status="in_progress")
        self.db.add(task)
        self.db.flush()
        sheet = AnswerSheet(school_id=school.id, task_id=task.id, student_id=student.id, questionnaire_id=questionnaire.id, status="submitted")
        self.db.add(sheet)
        self.db.flush()

        questions = self.db.query(Question).filter(Question.questionnaire_id == questionnaire.id).order_by(Question.sort_order).all()
        for idx, question in enumerate(questions, start=1):
            option = self.db.query(Option).filter(Option.question_id == question.id, Option.score == 3).first()
            self.db.add(AnswerRecord(answer_sheet_id=sheet.id, question_id=question.id, question_type=question.type, answer_content={"selected_option_id": option.id}, displayed_order=idx))
        self.db.commit()

        result = calculate_scores(self.db, sheet.id)
        self.assertEqual(result["total_score"], 27)
        self.assertEqual(result["total_max_score"], 27)
        self.assertEqual(result["risk_level"], "urgent")

    def test_gad_like_builtin_uses_0_to_21_ranges(self):
        from app.services.scoring_service import calculate_scores
        from app.services.seed_service import initialize_seed_data

        initialize_seed_data(self.db, FakeSettings(APP_ENV="demo", INIT_BUILTIN_QUESTIONNAIRES=True, INIT_DEMO_DATA=False))
        questionnaire = self.db.query(Questionnaire).filter(Questionnaire.code == "builtin-anxiety-gad-like-v1").first()
        self.assertIsNotNone(questionnaire)

        school = School(name=f"GAD学校{self.suffix}", code=f"GAD{self.suffix}")
        self.db.add(school)
        self.db.flush()
        student = User(school_id=school.id, username=f"gad_{self.suffix}", password_hash="", real_name="学生", role="student")
        self.db.add(student)
        self.db.flush()
        task = Task(school_id=school.id, questionnaire_id=questionnaire.id, name="GAD任务", target_type="student", target_ids=[student.id], status="in_progress")
        self.db.add(task)
        self.db.flush()
        sheet = AnswerSheet(school_id=school.id, task_id=task.id, student_id=student.id, questionnaire_id=questionnaire.id, status="submitted")
        self.db.add(sheet)
        self.db.flush()

        questions = self.db.query(Question).filter(Question.questionnaire_id == questionnaire.id).order_by(Question.sort_order).all()
        for idx, question in enumerate(questions, start=1):
            option = self.db.query(Option).filter(Option.question_id == question.id, Option.score == 3).first()
            self.db.add(AnswerRecord(answer_sheet_id=sheet.id, question_id=question.id, question_type=question.type, answer_content={"selected_option_id": option.id}, displayed_order=idx))
        self.db.commit()

        result = calculate_scores(self.db, sheet.id)
        self.assertEqual(result["total_score"], 21)
        self.assertEqual(result["total_max_score"], 21)
        self.assertEqual(result["risk_level"], "urgent")

    def test_sensitive_option_can_trigger_risk(self):
        from app.services.scoring_service import calculate_scores

        school = School(name=f"风险学校{self.suffix}", code=f"RK{self.suffix}")
        self.db.add(school)
        self.db.flush()
        questionnaire = Questionnaire(
            school_id=school.id,
            title="欺凌风险问卷",
            category="bullying",
            status="active",
            risk_rules={
                "total_score_ranges": [{"min": 0, "max": 100, "level": "low"}],
                "risk_tag_rules": {"bullying": {"level": "high", "type_label": "校园欺凌关注信号"}},
            },
        )
        self.db.add(questionnaire)
        self.db.flush()
        question = Question(questionnaire_id=questionnaire.id, title="是否被同学威胁", type="single_choice", sort_order=1, dimension="campus_safety", risk_tag="bullying")
        self.db.add(question)
        self.db.flush()
        safe = Option(question_id=question.id, content="没有", score=0, sort_order=1, is_risk_option=False)
        risky = Option(question_id=question.id, content="经常", score=4, sort_order=2, is_risk_option=True)
        self.db.add_all([safe, risky])
        self.db.flush()
        student = User(school_id=school.id, username=f"risk_{self.suffix}", password_hash="", real_name="学生", role="student")
        self.db.add(student)
        self.db.flush()
        task = Task(school_id=school.id, questionnaire_id=questionnaire.id, name="风险任务", target_type="student", target_ids=[student.id], status="in_progress")
        self.db.add(task)
        self.db.flush()
        sheet = AnswerSheet(school_id=school.id, task_id=task.id, student_id=student.id, questionnaire_id=questionnaire.id, status="submitted")
        self.db.add(sheet)
        self.db.flush()
        self.db.add(AnswerRecord(answer_sheet_id=sheet.id, question_id=question.id, question_type=question.type, answer_content={"selected_option_id": risky.id}, displayed_order=1))
        self.db.commit()

        result = calculate_scores(self.db, sheet.id)
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("校园欺凌关注信号", result["risk_type"])

    def test_copy_questionnaire_rewrites_contradiction_group_question_ids(self):
        from app.services.questionnaire_service import copy_questionnaire

        school = School(name=f"复制学校{self.suffix}", code=f"CP{self.suffix}")
        self.db.add(school)
        self.db.flush()
        teacher = User(school_id=school.id, username=f"copy_{self.suffix}", password_hash="", real_name="教师", role="teacher")
        self.db.add(teacher)
        self.db.flush()
        questionnaire = Questionnaire(school_id=school.id, title="原问卷", category="custom", status="active", created_by=teacher.id)
        self.db.add(questionnaire)
        self.db.flush()
        q1 = Question(questionnaire_id=questionnaire.id, code="q1", title="题目一", type="single_choice", sort_order=1)
        q2 = Question(questionnaire_id=questionnaire.id, code="q2", title="题目二", type="single_choice", sort_order=2)
        self.db.add_all([q1, q2])
        self.db.flush()
        self.db.add_all([
            Option(question_id=q1.id, content="A", score=0, sort_order=1),
            Option(question_id=q2.id, content="B", score=0, sort_order=1),
            ContradictionGroup(questionnaire_id=questionnaire.id, question_a_id=q1.id, question_b_id=q2.id, relation_type="opposite", max_score_diff=2),
        ])
        self.db.commit()

        copied = copy_questionnaire(self.db, questionnaire.id, teacher.id, school.id)
        copied_question_ids = {
            question.id
            for question in self.db.query(Question).filter(Question.questionnaire_id == copied.id).all()
        }
        copied_groups = self.db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == copied.id).all()

        self.assertEqual(len(copied_groups), 1)
        self.assertIn(copied_groups[0].question_a_id, copied_question_ids)
        self.assertIn(copied_groups[0].question_b_id, copied_question_ids)
        self.assertNotEqual(copied_groups[0].question_a_id, q1.id)
        self.assertNotEqual(copied_groups[0].question_b_id, q2.id)


if __name__ == "__main__":
    unittest.main()
