import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.questionnaire import Questionnaire
from ..models.risk import Intervention
from ..models.task import AnswerRecord, AnswerSheet, Task
from ..models.user import Class, TeacherClass, User
from ..utils.password import hash_password
from . import scoring_service


tz = timezone(timedelta(hours=8))


def seed_demo_school_data(db: Session, school_id: int) -> bool:
    existing_students = db.query(User).filter(User.school_id == school_id, User.role == "student").count()
    if existing_students > 0:
        return False

    classes = db.query(Class).filter(Class.school_id == school_id, Class.status == True).order_by(Class.id).all()
    if not classes:
        return False

    existing_teachers = db.query(User).filter(User.school_id == school_id, User.role.in_(["teacher", "counselor"])).all()
    if existing_teachers:
        teachers = existing_teachers
    else:
        teachers = []
        for idx, name in enumerate(["张老师", "李老师", "王老师", "赵老师"], start=1):
            teacher = User(
                school_id=school_id,
                username=f"T{school_id:02d}{idx:02d}",
                password_hash=hash_password("DemoTeach123"),
                real_name=name,
                role="teacher",
                status=True,
            )
            db.add(teacher)
            db.flush()
            teachers.append(teacher)
            if idx - 1 < len(classes):
                db.add(TeacherClass(teacher_id=teacher.id, class_id=classes[idx - 1].id))
                classes[idx - 1].head_teacher_id = teacher.id
        db.flush()

    surnames = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴"]
    names = ["明", "华", "磊", "芳", "婷", "杰", "琳", "浩", "雪", "涛", "思", "晨"]
    students = []
    counter = 1
    for klass in classes[: min(len(classes), 4)]:
        for _ in range(6):
            username = f"DEMO{school_id:03d}{counter:04d}"
            student_no = f"STU{school_id:03d}{counter:04d}"
            student = User(
                school_id=school_id,
                username=username,
                password_hash=hash_password("DemoStu123"),
                real_name=random.choice(surnames) + random.choice(names),
                role="student",
                status=True,
                grade_id=klass.grade_id,
                class_id=klass.id,
                student_no=student_no,
            )
            db.add(student)
            db.flush()
            students.append(student)
            counter += 1

    questionnaires = {
        q.code: q
        for q in db.query(Questionnaire).filter(
            Questionnaire.is_builtin == True,
            Questionnaire.status == "active",
        ).all()
    }
    if not questionnaires:
        return False

    task_specs = []
    if "builtin-comprehensive-risk-v1" in questionnaires:
        task_specs.append(("综合关注筛查", questionnaires["builtin-comprehensive-risk-v1"], [klass.id for klass in classes[:2]]))
    if "builtin-emotion-phq-like-v1" in questionnaires:
        task_specs.append(("情绪状态关注筛查", questionnaires["builtin-emotion-phq-like-v1"], [klass.id for klass in classes[:3]]))

    for title, questionnaire, class_ids in task_specs:
        teacher = teachers[0]
        task = Task(
            school_id=school_id,
            questionnaire_id=questionnaire.id,
            name=title,
            target_type="class",
            target_ids=class_ids,
            status="in_progress",
            published_at=datetime.now(tz) - timedelta(days=2),
            start_time=datetime.now(tz) - timedelta(days=2),
            end_time=datetime.now(tz) + timedelta(days=5),
            created_by=teacher.id,
            description="演示数据任务",
        )
        db.add(task)
        db.flush()

        target_students = [student for student in students if student.class_id in class_ids]
        for index, student in enumerate(target_students):
            sheet = AnswerSheet(
                school_id=school_id,
                class_id=student.class_id,
                task_id=task.id,
                student_id=student.id,
                questionnaire_id=questionnaire.id,
                status="submitted",
                started_at=datetime.now(tz) - timedelta(minutes=15 + index),
                submitted_at=datetime.now(tz) - timedelta(minutes=5 + index),
            )
            db.add(sheet)
            db.flush()
            _fill_mock_answers(db, sheet, risk_mode=index % 5 == 0)
            scoring_service.calculate_scores(db, sheet.id)
            scoring_service.calculate_quality(db, sheet.id)
            scoring_service.check_risk_alerts(db, sheet.id)

    db.flush()
    first_teacher = teachers[0]
    first_student = students[0]
    db.add(
        Intervention(
            school_id=school_id,
            student_id=first_student.id,
            teacher_id=first_teacher.id,
            method="student_talk",
            content="已完成演示初始化后的首次关怀沟通。",
            result="学生愿意继续沟通。",
            follow_up_suggestion="建议一周后继续了解近期学习与睡眠状态。",
            need_follow_up=True,
            status="follow_up",
            next_follow_up_time=datetime.now(tz) + timedelta(days=7),
        )
    )
    db.commit()
    return True


def _fill_mock_answers(db: Session, sheet: AnswerSheet, risk_mode: bool = False) -> None:
    questions = (
        db.query(scoring_service.Question)
        .filter(scoring_service.Question.questionnaire_id == sheet.questionnaire_id)
        .order_by(scoring_service.Question.sort_order)
        .all()
    )
    sheet.question_order = [question.id for question in questions]
    for order, question in enumerate(questions, start=1):
        options = db.query(scoring_service.Option).filter(scoring_service.Option.question_id == question.id).order_by(scoring_service.Option.sort_order).all()
        if not options:
            continue
        if question.is_attention_check:
            selected = next((item for item in options if item.content == question.attention_correct_answer), options[-1])
        elif risk_mode and (question.risk_tag in {"self_safety", "bullying"} or not question.is_reverse):
            selected = options[-1]
        else:
            selected = options[1] if len(options) > 1 else options[0]
        db.add(
            AnswerRecord(
                answer_sheet_id=sheet.id,
                question_id=question.id,
                question_type=question.type,
                answer_content={"selected_option_id": selected.id},
                displayed_order=order,
                duration_seconds=5 if not risk_mode else 3,
            )
        )
