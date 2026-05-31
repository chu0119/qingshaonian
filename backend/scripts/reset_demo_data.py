#!/usr/bin/env python3
"""
演示数据重置脚本
清除所有现有数据并创建全面、真实的演示数据
"""
import sys
import os
import random
from datetime import datetime, timedelta, timezone

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.user import School, Grade, Class, User, TeacherClass
from app.models.questionnaire import Questionnaire
from app.models.task import Task, AnswerSheet, AnswerRecord
from app.models.risk import RiskAlert, Intervention, ScoringResult, QualityAssessment
from app.models.audit import LoginLog, OperationLog
from app.models.external import SMSLog, AIAnalysisLog
from app.utils.password import hash_password

tz = timezone(timedelta(hours=8))

# 学校配置（虚构地名）
SCHOOLS = [
    {
        "name": "阳光中学",
        "code": "YG001",
        "address": "星城市光明区学府路120号",
        "phone": "0571-88001001",
        "grades": [
            {"name": "初一", "classes": ["1班", "2班", "3班", "4班"]},
            {"name": "初二", "classes": ["1班", "2班", "3班"]},
            {"name": "初三", "classes": ["1班", "2班", "3班"]},
        ],
    },
    {
        "name": "明德中学",
        "code": "MD002",
        "address": "星城市文汇区育才街88号",
        "phone": "0571-88001002",
        "grades": [
            {"name": "初一", "classes": ["1班", "2班", "3班"]},
            {"name": "初二", "classes": ["1班", "2班", "3班"]},
            {"name": "初三", "classes": ["1班", "2班"]},
        ],
    },
    {
        "name": "启航中学",
        "code": "QH003",
        "address": "星城市新远区青年路66号",
        "phone": "0571-88001003",
        "grades": [
            {"name": "初一", "classes": ["1班", "2班", "3班", "4班"]},
            {"name": "初二", "classes": ["1班", "2班", "3班", "4班"]},
            {"name": "初三", "classes": ["1班", "2班", "3班"]},
        ],
    },
    {
        "name": "星辰第一中学",
        "code": "XC004",
        "address": "星城市高新区星辰大道100号",
        "phone": "0571-88001004",
        "grades": [
            {"name": "初一", "classes": ["1班", "2班", "3班", "4班", "5班"]},
            {"name": "初二", "classes": ["1班", "2班", "3班", "4班"]},
            {"name": "初三", "classes": ["1班", "2班", "3班", "4班"]},
        ],
    },
    {
        "name": "博文中学",
        "code": "BW005",
        "address": "星城市安宁区博学路99号",
        "phone": "0571-88001005",
        "grades": [
            {"name": "初一", "classes": ["1班", "2班", "3班"]},
            {"name": "初二", "classes": ["1班", "2班", "3班"]},
            {"name": "初三", "classes": ["1班", "2班"]},
        ],
    },
]

# 姓名库
SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
MALE_NAMES = ["明", "华", "磊", "杰", "浩", "涛", "强", "军", "勇", "鑫", "宇", "飞", "鹏", "斌", "超", "辉", "亮", "刚", "波", "宁"]
FEMALE_NAMES = ["芳", "婷", "琳", "雪", "思", "晨", "静", "敏", "丽", "艳", "娟", "霞", "秀英", "桂英", "玉兰", "淑芬", "美玲", "小红", "晓燕", "翠花"]

# 教师姓名库
TEACHER_NAMES = [
    ("张", "伟"), ("李", "娜"), ("王", "强"), ("刘", "洋"), ("陈", "静"),
    ("杨", "军"), ("赵", "敏"), ("黄", "磊"), ("周", "涛"), ("吴", "芳"),
    ("徐", "杰"), ("孙", "丽"), ("胡", "勇"), ("朱", "华"), ("高", "明"),
    ("林", "娟"), ("何", "波"), ("郭", "艳"), ("马", "飞"), ("罗", "鑫"),
]

# 身份证号生成器（模拟，使用真实格式）
def generate_id_card(birth_year: int, birth_month: int, birth_day: int, gender: str, seq: int) -> str:
    """生成模拟的18位身份证号"""
    area_code = "610102"  # 西安市碑林区
    birth = f"{birth_year:04d}{birth_month:02d}{birth_day:02d}"
    gender_code = seq * 2 + (0 if gender == "男" else 1)
    seq_str = f"{gender_code:03d}"
    id_without_check = f"{area_code}{birth}{seq_str}"

    # 计算校验码
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_chars = "10X98765432"
    total = sum(int(id_without_check[i]) * weights[i] for i in range(17))
    check_char = check_chars[total % 11]

    return id_without_check + check_char


