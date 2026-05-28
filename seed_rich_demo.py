"""增强演示数据注入 — 更丰富、更有演示性"""
import random, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/www/wwwroot/qingshaonian/backend')

from app.database import SessionLocal
from app.models.questionnaire import Questionnaire, Question, Option
from app.models.risk import Intervention
from app.models.task import AnswerRecord, AnswerSheet, Task
from app.models.user import Class, TeacherClass, User
from app.utils.password import hash_password
from app.services import scoring_service

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)

db = SessionLocal()

# 找到默认学校
from app.models.user import School
school = db.query(School).first()
if not school:
    print("No school found")
    sys.exit(1)
print(f"Seeding: {school.name} (id={school.id})")

# 清除旧的演示数据（按外键依赖顺序）
from app.models.risk import ScoringResult, QualityAssessment, RiskAlert
from app.models.audit import LoginLog, OperationLog

# 按依赖顺序删除
db.query(QualityAssessment).delete()
db.query(ScoringResult).delete()
db.query(RiskAlert).delete()
db.query(Intervention).delete()
db.query(AnswerRecord).delete()
db.query(AnswerSheet).delete()
db.query(Task).filter(Task.school_id == school.id).delete()

# 先清空班级的外键引用再删用户
for c in db.query(Class).filter(Class.school_id == school.id).all():
    c.head_teacher_id = None
    c.counselor_id = None
db.flush()
db.query(TeacherClass).delete()
db.query(User).filter(User.school_id == school.id, User.role.in_(['teacher', 'student'])).delete()
db.flush()

# === 1. 教师（8人） ===
teacher_info = [
    ("T0101", "张老师", "head_teacher"),
    ("T0102", "李老师", "head_teacher"),
    ("T0103", "王老师", "head_teacher"),
    ("T0104", "陈老师", "head_teacher"),
    ("T0105", "刘老师", "counselor"),
    ("T0106", "杨老师", "counselor"),
    ("T0107", "赵老师", "grade_director"),
    ("T0108", "周老师", "moral_edu"),
]
classes = db.query(Class).filter(Class.school_id == school.id, Class.status == True).order_by(Class.id).all()
teachers = []
for idx, (uname, rname, ttype) in enumerate(teacher_info):
    t = User(
        school_id=school.id, username=uname,
        password_hash=hash_password("Demo@123"),
        real_name=rname, role="teacher", teacher_type=ttype, status=True,
    )
    db.add(t)
    db.flush()
    teachers.append(t)
    # 前4个班主任各负责一个班
    if idx < len(classes):
        db.add(TeacherClass(teacher_id=t.id, class_id=classes[idx].id))
        classes[idx].head_teacher_id = t.id
print(f"  Teachers: {len(teachers)}")

# === 2. 学生（60人，每班约10人） ===
surnames_m = "王李张刘陈杨赵黄周吴徐孙马朱胡郭何高林郑罗梁宋谢唐韩冯"
surnames = [surnames_m[i] for i in range(len(surnames_m))]
names_m = "明华磊杰浩涛晨宇轩然阳阳雪琳婷芳思雨悦涵博文悦"
names = [names_m[i] for i in range(len(names_m))]
male_names = ["明","华","磊","杰","浩","涛","晨","宇","轩","然","阳","博","文","泽","瑞","凯","旭","彬"]
female_names = ["雪","琳","婷","芳","思","雨","悦","涵","怡","萱","欣","雅","诗","琪","婉","慧"]

all_students = []
all_classes = classes[:6]  # 最多6个班
for klass in all_classes:
    for i in range(10):
        if i < 5:
            name = random.choice(surnames) + random.choice(male_names)
            gender = "男"
        else:
            name = random.choice(surnames) + random.choice(female_names)
            gender = "女"
        stuno = f"S2024{school.id:02d}{len(all_students)+1:03d}"
        s = User(
            school_id=school.id, username=stuno,
            password_hash=hash_password("Demo@123"),
            real_name=name, role="student", gender=gender,
            status=True, grade_id=klass.grade_id, class_id=klass.id,
            student_no=stuno,
        )
        db.add(s)
        db.flush()
        all_students.append(s)
