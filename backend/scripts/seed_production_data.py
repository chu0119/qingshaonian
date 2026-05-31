"""
金盾护苗 - 演示数据初始化脚本

用法: cd /www/wwwroot/qingshaonian/backend && .venv/bin/python -m scripts.seed_production_data

生成虚构演示数据，所有名称后缀"(演示)"。
使用 scoring_service 真实评分流程生成答卷数据。
"""

import os
import sys
import random
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 确保 app 包可导入
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import School, Grade, Class, User, TeacherClass
from app.models.questionnaire import Questionnaire, Question, Option
from app.models.task import Task, AnswerSheet, AnswerRecord
from app.models.risk import ScoringResult, QualityAssessment, RiskAlert, Intervention
from app.utils.password import hash_password
from app.services import scoring_service

tz = timezone(timedelta(hours=8))

# ─── 虚构数据模板 ─────────────────────────────────────────

SCHOOL_TEMPLATES = [
    {"name": "青云中学(演示)", "code": "DEMO-QY", "address": "XX省XX市XX区青云路1号(演示)", "phone": "010-88001001"},
    {"name": "明德中学(演示)", "code": "DEMO-MD", "address": "XX省XX市XX区明德路2号(演示)", "phone": "010-88002002"},
    {"name": "星河中学(演示)", "code": "DEMO-XH", "address": "XX省XX市XX区星河路3号(演示)", "phone": "010-88003003"},
]

GRADE_NAMES = ["七年级", "八年级", "九年级"]

SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡", "林", "郭", "何", "高", "罗"]
GIVEN_NAMES = ["明", "华", "磊", "芳", "婷", "杰", "琳", "浩", "雪", "涛", "思", "晨", "伟", "丽", "静", "强", "敏", "军", "慧", "鑫"]

DEMO_SUFFIX = "(演示)"


def _random_name() -> str:
    return random.choice(SURNAMES) + random.choice(GIVEN_NAMES) + DEMO_SUFFIX


def _random_id_number(seq: int) -> str:
    """生成虚构的18位身份证号（9901开头避免与真实号冲突）"""
    prefix = "990102"
    year = random.choice([2009, 2010, 2011, 2012])
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    seq_code = f"{seq:03d}"
    body = f"{prefix}{year}{month:02d}{day:02d}{seq_code}"
    # 计算校验码
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_chars = "10X98765432"
    total = sum(int(body[i]) * weights[i] for i in range(17))
    return body + check_chars[total % 11]


def _random_phone() -> str:
    return f"1{random.choice(['38','39','50','58','59','82','85','86','87','88'])}{random.randint(10000000, 99999999)}"