def clear_all_data(db):
    """清除所有数据（保留平台管理员）"""
    print("清除现有数据...")

    # 禁用外键检查，避免删除顺序问题
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

    tables = [
        "answer_records", "scoring_results", "quality_assessments",
        "interventions", "risk_alerts", "answer_sheets", "tasks",
        "teacher_classes", "sms_logs", "ai_analysis_logs",
        "login_logs", "operation_logs",
        "options", "questions", "contradiction_groups", "questionnaires",
    ]
    for table in tables:
        db.execute(text(f"DELETE FROM {table}"))

    # 删除非平台管理员用户
    db.execute(text("DELETE FROM users WHERE role != 'platform_admin'"))

    # 删除学校相关数据
    db.execute(text("DELETE FROM classes"))
    db.execute(text("DELETE FROM grades"))
    db.execute(text("DELETE FROM schools"))

    db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    db.commit()
    print("数据清除完成")


def create_schools(db):
    """创建学校"""
    print("创建学校...")
    schools = []
    for school_data in SCHOOLS:
        school = School(
            name=school_data["name"],
            code=school_data["code"],
            address=school_data["address"],
            phone=school_data["phone"],
            status=True,
        )
        db.add(school)
        db.flush()
        schools.append((school, school_data))
    db.commit()
    return schools


def create_grades_and_classes(db, schools):
    """创建年级和班级"""
    print("创建年级和班级...")
    class_map = {}  # school_id -> {grade_name -> [class_objects]}

    for school, school_data in schools:
        class_map[school.id] = {}
        for grade_order, grade_data in enumerate(school_data["grades"]):
            grade = Grade(
                school_id=school.id,
                name=grade_data["name"],
                sort_order=grade_order,
                status=True,
            )
            db.add(grade)
            db.flush()

            classes = []
            for class_name in grade_data["classes"]:
                cls = Class(
                    school_id=school.id,
                    grade_id=grade.id,
                    name=class_name,
                    status=True,
                )
                db.add(cls)
                db.flush()
                classes.append(cls)

            class_map[school.id][grade_data["name"]] = (grade, classes)

    db.commit()
    return class_map


def create_teachers(db, schools, class_map):
    """创建教师"""
    print("创建教师...")
    teacher_map = {}  # school_id -> [teacher_objects]
    teacher_idx = 0

    for school, _ in schools:
        teachers = []
        school_classes = []
        for grade_name, (_, classes) in class_map[school.id].items():
            school_classes.extend(classes)

        # 为每个学校创建教师
        for i, (surname, given_name) in enumerate(TEACHER_NAMES[:8]):
            if teacher_idx >= len(TEACHER_NAMES):
                teacher_idx = 0

            gender = "男" if i % 2 == 0 else "女"
            birth_year = random.randint(1975, 1995)
            id_card = generate_id_card(birth_year, random.randint(1, 12), random.randint(1, 28), gender, teacher_idx)

            role = "counselor" if i == 0 else "teacher"
            teacher_type = "counselor" if i == 0 else ("head_teacher" if i < 4 else "normal")

            teacher = User(
                school_id=school.id,
                username=id_card,
                password_hash=hash_password(id_card[-6:]),
                real_name=surname + given_name,
                role=role,
                teacher_type=teacher_type,
                gender=gender,
                phone=f"138{random.randint(10000000, 99999999)}",
                status=True,
                must_change_password=True,
            )
            db.add(teacher)
            db.flush()
            teachers.append(teacher)
            teacher_idx += 1

        # 分配班主任
        for i, cls in enumerate(school_classes[:len(teachers)-1]):
            if i + 1 < len(teachers):
                cls.head_teacher_id = teachers[i + 1].id
                db.add(TeacherClass(teacher_id=teachers[i + 1].id, class_id=cls.id))

        # 分配心理老师
        if school_classes and teachers:
            for cls in school_classes:
                cls.counselor_id = teachers[0].id

        teacher_map[school.id] = teachers

    db.commit()
    return teacher_map