print(f"  Students: {len(all_students)}")

# === 3. 获取内置问卷 ===
qmap = {q.code: q for q in db.query(Questionnaire).filter(
    Questionnaire.is_builtin == True, Questionnaire.status == "active").all()}
print(f"  Builtin questionnaires: {len(qmap)}")

# === 4. 创建任务 (name, code, classes, days_ago) ===
task_specs = [
    ("全校综合风险筛查", "builtin-comprehensive-risk-v1", classes[:6], 14),
    ("初一年级情绪筛查", "builtin-emotion-phq-like-v1", classes[:2], 10),
    ("初二年级情绪筛查", "builtin-emotion-phq-like-v1", classes[2:4], 10),
    ("初一年级焦虑筛查", "builtin-anxiety-gad-like-v1", classes[:2], 7),
    ("校园欺凌排查", "builtin-bullying-risk-v1", classes[:4], 5),
    ("网络使用评估", "builtin-internet-risk-v1", classes[2:], 3),
    ("学业压力测评", "builtin-academic-pressure-v1", classes[2:4], 1),
    ("人际关系调查", "builtin-interpersonal-adaptation-v1", classes[:2], 0),
]

tasks = []
for tname, qcode, tclasses, days_ago in task_specs:
    q = qmap.get(qcode)
    if not q:
        continue
    teacher = random.choice(teachers[:4])
    t = Task(
        school_id=school.id, questionnaire_id=q.id, name=tname,
        target_type="class", target_ids=[c.id for c in tclasses],
        status="in_progress",
        published_at=now - timedelta(days=days_ago),
        start_time=now - timedelta(days=days_ago),
        end_time=now + timedelta(days=14 - days_ago),
        created_by=teacher.id,
        description=f"演示任务 - {tname}",
    )
    db.add(t)
    db.flush()
    tasks.append((t, tclasses))
print(f"  Tasks: {len(tasks)}")

# === 5. 生成答卷 ===
def pick_answer(student_index, total_students, question, options):
    """根据学生编号决定答题模式"""
    mode = student_index % 10  # 0-9

    if question.is_attention_check:
        return next((o for o in options if o.content == question.attention_correct_answer), options[0])

    # 模式0-1: 高风险 (选高分)
    # 模式2-3: 中风险 (中等分)
    # 模式4-6: 低风险 (低分)
    # 模式7: 连续同选项
    # 模式8: 快速乱答
    # 模式9: 注意力失败

    if mode in (0, 1):
        if question.risk_tag in ("self_safety", "bullying") or question.is_reverse:
            return options[-1]  # 高分选项
        return options[random.randint(2, len(options)-1)]
    elif mode in (2, 3):
        return options[random.randint(1, len(options)-2)]
    elif mode in (7, 8):
        return options[0]  # 始终选第一个
    else:
        # 低风险
        return options[0] if not question.is_reverse else options[-1]

scores = {"high_count": 0, "medium_count": 0, "low_count": 0, "quality_issues": 0}
intervention_count = 0