def _get_db_session():
    db_url = os.getenv("DB_TYPE", "mysql")
    if db_url == "mysql":
        host = os.getenv("DB_HOST", "127.0.0.1")
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "a_annanyun_com")
        user = os.getenv("DB_USER", "a_annanyun_com")
        pwd = os.getenv("DB_PASSWORD", "")
        url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"
    else:
        url = "sqlite:///./dev.db"
    engine = create_engine(url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def seed():
    db = _get_db_session()
    try:
        # 检查是否已有演示数据
        existing = db.query(School).filter(School.code.like("DEMO-%")).count()
        if existing > 0:
            print(f"[跳过] 已存在 {existing} 所演示学校，请先清理")
            return

        # ─── 1. 创建学校 ──────────────────────────────────
        schools = []
        for tpl in SCHOOL_TEMPLATES:
            s = School(name=tpl["name"], code=tpl["code"], address=tpl["address"], phone=tpl["phone"], status=True)
            db.add(s)
            db.flush()
            schools.append(s)
            print(f"  创建学校: {s.name} (id={s.id})")

        # ─── 2. 创建年级 + 班级 + 用户 ────────────────────
        all_account_info = []  # 收集账号信息用于文档
        student_counter = 0
        teacher_counter = 0

        for school in schools:
            sc = school.code.split("-")[1]  # QY, MD, XH

            # 学校管理员
            admin_username = f"DEMO_{sc}_admin"
            admin = User(
                school_id=school.id, username=admin_username,
                password_hash=hash_password("admin123"),
                real_name=_random_name(), role="school_admin",
                phone=_random_phone(), status=True, must_change_password=True,
            )
            db.add(admin)
            db.flush()
            all_account_info.append({"role": "school_admin", "school": school.name, "name": admin.real_name, "username": admin_username, "password": "admin123"})
            print(f"  创建学校管理员: {admin.real_name} ({admin_username})")

            # 心理老师
            counselor_username = f"DEMO_{sc}_c01"
            counselor = User(
                school_id=school.id, username=counselor_username,
                password_hash=hash_password(counselor_username[-6:]),
                real_name=_random_name(), role="counselor",
                teacher_type="counselor", phone=_random_phone(),
                status=True, must_change_password=True,
            )
            db.add(counselor)
            db.flush()
            all_account_info.append({"role": "counselor", "school": school.name, "name": counselor.real_name, "username": counselor_username, "password": counselor_username[-6:]})
            print(f"  创建心理老师: {counselor.real_name} ({counselor_username})")

            school_grades = []
            school_classes = []

            for gi, grade_name in enumerate(GRADE_NAMES):
                g = Grade(school_id=school.id, name=grade_name, sort_order=gi + 1, status=True)
                db.add(g)
                db.flush()
                school_grades.append(g)

                for ci in range(1, 3):  # 每年级2个班
                    class_name = f"{grade_name}({ci})班{DEMO_SUFFIX}"

                    # 先创建班级（head_teacher_id 后补）
                    c = Class(
                        school_id=school.id, grade_id=g.id, name=class_name,
                        counselor_id=counselor.id, status=True,
                    )
                    db.add(c)
                    db.flush()
                    school_classes.append(c)

                    # 班主任
                    teacher_counter += 1
                    t_username = f"DEMO_{sc}_t{teacher_counter:02d}"
                    teacher = User(
                        school_id=school.id, username=t_username,
                        password_hash=hash_password(t_username[-6:]),
                        real_name=_random_name(), role="teacher",
                        teacher_type="head_teacher", phone=_random_phone(),
                        status=True, must_change_password=True,
                    )
                    db.add(teacher)
                    db.flush()
                    all_account_info.append({"role": "teacher", "school": school.name, "name": teacher.real_name, "username": t_username, "password": t_username[-6:]})

                    # 补充班主任关系
                    c.head_teacher_id = teacher.id
                    teacher.grade_id = g.id
                    teacher.class_id = c.id
                    db.add(TeacherClass(teacher_id=teacher.id, class_id=c.id))
                    db.flush()

                    # 学生
                    num_students = random.randint(25, 30)
                    for _ in range(num_students):
                        student_counter += 1
                        id_number = _random_id_number(student_counter)
                        s_default_pw = id_number[-6:]
                        gender = random.choice(["男", "女"])
                        birth_year = random.choice([2009, 2010, 2011, 2012])
                        birth_month = random.randint(1, 12)
                        birth_day = random.randint(1, 28)

                        student = User(
                            school_id=school.id, username=id_number,
                            password_hash=hash_password(s_default_pw),
                            real_name=_random_name(), role="student",
                            gender=gender, phone="",
                            student_no=f"STU{school.id:03d}{student_counter:04d}",
                            birth_date=datetime(birth_year, birth_month, birth_day).date(),
                            grade_id=g.id, class_id=c.id,
                            status=True, must_change_password=True,
                        )
                        db.add(student)

            db.flush()
            print(f"  学校 {school.name}: {len(school_grades)} 年级, {len(school_classes)} 班级, ~{student_counter} 学生")

        db.commit()
        print("\n[完成] 学校/年级/班级/用户数据已创建")

        # ─── 3. 创建测评任务 + 答卷 ──────────────────────
        # 获取内置问卷
        questionnaires = {
            q.code: q for q in db.query(Questionnaire).filter(Questionnaire.is_builtin == True, Questionnaire.status == "active").all()
        }

        now = datetime.now(tz)

        for school in schools:
            classes = db.query(Class).filter(Class.school_id == school.id).all()
            all_students = db.query(User).filter(User.school_id == school.id, User.role == "student").all()

            # 任务1: 综合关注筛查 - 面向全校
            q1_code = "builtin-comprehensive-risk-v1"
            if q1_code in questionnaires:
                task1 = Task(
                    school_id=school.id, questionnaire_id=questionnaires[q1_code].id,
                    name=f"2026年春季综合关注筛查{DEMO_SUFFIX}",
                    target_type="school", target_ids=[c.id for c in classes],
                    status="in_progress",
                    published_at=now - timedelta(days=5),
                    start_time=now - timedelta(days=5),
                    end_time=now + timedelta(days=10),
                    description="演示数据任务",
                )
                db.add(task1)
                db.flush()
                _generate_answers_for_task(db, task1, all_students, questionnaires[q1_code])
                print(f"  任务: {task1.name} ({len(all_students)} 学生)")

            # 任务2: 情绪状态关注评估 - 面向八年级
            q2_code = "builtin-emotion-phq-like-v1"
            if q2_code in questionnaires:
                grade_8 = db.query(Grade).filter(Grade.school_id == school.id, Grade.name == "八年级").first()
                if grade_8:
                    g8_classes = db.query(Class).filter(Class.school_id == school.id, Class.grade_id == grade_8.id).all()
                    g8_students = db.query(User).filter(User.school_id == school.id, User.role == "student", User.grade_id == grade_8.id).all()
                    task2 = Task(
                        school_id=school.id, questionnaire_id=questionnaires[q2_code].id,
                        name=f"情绪状态关注评估{DEMO_SUFFIX}",
                        target_type="grade", target_ids=[c.id for c in g8_classes],
                        status="in_progress",
                        published_at=now - timedelta(days=3),
                        start_time=now - timedelta(days=3),
                        end_time=now + timedelta(days=7),
                        description="演示数据任务",
                    )
                    db.add(task2)
                    db.flush()
                    _generate_answers_for_task(db, task2, g8_students, questionnaires[q2_code])
                    print(f"  任务: {task2.name} ({len(g8_students)} 学生)")

        db.commit()
        print("\n[完成] 任务和答卷数据已创建")

        # ─── 4. 为风险预警创建干预记录 ─────────────────────
        risk_alerts = db.query(RiskAlert).filter(RiskAlert.school_id == school.id).all()
        # 实际上面有循环，这里用所有学校的 alerts
        all_alerts = db.query(RiskAlert).filter(RiskAlert.risk_level.in_(["medium", "high", "urgent"])).all()
        intervention_methods = ["student_talk", "family_school", "counselor_guidance", "observation", "home_visit"]
        intervention_contents = [
            "与学生进行了一对一沟通，了解了近期学习和生活状况。",
            "联系家长了解学生在家的表现和情绪变化。",
            "安排心理辅导老师进行专业评估和初步辅导。",
            "在课堂和课间观察学生的社交和情绪状态。",
            "进行家访，了解家庭环境和亲子关系。",
        ]

        for i, alert in enumerate(all_alerts[:20]):
            teacher = db.query(User).filter(User.school_id == alert.school_id, User.role.in_(["teacher", "counselor"]), User.status == True).first()
            if not teacher:
                continue
            method_idx = i % len(intervention_methods)
            iv = Intervention(
                school_id=alert.school_id, student_id=alert.student_id,
                risk_alert_id=alert.id, teacher_id=teacher.id,
                intervention_time=now - timedelta(days=random.randint(1, 4)),
                method=intervention_methods[method_idx],
                content=intervention_contents[method_idx],
                result="已初步了解情况，持续关注中。",
                follow_up_suggestion="建议继续跟进观察，必要时进行二次沟通。",
                need_follow_up=random.choice([True, False]),
                status=random.choice(["completed", "follow_up"]),
                next_follow_up_time=now + timedelta(days=random.randint(3, 14)) if random.random() > 0.5 else None,
            )
            db.add(iv)
            # 更新 RiskAlert 状态
            alert.status = "assigned"
            alert.assigned_teacher_id = teacher.id
            alert.due_at = now + timedelta(days=7)

        db.commit()
        print(f"\n[完成] 创建 {min(len(all_alerts), 20)} 条干预记录")

        # ─── 5. 输出账号信息 ──────────────────────────────
        print("\n" + "=" * 70)
        print("演示账号一览")
        print("=" * 70)
        for info in all_account_info:
            print(f"  [{info['role']:14s}] {info['school']:16s} | {info['name']:10s} | {info['username']:20s} | {info['password']}")

        # 平台管理员
        padm = db.query(User).filter(User.role == "platform_admin").first()
        if padm:
            print(f"  [{'platform_admin':14s}] {'(全域)':16s} | {padm.real_name:10s} | {padm.username:20s} | (已设密码)")

        # 保存账号信息到 JSON 文件
        accounts_file = backend_dir / "scripts" / "demo_accounts.json"
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(all_account_info, f, ensure_ascii=False, indent=2)
        print(f"\n账号信息已保存到: {accounts_file}")

        print("\n[全部完成] 演示数据初始化成功!")

    except Exception as e:
        db.rollback()
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def _generate_answers_for_task(db, task: Task, students: list, questionnaire: Questionnaire):
    """为任务生成答卷，使用真实评分流程"""
    questions = db.query(Question).filter(Question.questionnaire_id == questionnaire.id).order_by(Question.sort_order).all()
    if not questions:
        return

    # 预加载选项
    options_map = {}
    for q in questions:
        opts = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
        options_map[q.id] = opts

    # 随机决定每个学生的风险分布
    random.shuffle(students)
    n = len(students)
    # ~80% 低风险，15% 中等，5% 高风险
    for i, student in enumerate(students):
        if i < n * 0.80:
            profile = "normal"
        elif i < n * 0.95:
            profile = "elevated"
        else:
            profile = "high"

        # 随机跳过 20%（未完成）
        if random.random() < 0.2:
            continue

        now = datetime.now(tz)
        start = now - timedelta(minutes=random.randint(10, 30))
        end = start + timedelta(minutes=random.randint(5, 15))

        sheet = AnswerSheet(
            school_id=student.school_id, class_id=student.class_id,
            task_id=task.id, student_id=student.id,
            questionnaire_id=questionnaire.id,
            question_order=[q.id for q in questions],
            option_orders={},
            status="submitted", started_at=start, submitted_at=end,
            total_duration_seconds=int((end - start).total_seconds()),
        )
        db.add(sheet)
        db.flush()

        # 生成答案
        _fill_answers(db, sheet, questions, options_map, profile)

        # 使用真实评分流程
        try:
            scoring_service.calculate_scores(db, sheet.id)
            scoring_service.calculate_quality(db, sheet.id)
            scoring_service.check_risk_alerts(db, sheet.id)
        except Exception as e:
            print(f"    [评分异常] sheet={sheet.id}, student={student.real_name}: {e}")

    db.flush()


def _fill_answers(db, sheet: AnswerSheet, questions: list, options_map: dict, profile: str):
    """根据 profile 生成答案"""
    for order, question in enumerate(questions, start=1):
        options = options_map.get(question.id, [])
        if not options:
            continue

        if question.is_attention_check:
            # 注意力检测题：选正确答案
            correct = question.attention_correct_answer
            selected = next((o for o in options if o.content == correct), options[-1])
            duration = random.randint(3, 8)
        elif question.type in ("single_choice", "scale", "true_false"):
            selected = _pick_option(options, profile)
            duration = random.randint(4, 12) if profile == "normal" else random.randint(3, 8)
        elif question.type == "multi_choice":
            # 多选题：选 1-3 个
            selected_ids = _pick_multi_options(options, profile)
            db.add(AnswerRecord(
                answer_sheet_id=sheet.id, question_id=question.id,
                question_type=question.type,
                answer_content={"selected_option_ids": selected_ids},
                displayed_order=order,
                duration_seconds=random.randint(4, 12),
            ))
            continue
        else:
            # 填空/简答 - 跳过
            continue

        db.add(AnswerRecord(
            answer_sheet_id=sheet.id, question_id=question.id,
            question_type=question.type,
            answer_content={"selected_option_id": selected.id},
            displayed_order=order,
            duration_seconds=duration,
        ))


def _pick_option(options: list, profile: str) -> "Option":
    """根据 profile 选择选项"""
    n = len(options)
    if n == 0:
        return None

    if profile == "normal":
        # 倾向低分选项（前半部分）
        weights = [max(1, n - i) for i in range(n)]
    elif profile == "elevated":
        # 倾向中高分选项（后半部分）
        weights = [max(1, i + 1) for i in range(n)]
    else:  # high
        # 强烈倾向高分选项
        weights = [1] * (n - 1) + [5]
        if n > 2:
            weights[-2] = 3

    return random.choices(options, weights=weights, k=1)[0]


def _pick_multi_options(options: list, profile: str) -> list[int]:
    """多选题选几个选项"""
    n = len(options)
    if n == 0:
        return []

    if profile == "normal":
        count = random.randint(1, min(2, n))
    elif profile == "elevated":
        count = random.randint(1, min(3, n))
    else:
        count = random.randint(2, min(4, n))

    return [o.id for o in random.sample(options, min(count, n))]


if __name__ == "__main__":
    seed()