def create_students(db, schools, class_map):
    """创建学生"""
    print("创建学生...")
    student_map = {}  # school_id -> [student_objects]
    student_idx = 0
    student_seq_per_school = {}  # school_id -> counter

    for school, _ in schools:
        students = []
        student_seq_per_school[school.id] = 1

        for grade_name, (_, classes) in class_map[school.id].items():
            for cls in classes:
                # 每个班级创建20-30名学生
                num_students = random.randint(20, 30)
                for i in range(num_students):
                    gender = random.choice(["男", "女"])
                    surname = random.choice(SURNAMES)
                    given_name = random.choice(MALE_NAMES if gender == "男" else FEMALE_NAMES)

                    # 根据年级计算出生年份
                    if grade_name == "初一":
                        birth_year = random.randint(2011, 2012)
                    elif grade_name == "初二":
                        birth_year = random.randint(2010, 2011)
                    else:  # 初三
                        birth_year = random.randint(2009, 2010)

                    id_card = generate_id_card(birth_year, random.randint(1, 12), random.randint(1, 28), gender, student_idx)
                    student_no = f"STU{school.id:03d}{student_seq_per_school[school.id]:04d}"
                    student_seq_per_school[school.id] += 1

                    student = User(
                        school_id=school.id,
                        username=id_card,
                        password_hash=hash_password(id_card[-6:]),
                        real_name=surname + given_name,
                        role="student",
                        gender=gender,
                        student_no=student_no,
                        birth_date=datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date(),
                        grade_id=cls.grade_id,
                        class_id=cls.id,
                        status=True,
                        must_change_password=True,
                    )
                    db.add(student)
                    db.flush()
                    students.append(student)
                    student_idx += 1

        student_map[school.id] = students

    db.commit()
    return student_map


def create_questionnaires(db):
    """确保内置问卷存在"""
    print("检查内置问卷...")
    questionnaires = {q.code: q for q in db.query(Questionnaire).filter(Questionnaire.is_builtin == True).all()}
    if not questionnaires:
        from app.questionnaire_bank import ensure_builtin_questionnaires
        ensure_builtin_questionnaires(db)
        questionnaires = {q.code: q for q in db.query(Questionnaire).filter(Questionnaire.is_builtin == True).all()}
    return questionnaires


def create_tasks_and_answers(db, schools, class_map, teacher_map, student_map, questionnaires):
    """创建任务和答卷"""
    print("创建任务和答卷...")

    if not questionnaires:
        print("警告：没有可用的问卷")
        return

    # 问卷代码列表
    q_codes = list(questionnaires.keys())

    for school, _ in schools:
        teachers = teacher_map.get(school.id, [])
        students = student_map.get(school.id, [])

        if not teachers or not students:
            continue

        # 为每个学校创建2-3个任务
        num_tasks = random.randint(2, 3)
        for task_idx in range(num_tasks):
            q_code = q_codes[task_idx % len(q_codes)]
            questionnaire = questionnaires[q_code]

            # 选择目标班级
            school_classes = []
            for grade_name, (_, classes) in class_map[school.id].items():
                school_classes.extend(classes)

            target_classes = random.sample(school_classes, min(3, len(school_classes)))
            target_class_ids = [c.id for c in target_classes]

            # 创建任务
            days_ago = random.randint(3, 10)
            task = Task(
                school_id=school.id,
                questionnaire_id=questionnaire.id,
                name=f"{questionnaire.title} - 第{task_idx + 1}期",
                target_type="class",
                target_ids=target_class_ids,
                status="in_progress",
                published_at=datetime.now(tz) - timedelta(days=days_ago),
                start_time=datetime.now(tz) - timedelta(days=days_ago),
                end_time=datetime.now(tz) + timedelta(days=5),
                created_by=teachers[0].id,
                description=f"2024-2025学年第一学期{questionnaire.title}",
            )
            db.add(task)
            db.flush()

            # 为目标班级的学生创建答卷
            target_students = [s for s in students if s.class_id in target_class_ids]

            # 80%的学生已完成答卷
            completed_count = int(len(target_students) * 0.8)
            completed_students = random.sample(target_students, completed_count)

            for idx, student in enumerate(completed_students):
                # 随机决定风险模式（15%的学生有风险）
                risk_mode = random.random() < 0.15

                sheet = AnswerSheet(
                    school_id=school.id,
                    class_id=student.class_id,
                    task_id=task.id,
                    student_id=student.id,
                    questionnaire_id=questionnaire.id,
                    status="submitted",
                    started_at=datetime.now(tz) - timedelta(days=days_ago, hours=random.randint(0, 12)),
                    submitted_at=datetime.now(tz) - timedelta(days=days_ago, hours=random.randint(0, 6)),
                )
                db.add(sheet)
                db.flush()

                # 填充答案
                _fill_answers(db, sheet, risk_mode)

                # 计算分数和质量
                try:
                    from app.services import scoring_service
                    scoring_service.calculate_scores(db, sheet.id)
                    scoring_service.calculate_quality(db, sheet.id)
                    scoring_service.check_risk_alerts(db, sheet.id)
                except Exception as e:
                    print(f"评分警告: {e}")

            db.commit()

    print("任务和答卷创建完成")


