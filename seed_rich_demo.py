"""重建真实可用的演示数据。

用途：服务器演示环境清空旧业务样例后，重建多学校、多年级、多角色、任务、答卷、风险、干预闭环数据。
保留 platform_admin 和 school_admin 账号，清除 teacher/counselor/student 及其业务数据。
"""

import random
import sys
from datetime import datetime, timedelta, timezone

try:
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent
    BACKEND = ROOT / "backend"
    if BACKEND.exists():
        sys.path.insert(0, str(BACKEND))
    else:
        sys.path.insert(0, "/www/wwwroot/qingshaonian/backend")
except NameError:
    sys.path.insert(0, "/www/wwwroot/qingshaonian/backend")

from app.database import SessionLocal
from app.models.questionnaire import Option, Question, Questionnaire
from app.models.risk import Intervention, QualityAssessment, RiskAlert, ScoringResult
from app.models.system_config import SystemConfig
from app.models.task import AnswerRecord, AnswerSheet, Task
from app.models.user import Class, Grade, School, TeacherClass, User
from app.questionnaire_bank import ensure_builtin_questionnaires
from app.services import scoring_service
from app.utils.password import hash_password

random.seed(20260528)
tz = timezone(timedelta(hours=8))
now = datetime.now(tz).replace(microsecond=0)
PASSWORD = "Demo@123456"

SCHOOLS = [
    {
        "code": "QS-DEMO-01",
        "name": "金盾护苗市第一实验学校",
        "address": "金盾护苗市朝阳区育才路 18 号",
        "phone": "010-66010001",
        "grades": ["五年级", "六年级", "初一", "初二", "初三"],
        "class_count": 2,
    },
    {
        "code": "QS-DEMO-02",
        "name": "金盾护苗市第二中学",
        "address": "金盾护苗市海淀区知行路 6 号",
        "phone": "010-66020002",
        "grades": ["初一", "初二", "初三", "高一", "高二"],
        "class_count": 2,
    },
    {
        "code": "QS-DEMO-03",
        "name": "金盾护苗市职业技术学校",
        "address": "金盾护苗市经开区匠心大道 9 号",
        "phone": "010-66030003",
        "grades": ["职一", "职二", "职三"],
        "class_count": 3,
    },
]

TEACHER_TYPES = [
    ("班主任", "teacher", "head_teacher"),
    ("心理老师", "counselor", "counselor"),
    ("德育老师", "teacher", "moral_edu"),
    ("年级主任", "teacher", "grade_director"),
]

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
BOY_NAMES = ["明轩", "浩然", "子涵", "宇航", "嘉豪", "梓睿", "一诺", "俊杰", "泽宇", "承泽", "思远", "奕辰"]
GIRL_NAMES = ["雨桐", "梓涵", "欣怡", "诗涵", "若曦", "佳宁", "思琪", "语晨", "梦瑶", "可欣", "雅婷", "悦然"]


def school_id_for_username(index: int) -> str:
    return f"D{index:02d}"


def ensure_school_admin(db, school: School, index: int) -> None:
    username = f"admin_{school_id_for_username(index).lower()}"
    admin = db.query(User).filter(User.username == username).first()
    if not admin:
        db.add(User(
            school_id=school.id,
            username=username,
            password_hash=hash_password(PASSWORD),
            real_name=f"{school.name}管理员",
            role="school_admin",
            status=True,
        ))
    else:
        admin.school_id = school.id
        admin.real_name = f"{school.name}管理员"
        admin.role = "school_admin"
        admin.status = True
        admin.password_hash = hash_password(PASSWORD)


def clean_business_data(db) -> None:
    print("Cleaning old demo/business data ...")
    db.query(Intervention).delete(synchronize_session=False)
    db.query(QualityAssessment).delete(synchronize_session=False)
    db.query(ScoringResult).delete(synchronize_session=False)
    db.query(RiskAlert).delete(synchronize_session=False)
    db.query(AnswerRecord).delete(synchronize_session=False)
    db.query(AnswerSheet).delete(synchronize_session=False)
    db.query(Task).delete(synchronize_session=False)

    for klass in db.query(Class).all():
        klass.head_teacher_id = None
        klass.counselor_id = None
    db.flush()

    db.query(TeacherClass).delete(synchronize_session=False)
    db.query(User).filter(User.role.in_(["teacher", "counselor", "student"])).delete(synchronize_session=False)
    db.query(Class).delete(synchronize_session=False)
    db.query(Grade).delete(synchronize_session=False)
    db.query(SystemConfig).filter(SystemConfig.school_id.isnot(None)).delete(synchronize_session=False)
    db.commit()