for task, tclasses in tasks:
    target_students = [s for s in all_students if s.class_id in [c.id for c in tclasses]]
    random.shuffle(target_students)
    # 80% 学生提交，10% 进行中，10% 未开始
    submit_count = int(len(target_students) * 0.8)
    in_progress_count = int(len(target_students) * 0.1)

    for idx, student in enumerate(target_students):
        if idx < in_progress_count:
            status = "in_progress"
        elif idx >= submit_count:
            continue  # 未开始
        else:
            status = "submitted"

        started = now - timedelta(minutes=20 + idx * 3)
        submitted = started + timedelta(minutes=5 + random.randint(2, 18)) if status == "submitted" else None

        sheet = AnswerSheet(
            school_id=school.id, class_id=student.class_id,
            task_id=task.id, student_id=student.id,
            questionnaire_id=task.questionnaire_id,
            status=status,
            started_at=started,
            submitted_at=submitted,
            total_duration_seconds=int((submitted - started).total_seconds()) if submitted else 0,
        )
        db.add(sheet)
        db.flush()

        if status == "submitted":
            questions = db.query(Question).filter(
                Question.questionnaire_id == task.questionnaire_id).order_by(Question.sort_order).all()
            mode = idx % 10
            for order, q in enumerate(questions, start=1):
                options = db.query(Option).filter(Option.question_id == q.id, Option.score.isnot(None)).order_by(Option.sort_order).all()
                if not options:
                    options = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
                if not options:
                    continue
                selected = pick_answer(idx, len(target_students), q, options)
                db.add(AnswerRecord(
                    answer_sheet_id=sheet.id, question_id=q.id,
                    question_type=q.type,
                    answer_content={"selected_option_id": selected.id},
                    displayed_order=order,
                    duration_seconds=2 if mode == 8 else (3 if mode == 7 else random.randint(3, 8)),
                ))

            scoring_service.calculate_scores(db, sheet.id)
            scoring_service.calculate_quality(db, sheet.id)
            scoring_service.check_risk_alerts(db, sheet.id)

            from app.models.risk import ScoringResult, QualityAssessment, RiskAlert
            sr = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).first()
            qa = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == sheet.id).first()
            if sr:
                if sr.risk_level in ("high", "urgent"):
                    scores["high_count"] += 1
                elif sr.risk_level == "medium":
                    scores["medium_count"] += 1
                else:
                    scores["low_count"] += 1
            if qa and qa.quality_level != "normal":
                scores["quality_issues"] += 1

            # 给高风险学生创建干预记录
            if sr and sr.risk_level in ("high", "urgent") and intervention_count < 8:
                methods = ["student_talk", "counselor_counsel", "parent_communication", "home_visit", "observation", "other"]
                contents = [
                    f"已与{student.real_name}进行一对一谈话，了解近期学习和生活状态。",
                    f"心理老师已针对{student.real_name}开展辅导，学生表示愿意配合。",
                    f"已联系{student.real_name}家长，沟通学生在校情况和测评结果。",
                    f"已进行家访，了解{student.real_name}的家庭环境和日常表现。",
                    f"正在持续观察{student.real_name}的行为和情绪变化，待进一步评估。",
                ]
                db.add(Intervention(
                    school_id=school.id, student_id=student.id,
                    teacher_id=random.choice(teachers).id,
                    method=random.choice(methods),
                    content=random.choice(contents),
                    result=random.choice(["学生情况稳定，建议继续关注", "已与家长达成共识，后续家校配合", "学生愿意继续沟通，建议每周访谈"]),
                    follow_up_suggestion="建议两周内再次跟进了解情况",
                    need_follow_up=random.choice([True, True, False]),
                    status=random.choice(["completed", "follow_up", "in_progress", "pending"]),
                    next_follow_up_time=now + timedelta(days=random.randint(3, 14)) if random.random() > 0.3 else None,
                ))
                intervention_count += 1

            db.flush()
    db.commit()
    print(f"  Task '{tname}': {submit_count} submitted, {in_progress_count} in-progress, rest unstarted")

print(f"\nResults: {scores}")
print(f"  Interventions: {intervention_count}")

# 额外加几条已完成的干预
ac = db.query(Intervention).count()
if ac < 10:
    for i in range(10 - ac):
        s = random.choice(all_students)
        db.add(Intervention(
            school_id=school.id, student_id=s.id,
            teacher_id=random.choice(teachers).id,
            method=random.choice(["student_talk", "parent_communication"]),
            content=f"补充干预记录 #{i+1}：已与相关人员进行沟通，评估学生状态并制定后续支持计划。",
            result="情况稳定",
            status="completed",
        ))
db.commit()

print("\nDone! Final stats:")
print(f"  Students: {db.query(User).filter(User.school_id==school.id, User.role=='student').count()}")
print(f"  Teachers: {db.query(User).filter(User.school_id==school.id, User.role=='teacher').count()}")
print(f"  Tasks: {db.query(Task).filter(Task.school_id==school.id).count()}")
print(f"  AnswerSheets: {db.query(AnswerSheet).count()}")
print(f"  Interventions: {db.query(Intervention).filter(Intervention.school_id==school.id).count()}")
from app.models.risk import RiskAlert
print(f"  RiskAlerts: {db.query(RiskAlert).filter(RiskAlert.school_id==school.id).count()}")

db.close()