def _fill_answers(db, sheet, risk_mode=False):
    """填充答卷答案"""
    from app.models.questionnaire import Question, Option

    questions = db.query(Question).filter(
        Question.questionnaire_id == sheet.questionnaire_id
    ).order_by(Question.sort_order).all()

    sheet.question_order = [q.id for q in questions]

    for order, question in enumerate(questions, start=1):
        options = db.query(Option).filter(
            Option.question_id == question.id
        ).order_by(Option.sort_order).all()

        if not options:
            continue

        # 选择答案
        if question.is_attention_check:
            selected = next((o for o in options if o.content == question.attention_correct_answer), options[-1])
        elif risk_mode and (question.risk_tag in {"self_safety", "bullying"} or not question.is_reverse):
            # 风险模式：选择高风险选项
            selected = options[-1]
        else:
            # 正常模式：选择中间或低风险选项
            selected = options[1] if len(options) > 1 else options[0]

        answer = AnswerRecord(
            answer_sheet_id=sheet.id,
            question_id=question.id,
            question_type=question.type,
            answer_content={"selected_option_id": selected.id},
            displayed_order=order,
            duration_seconds=random.randint(3, 15),
        )
        db.add(answer)


def create_interventions(db, schools, teacher_map, student_map):
    """创建干预记录"""
    print("创建干预记录...")

    methods = ["student_talk", "teacher_communication", "counselor_guidance", "family_school", "observation"]
    statuses = ["completed", "in_progress", "follow_up", "pending"]

    for school, _ in schools:
        teachers = teacher_map.get(school.id, [])
        students = student_map.get(school.id, [])

        if not teachers or not students:
            continue

        # 为每个学校创建5-10条干预记录
        num_interventions = random.randint(5, 10)
        for _ in range(num_interventions):
            teacher = random.choice(teachers)
            student = random.choice(students)
            method = random.choice(methods)
            status = random.choice(statuses)

            content_templates = [
                f"与{student.real_name}同学进行了一对一沟通，了解近期学习和生活情况。",
                f"与{student.real_name}同学的家长进行了电话沟通，反馈学生在校表现。",
                f"对{student.real_name}同学进行了心理辅导，帮助其缓解学习压力。",
                f"安排{student.real_name}同学参加团体辅导活动，增强社交能力。",
                f"持续观察{student.real_name}同学的行为变化，记录观察结果。",
            ]

            result_templates = [
                "学生表示愿意配合改进，态度积极。",
                "家长表示会加强家庭关注和配合。",
                "学生情绪有所好转，建议继续跟进。",
                "初步效果良好，需要持续关注。",
                "已建立定期沟通机制。",
            ]

            intervention = Intervention(
                school_id=school.id,
                student_id=student.id,
                teacher_id=teacher.id,
                method=method,
                content=random.choice(content_templates),
                result=random.choice(result_templates),
                follow_up_suggestion="建议一周后继续跟进了解情况。",
                need_follow_up=status == "follow_up",
                status=status,
                intervention_time=datetime.now(tz) - timedelta(days=random.randint(0, 14)),
                next_follow_up_time=datetime.now(tz) + timedelta(days=7) if status == "follow_up" else None,
            )
            db.add(intervention)

    db.commit()
    print("干预记录创建完成")


def create_school_admins(db, schools):
    """创建学校管理员账号"""
    print("创建学校管理员...")

    for school, _ in schools:
        admin = User(
            school_id=school.id,
            username=f"admin_{school.code.lower()}",
            password_hash=hash_password("Admin@123456"),
            real_name=f"{school.name}管理员",
            role="school_admin",
            phone=f"139{random.randint(10000000, 99999999)}",
            status=True,
            must_change_password=True,
        )
        db.add(admin)

    db.commit()
    print("学校管理员创建完成")


def main():
    print("=" * 50)
    print("演示数据重置脚本")
    print("=" * 50)

    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. 清除现有数据
        clear_all_data(db)

        # 2. 创建学校
        schools = create_schools(db)

        # 3. 创建年级和班级
        class_map = create_grades_and_classes(db, schools)

        # 4. 创建教师
        teacher_map = create_teachers(db, schools, class_map)

        # 5. 创建学生
        student_map = create_students(db, schools, class_map)

        # 6. 创建学校管理员
        create_school_admins(db, schools)

        # 7. 确保内置问卷存在
        questionnaires = create_questionnaires(db)

        # 8. 创建任务和答卷
        create_tasks_and_answers(db, schools, class_map, teacher_map, student_map, questionnaires)

        # 9. 创建干预记录
        create_interventions(db, schools, teacher_map, student_map)

        print("=" * 50)
        print("演示数据创建完成！")
        print("=" * 50)
        print("\n账号信息：")
        print("平台管理员: padm / padm123")
        for school, _ in schools:
            print(f"{school.name}: admin_{school.code.lower()} / Admin@123456")
        print("\n学生/教师默认密码: 身份证号后6位")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