def ensure_demo_schools(db) -> list[School]:
    schools: list[School] = []
    for index, spec in enumerate(SCHOOLS, start=1):
        school = db.query(School).filter(School.code == spec["code"]).first()
        if not school:
            school = School(code=spec["code"], name=spec["name"], address=spec["address"], phone=spec["phone"], status=True)
            db.add(school)
            db.flush()
        else:
            school.name = spec["name"]
            school.address = spec["address"]
            school.phone = spec["phone"]
            school.status = True
        ensure_school_admin(db, school, index)
        schools.append(school)
    db.commit()
    return schools


def create_grades_and_classes(db, school: School, spec: dict) -> list[Class]:
    classes: list[Class] = []
    for grade_index, grade_name in enumerate(spec["grades"], start=1):
        grade = Grade(school_id=school.id, name=grade_name, sort_order=grade_index, status=True)
        db.add(grade)
        db.flush()
        for class_index in range(1, spec["class_count"] + 1):
            klass = Class(school_id=school.id, grade_id=grade.id, name=f"{class_index}班", status=True)
            db.add(klass)
            db.flush()
            classes.append(klass)
    return classes


def create_teachers(db, school: School, classes: list[Class], school_index: int) -> list[User]:
    teachers: list[User] = []
    teacher_no = 1
    for grade_group in range(max(4, len(classes) // 2)):
        role_name, role, teacher_type = TEACHER_TYPES[grade_group % len(TEACHER_TYPES)]
        teacher = User(
            school_id=school.id,
            username=f"t_{school_id_for_username(school_index).lower()}_{teacher_no:02d}",
            password_hash=hash_password(PASSWORD),
            real_name=f"{random.choice(SURNAMES)}{role_name}",
            role=role,
            teacher_type=teacher_type,
            gender="女" if role == "counselor" else random.choice(["男", "女"]),
            phone=f"138{school_index:02d}{teacher_no:06d}",
            status=True,
        )
        db.add(teacher)
        db.flush()
        teachers.append(teacher)
        teacher_no += 1

    head_teachers = [t for t in teachers if t.teacher_type == "head_teacher"] or teachers[:2]
    counselors = [t for t in teachers if t.role == "counselor"] or teachers[:1]
    for idx, klass in enumerate(classes):
        head_teacher = head_teachers[idx % len(head_teachers)]
        counselor = counselors[idx % len(counselors)]
        klass.head_teacher_id = head_teacher.id
        klass.counselor_id = counselor.id
        db.add(TeacherClass(teacher_id=head_teacher.id, class_id=klass.id))
        db.add(TeacherClass(teacher_id=counselor.id, class_id=klass.id))
    return teachers


def create_students(db, school: School, classes: list[Class], school_index: int) -> list[User]:
    students: list[User] = []
    counter = 1
    for klass in classes:
        for i in range(8):
            is_boy = i % 2 == 0
            name = random.choice(SURNAMES) + random.choice(BOY_NAMES if is_boy else GIRL_NAMES)
            username = f"s_{school_id_for_username(school_index).lower()}_{counter:03d}"
            student_no = f"2026{school_index:02d}{counter:04d}"
            student = User(
                school_id=school.id,
                username=username,
                password_hash=hash_password(PASSWORD),
                real_name=name,
                role="student",
                gender="男" if is_boy else "女",
                student_no=student_no,
                grade_id=klass.grade_id,
                class_id=klass.id,
                status=True,
            )
            db.add(student)
            db.flush()
            students.append(student)
            counter += 1
    return students


def question_options(db, question: Question) -> list[Option]:
    options = db.query(Option).filter(Option.question_id == question.id).order_by(Option.sort_order, Option.id).all()
    return options


def choose_option(question: Question, options: list[Option], profile: str) -> Option | None:
    if not options:
        return None
    if question.is_attention_check:
        if profile == "invalid":
            return next((opt for opt in options if opt.content != question.attention_correct_answer), options[0])
        return next((opt for opt in options if opt.content == question.attention_correct_answer), options[-1])

    sorted_options = sorted(options, key=lambda item: item.score or 0)
    low = sorted_options[0]
    mid = sorted_options[len(sorted_options) // 2]
    high = sorted_options[-1]

    if profile == "urgent":
        return high
    if profile == "high":
        return high if random.random() < 0.75 else mid
    if profile == "medium":
        return mid if random.random() < 0.8 else random.choice([low, high])
    if profile in {"invalid", "pattern"}:
        return sorted_options[0]
    return low if random.random() < 0.85 else mid


def fill_answers(db, sheet: AnswerSheet, profile: str, duration_base: int) -> None:
    questions = db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id).order_by(Question.sort_order, Question.id).all()
    sheet.question_order = [question.id for question in questions]
    for order, question in enumerate(questions, start=1):
        options = question_options(db, question)
        selected = choose_option(question, options, profile)
        if not selected:
            continue
        duration = 2 if profile in {"invalid", "pattern"} else random.randint(max(3, duration_base - 2), duration_base + 4)
        db.add(AnswerRecord(
            answer_sheet_id=sheet.id,
            question_id=question.id,
            question_type=question.type,
            answer_content={"selected_option_id": selected.id},
            score=selected.score or 0,
            duration_seconds=duration,
            displayed_order=order,
            selected_display_index=max(order - 1, 0),
        ))


def ensure_demo_risk_alert(db, sheet: AnswerSheet, profile: str, teacher_id: int | None) -> None:
    if profile not in {"medium", "high", "urgent"}:
        return
    exists = db.query(RiskAlert).filter(RiskAlert.answer_sheet_id == sheet.id).first()
    if exists:
        return
    risk_level = "urgent" if profile == "urgent" else "high" if profile == "high" else "medium"
    risk_type = {
        "medium": "学习与情绪压力关注信号",
        "high": "持续情绪压力关注信号",
        "urgent": "重点关注信号",
    }[profile]
    db.add(RiskAlert(
        school_id=sheet.school_id,
        student_id=sheet.student_id,
        answer_sheet_id=sheet.id,
        task_id=sheet.task_id,
        risk_level=risk_level,
        risk_type=risk_type,
        trigger_method="demo_profile",
        trigger_detail={"source": "demo_seed", "profile": profile},
        assigned_teacher_id=teacher_id,
        status="pending",
        due_at=now + timedelta(days=7 if risk_level != "urgent" else 3),
        source_rule_version="demo-v1",
    ))


def create_task_with_answers(db, school: School, questionnaire: Questionnaire, name: str, target_classes: list[Class], creator: User, days_ago: int, profile_cycle: list[str]) -> Task:
    task = Task(
        school_id=school.id,
        questionnaire_id=questionnaire.id,
        name=name,
        target_type="class",
        target_ids=[klass.id for klass in target_classes],
        start_time=now - timedelta(days=days_ago),
        end_time=now + timedelta(days=max(3, 21 - days_ago)),
        published_at=now - timedelta(days=days_ago, hours=2),
        reminder_strategy={"type": "deadline_24h"},
        description=f"{school.name}{name}，用于演示学校测评发布、学生作答、风险提示与后续干预流程。",
        allow_edit=days_ago <= 7,
        shuffle_questions=True,
        shuffle_options=True,
        enable_quality_check=True,
        status="in_progress",
        created_by=creator.id,
    )
    db.add(task)
    db.flush()

    target_students = db.query(User).filter(User.school_id == school.id, User.role == "student", User.class_id.in_([klass.id for klass in target_classes])).order_by(User.id).all()
    task.target_snapshot = {"student_ids": [student.id for student in target_students], "target_type": "class", "target_ids": task.target_ids}

    submitted_limit = int(len(target_students) * 0.82)
    in_progress_limit = submitted_limit + max(1, int(len(target_students) * 0.08))
    for idx, student in enumerate(target_students):
        if idx >= in_progress_limit:
            continue
        status = "submitted" if idx < submitted_limit else "in_progress"
        started_at = now - timedelta(days=max(0, days_ago - 1), hours=random.randint(1, 8), minutes=idx)
        duration = random.randint(380, 1260)
        submitted_at = started_at + timedelta(seconds=duration) if status == "submitted" else None
        sheet = AnswerSheet(
            school_id=school.id,
            class_id=student.class_id,
            task_id=task.id,
            student_id=student.id,
            questionnaire_id=questionnaire.id,
            status=status,
            started_at=started_at,
            submitted_at=submitted_at,
            total_duration_seconds=duration if submitted_at else 0,
            ip_address=f"10.{school.id % 250}.{(idx // 255) + 1}.{idx % 255}",
            user_agent="Demo Browser",
        )
        db.add(sheet)
        db.flush()
        if status == "submitted":
            profile = profile_cycle[idx % len(profile_cycle)]
            fill_answers(db, sheet, profile, duration_base=max(4, duration // max(1, len(task.target_snapshot["student_ids"]))))
            scoring_service.calculate_scores(db, sheet.id)
            scoring_service.calculate_quality(db, sheet.id)
            scoring_service.check_risk_alerts(db, sheet.id)
            ensure_demo_risk_alert(db, sheet, profile, creator.id)
    db.commit()
    return task


def attach_interventions(db, school: School, teachers: list[User]) -> int:
    alerts = db.query(RiskAlert).filter(RiskAlert.school_id == school.id).order_by(RiskAlert.id).all()
    count = 0
    for idx, alert in enumerate(alerts[:12]):
        teacher = teachers[idx % len(teachers)]
        status = ["completed", "follow_up", "processing", "pending"][idx % 4]
        need_follow_up = status in {"follow_up", "processing", "pending"}
        db.add(Intervention(
            school_id=school.id,
            student_id=alert.student_id,
            risk_alert_id=alert.id,
            teacher_id=teacher.id,
            intervention_time=now - timedelta(days=max(0, 6 - idx % 6), hours=idx),
            method=["student_talk", "counselor_guidance", "family_school", "parent_communication", "observation"][idx % 5],
            content="已结合测评结果与班级日常观察开展关怀沟通，重点了解近期学习压力、同伴关系和睡眠状态。",
            result=["学生愿意继续沟通，当前状态总体稳定。", "已与家长同步情况，后续由班主任和心理老师联合关注。", "需要持续跟进，建议一周内复访。", "已建立观察记录，等待下一次沟通。"] [idx % 4],
            follow_up_suggestion="建议班主任、心理老师和家长保持低压力沟通，两周内完成一次复评或访谈。",
            need_follow_up=need_follow_up,
            next_follow_up_time=now + timedelta(days=7 + idx) if need_follow_up else None,
            status=status,
            closed_at=now - timedelta(days=1) if status == "completed" else None,
        ))
        if status == "completed":
            alert.status = "completed"
            alert.latest_handled_at = now - timedelta(days=1)
        elif status == "follow_up":
            alert.status = "follow_up"
            alert.latest_handled_at = now - timedelta(days=2)
        elif status == "processing":
            alert.status = "processing"
            alert.latest_handled_at = now - timedelta(days=3)
        count += 1
    db.commit()
    return count


def create_school_configs(db, school: School) -> None:
    configs = {
        "screen_title": f"{school.name}学生关怀数据大屏",
        "screen_subtitle": "测评进度、风险提示、干预跟进一屏掌握",
        "fast_answer_threshold": "30",
        "consecutive_same_threshold": "5",
    }
    for key, value in configs.items():
        db.add(SystemConfig(school_id=school.id, config_key=key, config_value=value, description=f"演示配置 - {key}"))


def main() -> None:
    db = SessionLocal()
    try:
        ensure_builtin_questionnaires(db)
        clean_business_data(db)
        schools = ensure_demo_schools(db)
        questionnaires = {q.code: q for q in db.query(Questionnaire).filter(Questionnaire.is_builtin == True, Questionnaire.status == "active").all()}
        if not questionnaires:
            raise RuntimeError("未找到内置问卷，无法创建演示任务")

        grand_totals = {"schools": 0, "grades": 0, "classes": 0, "teachers": 0, "students": 0, "tasks": 0, "answers": 0, "risks": 0, "interventions": 0}
        for school_index, (school, spec) in enumerate(zip(schools, SCHOOLS), start=1):
            classes = create_grades_and_classes(db, school, spec)
            teachers = create_teachers(db, school, classes, school_index)
            students = create_students(db, school, classes, school_index)
            create_school_configs(db, school)
            db.commit()

            by_grade: dict[str, list[Class]] = {}
            for klass in classes:
                grade = db.query(Grade).filter(Grade.id == klass.grade_id).first()
                by_grade.setdefault(grade.name, []).append(klass)

            task_specs = [
                ("全校综合风险筛查", "builtin-comprehensive-risk-v1", classes[: min(8, len(classes))], 15, ["low", "low", "medium", "high", "urgent", "pattern", "low", "medium", "invalid"]),
                ("情绪状态关注筛查", "builtin-emotion-phq-like-v1", classes[: min(4, len(classes))], 10, ["low", "medium", "high", "low", "urgent", "medium"]),
                ("焦虑压力筛查", "builtin-anxiety-gad-like-v1", classes[-min(4, len(classes)):], 7, ["low", "low", "medium", "high", "pattern"]),
                ("校园欺凌排查", "builtin-bullying-risk-v1", classes[::2] or classes[:1], 5, ["low", "medium", "high", "urgent", "low"]),
                ("网络使用习惯评估", "builtin-internet-risk-v1", classes[1::2] or classes[:1], 3, ["low", "medium", "medium", "high", "low"]),
            ]
            if "builtin-academic-pressure-v1" in questionnaires:
                task_specs.append(("学习压力测评", "builtin-academic-pressure-v1", classes[: min(3, len(classes))], 1, ["low", "medium", "high", "low"]))
            if "builtin-interpersonal-adaptation-v1" in questionnaires:
                task_specs.append(("人际适应调查", "builtin-interpersonal-adaptation-v1", classes[-min(3, len(classes)):], 0, ["low", "medium", "low", "high"]))

            tasks = []
            for name, code, target_classes, days_ago, cycle in task_specs:
                questionnaire = questionnaires.get(code)
                if questionnaire and target_classes:
                    tasks.append(create_task_with_answers(db, school, questionnaire, name, target_classes, teachers[0], days_ago, cycle))

            interventions = attach_interventions(db, school, teachers)
            answers = db.query(AnswerSheet).filter(AnswerSheet.school_id == school.id).count()
            risks = db.query(RiskAlert).filter(RiskAlert.school_id == school.id).count()
            print(f"{school.name}: grades={len(spec['grades'])}, classes={len(classes)}, teachers={len(teachers)}, students={len(students)}, tasks={len(tasks)}, answers={answers}, risks={risks}, interventions={interventions}")

            grand_totals["schools"] += 1
            grand_totals["grades"] += len(spec["grades"])
            grand_totals["classes"] += len(classes)
            grand_totals["teachers"] += len(teachers)
            grand_totals["students"] += len(students)
            grand_totals["tasks"] += len(tasks)
            grand_totals["answers"] += answers
            grand_totals["risks"] += risks
            grand_totals["interventions"] += interventions

        print("\nDemo accounts:")
        print(f"  platform_admin: 保留原账号 / 原密码")
        for index, school in enumerate(schools, start=1):
            print(f"  school_admin: admin_{school_id_for_username(index).lower()} / {PASSWORD} / {school.name}")
            print(f"  teacher:      t_{school_id_for_username(index).lower()}_01 / {PASSWORD}")
            print(f"  student:      s_{school_id_for_username(index).lower()}_001 / {PASSWORD}")
        print("\nTotals:", grand_totals)
    finally:
        db.close()


if __name__ == "__main__":
    main()
