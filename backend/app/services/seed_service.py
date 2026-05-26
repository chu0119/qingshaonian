"""
种子数据服务 - 创建20套专业内置问卷（基于国家公开标准量表），
含注意力检测题、反向题、矛盾题组配置。
同时生成模拟学生、教师、任务和答卷数据。
"""
import json
import random
from sqlalchemy.orm import Session
from ..models.user import School, User, Grade, Class, TeacherClass
from ..models.questionnaire import Questionnaire, Question, Option, ContradictionGroup
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.risk import ScoringResult, QualityAssessment, RiskAlert, Intervention
from ..utils.password import hash_password
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))

# ============================================================
# 通用选项模板
# ============================================================
# 5级频率 (0-4)
scale5 = [
    {"content": "完全不符合", "score": 0},
    {"content": "不太符合", "score": 1},
    {"content": "一般", "score": 2},
    {"content": "比较符合", "score": 3},
    {"content": "完全符合", "score": 4},
]
# 5级频率反向 (4-0)
scale5r = [
    {"content": "完全不符合", "score": 4},
    {"content": "不太符合", "score": 3},
    {"content": "一般", "score": 2},
    {"content": "比较符合", "score": 1},
    {"content": "完全符合", "score": 0},
]
# 5级行为频率 (0-4)
freq5 = [
    {"content": "从未", "score": 0},
    {"content": "偶尔", "score": 1},
    {"content": "有时", "score": 2},
    {"content": "经常", "score": 3},
    {"content": "几乎每天", "score": 4},
]
# MSSMHS专用 - 5级症状严重度 (1-5)
mssmhs_opts = [
    {"content": "从无", "score": 1},
    {"content": "轻度", "score": 2},
    {"content": "中度", "score": 3},
    {"content": "偏重", "score": 4},
    {"content": "严重", "score": 5},
]
mssmhs_opts_r = [
    {"content": "从无", "score": 5},
    {"content": "轻度", "score": 4},
    {"content": "中度", "score": 3},
    {"content": "偏重", "score": 2},
    {"content": "严重", "score": 1},
]
# DASS-21专用 - 4级 (0-3)
dass_opts = [
    {"content": "不符合", "score": 0},
    {"content": "有时符合", "score": 1},
    {"content": "常常符合", "score": 2},
    {"content": "总是符合", "score": 3},
]
# PHQ-9 / GAD-7专用 - 4级近两周频率 (0-3)
phq9_opts = [
    {"content": "完全不会", "score": 0},
    {"content": "好几天", "score": 1},
    {"content": "一半以上天数", "score": 2},
    {"content": "几乎每天", "score": 3},
]
# 睡眠专用 - 5级 (0-4)
sleep_opts = [
    {"content": "没有", "score": 0},
    {"content": "少于1次/周", "score": 1},
    {"content": "1-2次/周", "score": 2},
    {"content": "3次以上/周", "score": 3},
    {"content": "几乎每天", "score": 4},
]

# ---- 注意力检测选项（score全为0）----
att_check5 = [
    {"content": "完全不符合", "score": 0},
    {"content": "不太符合", "score": 0},
    {"content": "一般", "score": 0},
    {"content": "比较符合", "score": 0},
    {"content": "完全符合", "score": 0},
]
att_check4 = [
    {"content": "完全不符合", "score": 0},
    {"content": "不太符合", "score": 0},
    {"content": "一般", "score": 0},
    {"content": "比较符合", "score": 0},
]
att_check_mssmhs = [
    {"content": "从无", "score": 0},
    {"content": "轻度", "score": 0},
    {"content": "中度", "score": 0},
    {"content": "偏重", "score": 0},
    {"content": "严重", "score": 0},
]
att_check_dass = [
    {"content": "不符合", "score": 0},
    {"content": "有时符合", "score": 0},
    {"content": "常常符合", "score": 0},
    {"content": "总是符合", "score": 0},
]
att_check_phq9 = [
    {"content": "完全不会", "score": 0},
    {"content": "好几天", "score": 0},
    {"content": "一半以上天数", "score": 0},
    {"content": "几乎每天", "score": 0},
]
att_check_freq5 = [
    {"content": "从未", "score": 0},
    {"content": "偶尔", "score": 0},
    {"content": "有时", "score": 0},
    {"content": "经常", "score": 0},
    {"content": "几乎每天", "score": 0},
]
att_check_sleep = [
    {"content": "没有", "score": 0},
    {"content": "少于1次/周", "score": 0},
    {"content": "1-2次/周", "score": 0},
    {"content": "3次以上/周", "score": 0},
    {"content": "几乎每天", "score": 0},
]

# 8个维度的英文 key
DIM_EMOTION = "emotion"
DIM_SLEEP = "sleep"
DIM_ACADEMIC = "academic_pressure"
DIM_INTERPERSONAL = "interpersonal"
DIM_FAMILY = "family_support"
DIM_CAMPUS = "campus_safety"
DIM_INTERNET = "internet_use"
DIM_SELF_SAFETY = "self_safety"


def seed_demo_data(db: Session):
    """主入口：创建学校种子数据（教师、学生、20套内置问卷、模拟答卷）"""
    school = db.query(School).filter(School.code == "MINGDE").first()
    if not school:
        return
    school_id = school.id
    grades = {g.name: g for g in db.query(Grade).filter(Grade.school_id == school_id).all()}
    classes = {c.name: c for c in db.query(Class).filter(Class.school_id == school_id).all()}
    existing_students = db.query(User).filter(User.school_id == school_id, User.role == "student").count()
    if existing_students > 0:
        return

    # ---- 创建教师 ----
    teachers_data = [
        ("T001", "张老师", "head_teacher"), ("T002", "李老师", "head_teacher"),
        ("T003", "王老师", "head_teacher"), ("T004", "赵老师", "head_teacher"),
        ("T005", "刘老师", "head_teacher"), ("T006", "陈老师", "head_teacher"),
        ("T007", "周老师", "counselor"), ("T008", "林老师", "counselor"),
    ]
    teachers = {}
    for uname, rname, ttype in teachers_data:
        role = "counselor" if ttype == "counselor" else "teacher"
        u = User(school_id=school_id, username=uname, password_hash=hash_password("123456"),
                 real_name=rname, role=role, teacher_type=ttype, status=True)
        db.add(u); db.flush(); teachers[uname] = u

    class_list = list(classes.values())
    teacher_list = [t for t in teachers.values() if t.role == "teacher"]
    for i, cls in enumerate(class_list):
        if i < len(teacher_list):
            cls.head_teacher_id = teacher_list[i].id
            db.add(TeacherClass(teacher_id=teacher_list[i].id, class_id=cls.id))
    db.flush()

    # ---- 创建学生（每班12名，共72名）----
    surnames = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
                "郑", "钱", "孙", "马", "朱", "胡", "林", "何", "郭", "高",
                "罗", "梁", "宋", "唐", "许", "韩", "冯", "邓", "曹", "彭"]
    given = ["明", "华", "磊", "芳", "婷", "杰", "琳", "浩", "雪", "涛",
             "雨", "超", "峰", "悦", "文", "洋", "思", "宁", "晨", "宇"]
    students = []
    idx = 0
    for cls in class_list:
        for _ in range(12):
            sno = f"S2024{str(idx+1).zfill(3)}"
            sname = random.choice(surnames) + random.choice(given)
            u = User(school_id=school_id, username=sno, password_hash=hash_password("123456"),
                     real_name=sname, role="student", gender=random.choice(["男", "女"]),
                     student_no=sno, grade_id=cls.grade_id, class_id=cls.id, status=True)
            db.add(u); db.flush(); students.append(u); idx += 1
    db.flush()

    # ---- 创建20套内置问卷 ----
    builtin = _create_all_questionnaires(db)
    db.flush()

    # ---- 创建任务并模拟答卷 ----
    q_ids = [q.id for q in builtin]
    tasks_config = [
        ("初一年级综合测评", q_ids[0], [c.id for c in class_list if "初一" in c.name]),
        ("初二年级综合测评", q_ids[0], [c.id for c in class_list if "初二" in c.name]),
        ("全校心理健康筛查", q_ids[2], [c.id for c in class_list]),  # PHQ-9
        ("全校综合风险筛查", q_ids[19], [c.id for c in class_list]),  # 综合风险筛查
    ]
    for tname, qid, target_ids in tasks_config:
        task = Task(school_id=school_id, questionnaire_id=qid, name=tname,
                    target_type="class", target_ids=target_ids, status="active",
                    enable_quality_check=True, created_by=teachers["T001"].id)
        db.add(task); db.flush()
        target_students = [s for s in students if s.class_id in target_ids]
        for student in target_students:
            _create_mock_answer(db, task, student, school_id)
    db.commit()


# ============================================================
# 辅助函数
# ============================================================
def _mkq(db: Session, title: str, desc: str, cat: str) -> Questionnaire:
    """创建一个内置问卷"""
    q = Questionnaire(school_id=None, title=title, description=desc,
                       category=cat, is_builtin=True, status="active")
    db.add(q); db.flush()
    return q


def _addq(db: Session, q: Questionnaire, qdata_list: list):
    """批量添加题目和选项"""
    for i, qdata in enumerate(qdata_list):
        opts = qdata.pop("options", [])
        qo = Question(questionnaire_id=q.id, sort_order=i, **qdata)
        db.add(qo); db.flush()
        for j, od in enumerate(opts):
            db.add(Option(question_id=qo.id, sort_order=j, **od))
        db.flush()


def _add_cg(db: Session, q_ids: list, pairs_by_q: dict):
    """根据问卷索引添加矛盾题组"""
    for qi, pairs in pairs_by_q.items():
        qid = q_ids[qi]
        qs = {qq.title: qq.id for qq in
              db.query(Question).filter(Question.questionnaire_id == qid).all()}
        for ta, tb, rel in pairs:
            a = qs.get(ta); b = qs.get(tb)
            if a and b:
                db.add(ContradictionGroup(questionnaire_id=qid,
                        question_a_id=a, question_b_id=b,
                        relation_type=rel, max_score_diff=3))


def _add_cross_cg(db: Session, qida: int, qidb: int, title_a: str, title_b: str, rel: str = "opposite"):
    """跨问卷矛盾题组辅助函数"""
    qa = db.query(Question).filter(Question.questionnaire_id == qida,
                                    Question.title == title_a).first()
    qb = db.query(Question).filter(Question.questionnaire_id == qidb,
                                    Question.title == title_b).first()
    if qa and qb:
        db.add(ContradictionGroup(questionnaire_id=qida,
                question_a_id=qa.id, question_b_id=qb.id,
                relation_type=rel, max_score_diff=3))


# ============================================================
# 创建全部20套问卷
# ============================================================
def _create_all_questionnaires(db: Session) -> list[Questionnaire]:
    questionnaires = []

    # ================================================================
    # 问卷1：MSSMHS-中学生心理健康量表 (60题, 10因子)
    # 基于国家经典MSSMHS标准，每因子6题
    # ================================================================
    q = _mkq(db, "MSSMHS-中学生心理健康量表",
        "请根据最近两周的实际情况如实回答。本量表是中学生心理健康评估的经典工具，"
        "涵盖十个维度，帮助你全面了解自己的心理状态。答案没有对错之分，请根据第一反应作答。",
        "mental_health")
    _addq(db, q, [
        # ---- 因子1: 强迫症状 (6题) ----
        {"title": "我脑子中反复出现一些不必要的想法或念头，无法摆脱", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我总是不放心，需要反复检查已经做过的事情（如门窗、书包、作业）",
         "type": "scale", "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我做作业或考试时总是反复检查，担心出错", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "我会不自觉地重复某些动作或行为（如反复洗手、数数、摆放物品）",
         "type": "scale", "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我做事追求完美，稍有差错就很不安", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我能接受一些事情做得不够完美，不会太纠结", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子2: 偏执 (6题) ----
        {"title": "我觉得大多数人是不可信任的", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我感到别人在背后议论我或对我有看法", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我总觉得别人占了我的便宜或对我不公平", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我对别人的言行特别敏感，总觉得是在针对我", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我觉得有人故意跟我过不去", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我相信大多数人都是善意的，不会故意伤害我", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子3: 敌对 (6题) ----
        {"title": "我容易发怒或情绪激动", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我有时控制不住想摔东西或伤害别人的冲动", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我经常与人争论甚至争吵", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我看不惯别人的行为时，会忍不住指责对方", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我有时会无缘无故想大喊大叫或破坏东西", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "即使生气，我也能控制住自己的言行", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子4: 人际关系敏感 (6题) ----
        {"title": "我特别在意别人对我的看法和评价", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "与别人相处时我感到不自在或紧张", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我总觉得别人在背后笑话我", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我在人群中感到孤独，即使身边有人", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我害怕被别人拒绝或冷落", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我能自然地与他人相处，不会想太多", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子5: 抑郁 (6题) ----
        {"title": "我感到心情低落或郁闷", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我对平时喜欢的事情失去了兴趣", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我觉得生活没有意义或对未来感到绝望", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我经常想哭或感到想哭", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我感到自己没什么价值，让别人失望", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我对生活充满热情和期待", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子6: 焦虑 (6题) ----
        {"title": "我无缘无故地感到紧张或焦虑", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我心里不踏实，总觉得有什么不好的事要发生", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我经常感到心慌、心跳加快或呼吸急促", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我手心出汗或身体发抖，即使在平常的情境下", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我因为紧张而无法集中注意力做事情", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我能保持内心的平静和放松", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 注意力检测题1 ----
        {"title": "本题为注意力检测题，请选择「偏重」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "偏重",
         "dimension": DIM_EMOTION, "options": att_check_mssmhs},

        # ---- 因子7: 学习压力 (6题) ----
        {"title": "我感到学习负担太重，压得喘不过气来", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "我一听说要考试就感到紧张不安", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "我觉得无论怎么努力，成绩都无法提高", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "因为学习压力，我经常头痛、胃痛或失眠", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "我对学习感到厌倦，不想去学校", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "我能够应对目前的学习任务，不会感到过度压力", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子8: 适应不良 (6题) ----
        {"title": "我对学校的规章制度感到不适应", "type": "scale",
         "dimension": DIM_CAMPUS, "options": mssmhs_opts},
        {"title": "我不适应老师的教学方式", "type": "scale",
         "dimension": DIM_CAMPUS, "options": mssmhs_opts},
        {"title": "我不喜欢现在班级的氛围", "type": "scale",
         "dimension": DIM_CAMPUS, "options": mssmhs_opts},
        {"title": "我换了环境后很长时间才能适应", "type": "scale",
         "dimension": DIM_CAMPUS, "options": mssmhs_opts},
        {"title": "我觉得在学校里格格不入", "type": "scale",
         "dimension": DIM_CAMPUS, "options": mssmhs_opts},
        {"title": "我能够较好地适应学校生活和学习节奏", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子9: 情绪不平衡 (6题) ----
        {"title": "我的情绪忽好忽坏，变化很快", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我有时特别兴奋活跃，有时又特别低落消沉", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "一点小事就能让我情绪波动很大", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我对同学的态度的忽冷忽热，变化无常", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我很难让自己的心情长时间保持稳定", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我能够较好地管理自己的情绪，不会大起大落", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 因子10: 心理不平衡 (6题) ----
        {"title": "我经常觉得不公平，凭什么别人比我过得好", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "我看到同学成绩比我好时，心里很不舒服", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": mssmhs_opts},
        {"title": "我嫉妒那些比我受欢迎或条件好的同学", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": mssmhs_opts},
        {"title": "我总觉得自己的付出没有得到应有的回报", "type": "scale",
         "dimension": DIM_EMOTION, "options": mssmhs_opts},
        {"title": "老师对某些同学偏心，让我心里很不平衡", "type": "scale",
         "dimension": DIM_CAMPUS, "options": mssmhs_opts},
        {"title": "我能真心为他人的成功感到高兴", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": mssmhs_opts_r},

        # ---- 注意力检测题2 ----
        {"title": "本题为注意力检测题，请选择「严重」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "严重",
         "dimension": DIM_EMOTION, "options": att_check_mssmhs},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷2：DASS-21情绪自评量表 (21题, 3维度各7题)
    # ================================================================
    q = _mkq(db, "DASS-21情绪自评量表",
        "请仔细阅读以下每个句子，并根据过去一周内符合你的程度，"
        "选择最恰当的选项。本量表用于评估抑郁、焦虑和压力水平，"
        "答案没有对错之分。",
        "mental_health")
    _addq(db, q, [
        # ---- 抑郁维度 (7题) ----
        {"title": "我觉得很难从任何事情中感受到快乐", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到忧郁沮丧，情绪低落", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我无法对任何事情产生热情或兴趣", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我觉得自己没什么可期待的", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到自己没什么价值，是个没用的人", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到生命毫无意义", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我能够从日常生活中找到乐趣和满足", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": dass_opts},

        # ---- 焦虑维度 (7题) ----
        {"title": "我感到口干舌燥", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到呼吸困难或喘不过气来（即使没有运动）", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到身体颤抖或发抖（如手抖）", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我担心自己可能会因为紧张而在公共场合出丑", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到快要崩溃了", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "即使没有进行体力活动，我也感到心跳加速或心慌", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到无缘无故地害怕或恐惧", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「常常符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "常常符合",
         "dimension": DIM_EMOTION, "options": att_check_dass},

        # ---- 压力维度 (7题) ----
        {"title": "我觉得很难让自己安静下来", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我容易因为小事而感到烦躁或发脾气", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到神经紧张，很难放松下来", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我觉得很难容忍别人打扰我正在做的事情", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我发现自己很容易被激怒", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我感到自己消耗了很多精力在应对压力上", "type": "scale",
         "dimension": DIM_EMOTION, "options": dass_opts},
        {"title": "我能够冷静地面对遇到的困难", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": dass_opts},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷3：PHQ-9抑郁症筛查量表 (9题)
    # 基于DSM-5抑郁诊断标准，评估近两周状态
    # ================================================================
    q = _mkq(db, "PHQ-9抑郁症筛查量表",
        "在过去两周中，你有多频繁被以下问题所困扰？请根据实际情况如实选择。"
        "本量表基于抑郁诊断标准，用于初步筛查抑郁状况。",
        "mental_health")
    _addq(db, q, [
        {"title": "做事时提不起劲或没有兴趣", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "感到心情低落、沮丧或绝望", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "入睡困难、睡不安稳或睡眠过多", "type": "scale",
         "dimension": DIM_SLEEP, "options": phq9_opts},
        {"title": "感到疲倦或没有精力", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "食欲不振或吃太多", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "觉得自己很糟——或觉得自己很失败，让自己或家人失望", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "对事物难以集中注意力，例如阅读或看电视时", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "动作或说话速度缓慢到别人已经察觉，或正好相反——"
         "烦躁或坐立不安、动来动去的情况更胜于平常", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "有不如死掉或用某种方式伤害自己的念头", "type": "scale",
         "dimension": DIM_SELF_SAFETY, "options": phq9_opts},
        {"title": "本题为注意力检测题，请选择「好几天」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "好几天",
         "dimension": DIM_EMOTION, "options": att_check_phq9},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷4：GAD-7焦虑症筛查量表 (7题)
    # 评估近两周焦虑状态
    # ================================================================
    q = _mkq(db, "GAD-7焦虑症筛查量表",
        "在过去两周中，你有多频繁被以下问题所困扰？请根据实际情况如实选择。"
        "本量表用于评估广泛性焦虑状况，是国际通用的焦虑筛查工具。",
        "mental_health")
    _addq(db, q, [
        {"title": "感觉紧张、焦虑或急切", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "无法停止或控制担忧", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "对各种各样的事情担忧过多", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "很难放松下来", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "由于不安而无法静坐", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "变得容易烦恼或急躁", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "感到害怕，好像将有可怕的事情发生", "type": "scale",
         "dimension": DIM_EMOTION, "options": phq9_opts},
        {"title": "本题为注意力检测题，请选择「一半以上天数」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "一半以上天数",
         "dimension": DIM_EMOTION, "options": att_check_phq9},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷5：青少年情绪问题综合筛查 (15题)
    # 综合抑郁、焦虑、情绪调节维度，包含2对矛盾题组
    # ================================================================
    q = _mkq(db, "青少年情绪问题综合筛查",
        "请根据最近一个月的实际情况回答以下问题。本问卷帮助全面了解你的情绪状况，"
        "包括抑郁、焦虑和情绪调节能力。答案没有对错之分。",
        "mental_health")
    _addq(db, q, [
        {"title": "最近一个月，我多数时间感到心情愉快", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我对未来感到悲观，看不到希望", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我经常莫名其妙地想哭", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我觉得自己是个有价值的人", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我经常感到紧张或焦虑不安", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我很难控制自己的情绪，容易大起大落", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "遇到挫折时我能较快地调整好自己的心情", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我经常因为一些小事就心烦意乱", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我能够以积极的心态面对生活中的困难", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "本题为注意力检测题，请选择「一般」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "一般",
         "dimension": DIM_EMOTION, "options": att_check5},
        {"title": "我经常感到疲惫，做什么事都提不起精神", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我觉得自己的情绪问题已经影响了学习和生活", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我经常担心自己或家人会发生不好的事情", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "我能够合理地表达自己的情绪，不伤害他人", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我对自己总体是满意的", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷6：校园欺凌风险评估完整版 (15题)
    # 5维度：语言欺凌、身体欺凌、关系欺凌、网络欺凌、旁观者行为
    # ================================================================
    q = _mkq(db, "校园欺凌风险评估完整版",
        "请根据最近一个月在学校的真实经历和感受回答。校园应该是安全的地方，"
        "你的回答将帮助我们及时发现和制止欺凌行为，构建安全的校园环境。"
        "本问卷严格保密。",
        "bullying")
    _addq(db, q, [
        # ---- 语言欺凌 (3题) ----
        {"title": "最近一个月，有同学对我说过难听的话或给我起侮辱性外号",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有同学当众嘲笑或羞辱过我",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有同学用恶意的语言威胁或恐吓我",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},

        # ---- 身体欺凌 (3题) ----
        {"title": "最近一个月，有同学故意推搡、打或踢我",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有同学强行拿走或损坏我的个人物品",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有同学以身体方式威胁或欺负我",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},

        # ---- 关系欺凌 (3题) ----
        {"title": "最近一个月，有同学故意不让我参加集体活动或孤立我",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有同学散布关于我的谣言或恶意中伤",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有同学故意挑拨我和其他同学的关系",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},

        # ---- 网络欺凌 (2题) ----
        {"title": "最近一个月，有人在网上发布或传播关于我的恶意信息",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，有人在社交平台或聊天群中针对性地攻击我",
         "type": "scale", "dimension": DIM_CAMPUS, "options": freq5},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「经常」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "经常",
         "dimension": DIM_CAMPUS, "options": att_check_freq5},

        # ---- 旁观者行为 (2题) ----
        {"title": "看到有同学被欺负时，我会主动上前制止或报告老师",
         "type": "scale", "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "我在学校里感到安全、被尊重",
         "type": "scale", "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},

        # ---- 反向题 ----
        {"title": "总的来说，我在学校没有受到不公平的对待",
         "type": "scale", "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷7：校园人际关系安全问卷 (12题)
    # 学校安全感、师生信任、同伴支持，含反向题和矛盾题
    # ================================================================
    q = _mkq(db, "校园人际关系安全问卷",
        "请根据你在学校的真实感受回答。本问卷关注你在校园中的人际关系和安全感，"
        "帮助我们了解学校氛围，营造更友好的校园环境。",
        "interpersonal")
    _addq(db, q, [
        {"title": "我在学校里感到安全、被保护", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "我在学校里害怕某些同学或感到不安", "type": "scale",
         "dimension": DIM_CAMPUS, "options": scale5},
        {"title": "老师对我是关心和尊重的", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "遇到困难时我知道可以向哪位老师求助", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我觉得老师不公平地对待我", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "我在班级里有可以信任的同学", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我在班级里几乎没有可以说话的人", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "本题为注意力检测题，请选择「比较符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "比较符合",
         "dimension": DIM_INTERPERSONAL, "options": att_check5},
        {"title": "与同学发生矛盾时，我能够较好地处理和化解", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我觉得自己被排斥在班级的主流圈子之外", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "我相信学校是一个安全的地方", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "总体来说，我对在校的人际关系感到满意", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷8：青少年网络成瘾筛查量表-IAT精简版 (20题)
    # 基于Young的网络成瘾测试，适配青少年
    # 5维度：强迫性使用、戒断反应、耐受性、时间管理、人际健康损害
    # ================================================================
    q = _mkq(db, "青少年网络成瘾筛查量表-IAT精简版",
        "请根据最近一个月使用互联网（包括手机、电脑、游戏机等）的实际情况回答。"
        "本量表基于国际通用的网络成瘾测试标准，帮助了解你的网络使用习惯。"
        "请如实作答，答案没有对错之分。",
        "internet_addiction")
    _addq(db, q, [
        # ---- 强迫性使用 (4题) ----
        {"title": "我发现自己上网的时间比预期要长得多", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我经常心里想着网络上的事情，即使在做其他事情时也一样",
         "type": "scale", "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我一有时间就想上网，很难控制这种冲动", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我多次尝试减少上网时间，但都失败了", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},

        # ---- 戒断反应 (4题) ----
        {"title": "不能上网时，我会感到烦躁、焦虑或情绪低落", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "不上网时，我脑子里总想着下一次上网要做什么", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "不上网的时候，我坐立不安、不知道该做什么", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "如果有几天不能上网，我会感到非常难受", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},

        # ---- 耐受性 (4题) ----
        {"title": "我需要比过去花更长的上网时间才能感到满足", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "同样的上网时间已经无法让我感到满意，我需要更多", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我发现自己一直在升级设备或使用更快的网络以获得更好的体验",
         "type": "scale", "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我常常熬夜上网，第二天感到疲惫却仍控制不住", "type": "scale",
         "dimension": DIM_SLEEP, "options": freq5},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「一般」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "一般",
         "dimension": DIM_INTERNET, "options": att_check5},

        # ---- 时间管理 (4题) ----
        {"title": "因为上网，我的学习时间明显减少了", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "我经常因为上网而拖延作业或不去复习", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": freq5},
        {"title": "因为上网，我减少了与家人、朋友的面对面交流", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我能够合理安排上网和学习、休息的时间", "type": "scale",
         "dimension": DIM_INTERNET, "is_reverse": True, "options": scale5r},

        # ---- 人际健康损害 (4题) ----
        {"title": "因为上网，我和家人发生过争吵", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "为了上网，我有时会向家人或朋友隐瞒实际使用时间", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "因为上网，我的学习成绩下降了", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "上网让我逃避了现实中需要面对的问题或烦恼", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷9：手机依赖评估量表 (12题)
    # 评估手机使用对学习、睡眠、社交的影响
    # ================================================================
    q = _mkq(db, "手机依赖评估量表",
        "请根据过去一个月使用手机的实际情况回答。手机给生活带来便利，"
        "但过度使用可能影响学习和健康。本量表帮助评估你的手机使用习惯。",
        "internet_addiction")
    _addq(db, q, [
        {"title": "我每天使用手机的时间超过自己计划的时间", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我经常在上课时忍不住看手机", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": freq5},
        {"title": "晚上睡觉前我会长时间刷手机，导致睡眠不足", "type": "scale",
         "dimension": DIM_SLEEP, "options": freq5},
        {"title": "没有手机在身边时，我会感到焦虑或不安", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我经常因为玩手机而减少与身边人面对面的交流", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "我曾多次尝试减少手机使用时间但没有成功", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我能控制自己使用手机的时间，不影响正常生活", "type": "scale",
         "dimension": DIM_INTERNET, "is_reverse": True, "options": scale5r},
        {"title": "本题为注意力检测题，请选择「比较符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "比较符合",
         "dimension": DIM_INTERNET, "options": att_check5},
        {"title": "因为沉迷手机，我的学习成绩明显下滑", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "吃饭或走路时我也会看手机", "type": "scale",
         "dimension": DIM_INTERNET, "options": freq5},
        {"title": "即使知道不该看手机，我也会不自觉地拿起来刷", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "没有手机，我同样可以过得充实快乐", "type": "scale",
         "dimension": DIM_INTERNET, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷10：家庭支持系统评估量表 (15题)
    # 情感支持、物质支持、信息支持、陪伴支持，含反向题
    # ================================================================
    q = _mkq(db, "家庭支持系统评估量表",
        "请根据你与家人相处的实际情况回答。家庭支持对青少年的健康成长至关重要，"
        "你的回答将帮助我们了解同学们的家庭支持状况，以便提供更有针对性的帮助。",
        "family_relationship")
    _addq(db, q, [
        # ---- 情感支持 (4题) ----
        {"title": "当我心情不好时，家人会耐心倾听并安慰我", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "家人经常表扬和肯定我的努力和进步", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "我感到在家中不被理解或不被重视", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},
        {"title": "家人会尊重我的想法和选择，不强迫我做不喜欢的事", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},

        # ---- 物质支持 (3题) ----
        {"title": "在学习用品、书籍等方面，家人能够满足我的基本需求", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "家人为我提供了良好的学习环境和条件", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "我觉得家里的经济状况让我在同学中感到自卑", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},

        # ---- 信息支持 (3题) ----
        {"title": "当我不知道如何处理问题时，家人会给我好的建议和指导",
         "type": "scale", "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "家人会帮助我了解升学、选课等重要信息", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "我觉得家人无法理解我面临的困难和挑战", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「完全不符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "完全不符合",
         "dimension": DIM_FAMILY, "options": att_check5},

        # ---- 陪伴支持 (3题) ----
        {"title": "家人会花时间陪我参加活动或一起做事情", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "家人太忙，很少有时间和我说说话或关心我的情况", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},
        {"title": "在家里，我感到温暖和安全", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},

        # ---- 反向题 ----
        {"title": "总体来说，我对我的家庭关系感到满意", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷11：童年创伤筛查量表-简版 (20题)
    # 5维度：情感忽视、躯体忽视、情感虐待、躯体虐待、性虐待
    # 基于T/JPMA标准
    # ================================================================
    q = _mkq(db, "童年创伤筛查量表-简版",
        "以下问题涉及你在成长过程中的一些经历。请根据18岁之前的整体情况回答。"
        "这些信息将严格保密，仅用于评估你是否需要额外的心理支持。"
        "如果某些问题让你感到不适，可以选择不回答。",
        "mental_health")
    _addq(db, q, [
        # ---- 情感忽视 (4题) ----
        {"title": "小时候，家里有人让我感到自己很重要或很特别",
         "type": "scale", "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "小时候，我感觉家人之间关系亲密、互相支持",
         "type": "scale", "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "小时候，家里没有人关心我的感受和想法", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},
        {"title": "小时候，我感到自己在家中是多余的人", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},

        # ---- 躯体忽视 (4题) ----
        {"title": "小时候，家里有足够的东西让我吃饱穿暖", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "小时候，家人在我需要看病时能及时带我去医院", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "小时候，家里没有人保护我免受伤害", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},
        {"title": "小时候，我因为无人照顾而经常处于危险之中", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},

        # ---- 情感虐待 (4题) ----
        {"title": "小时候，家人经常对我说贬低、侮辱或伤自尊的话", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "小时候，家人曾说过希望我没有出生或类似的话", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "小时候，家人经常用冷漠、拒绝的方式惩罚我", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "小时候，我觉得家人中有人在情绪上虐待我", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},

        # ---- 躯体虐待 (4题) ----
        {"title": "小时候，我曾被家人打得瘀青、留下伤痕", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "小时候，家人用物品（皮带、棍子等）打过我", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "小时候，我曾被家人推撞或摔到地上", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "小时候，我觉得家人中有人在身体上虐待我", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「比较符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "比较符合",
         "dimension": DIM_FAMILY, "options": att_check5},

        # ---- 性虐待 (3题) ----
        {"title": "小时候，有人试图以性的方式触碰我或让我触碰他/她",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "options": freq5},
        {"title": "小时候，有人强迫或威胁我与他们发生与性相关的行为",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "options": freq5},
        {"title": "小时候，我认为自己遭受过性方面的虐待", "type": "scale",
         "dimension": DIM_SELF_SAFETY, "options": scale5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷12：青少年自我保护意识评估 (12题)
    # 安全知识、危险识别、求助意识、法律常识
    # ================================================================
    q = _mkq(db, "青少年自我保护意识评估",
        "请根据你对安全知识的了解和个人行为习惯如实回答。"
        "本问卷帮助了解同学们的自我保护意识和能力，以便学校开展更有针对性的安全教育。",
        "safety_awareness")
    _addq(db, q, [
        # ---- 安全知识 (3题) ----
        {"title": "我知道在地震、火灾等紧急情况下如何正确逃生和自救",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "我了解基本的交通规则，并能在日常生活中遵守",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "我知道如何识别常见的诈骗手段（如电话诈骗、网络诈骗）",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},

        # ---- 危险识别 (3题) ----
        {"title": "当有人让我感到不舒服或被冒犯时，我能识别这是危险信号",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "我知道哪些地方和时间段对我来说可能存在危险",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我有过独自去偏僻或不安全地方的情况",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "options": freq5},

        # ---- 求助意识 (3题) ----
        {"title": "遇到危险或紧急情况时，我知道拨打110或向周围人求助",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "遇到心理困扰时，我知道可以向学校的心理老师寻求帮助",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "当被欺负或受到不公平对待时，我会选择默默忍受",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "options": scale5},

        # ---- 法律常识 (3题) ----
        {"title": "我了解《中华人民共和国未成年人保护法》的基本内容",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "我知道未满18周岁的青少年有哪些合法权益",
         "type": "scale", "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "本题为注意力检测题，请选择「完全不符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "完全不符合",
         "dimension": DIM_SELF_SAFETY, "options": att_check5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷13：校园安全感知量表 (10题)
    # 物理安全、心理安全、应急能力
    # ================================================================
    q = _mkq(db, "校园安全感知量表",
        "请根据你在学校的实际感受回答。本量表评估你对校园安全的感知，"
        "包括物理环境安全、心理安全感和应急处理能力。",
        "safety_awareness")
    _addq(db, q, [
        # ---- 物理安全 (3题) ----
        {"title": "我觉得学校的建筑、设施和环境是安全的", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "学校有足够的安全设施（如消防设备、监控、安保人员）",
         "type": "scale", "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "我担心在学校里会发生安全事故", "type": "scale",
         "dimension": DIM_CAMPUS, "options": scale5},

        # ---- 心理安全 (4题) ----
        {"title": "在校园里，我不用担心被欺负或嘲笑", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "我可以自由地在课堂上表达自己的想法，不用担心被否定",
         "type": "scale", "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "在校园中我会刻意避开某些地方或某些人", "type": "scale",
         "dimension": DIM_CAMPUS, "options": scale5},
        {"title": "我觉得学校的整体氛围是友好和包容的", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},

        # ---- 应急能力 (3题) ----
        {"title": "学校定期组织安全演练（如消防疏散、地震避险等）",
         "type": "scale", "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "本题为注意力检测题，请选择「一般」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "一般",
         "dimension": DIM_CAMPUS, "options": att_check5},
        {"title": "如果发生紧急事件，我相信学校能妥善处理", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷14：青少年社交能力评估 (12题)
    # 社交主动性、沟通能力、冲突处理、社交焦虑，含反向题和矛盾题
    # ================================================================
    q = _mkq(db, "青少年社交能力评估",
        "请根据你与同学、老师及其他人交往的实际情况回答。"
        "本问卷帮助评估你的社交能力，了解你在人际交往中的优势和需要提升的方面。",
        "interpersonal")
    _addq(db, q, [
        # ---- 社交主动性 (3题) ----
        {"title": "我会主动与新同学打招呼或交谈", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "在班级或小组讨论中，我会积极表达自己的想法", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我很少主动与人交流，宁愿一个人待着", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},

        # ---- 沟通能力 (3题) ----
        {"title": "我能够清晰地表达自己的想法和感受", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "与别人交谈时，我会认真倾听并理解对方的观点", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我经常因为表达不清楚而让别人误解我", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},

        # ---- 冲突处理 (3题) ----
        {"title": "与同学发生矛盾时，我能冷静地沟通解决问题", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我会换位思考，理解对方的立场和感受", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "和同学发生争执时，我往往选择冷战或回避", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「完全符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "完全符合",
         "dimension": DIM_INTERPERSONAL, "options": att_check5},

        # ---- 社交焦虑 (3题) ----
        {"title": "我在陌生人面前或人多的地方容易紧张", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "我担心自己在社交场合说错话或做错事", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "总体来说，我对自己的社交能力感到满意", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷15：同伴关系质量量表 (10题)
    # 友谊质量、同伴接纳、孤独感
    # ================================================================
    q = _mkq(db, "同伴关系质量量表",
        "请根据你与同龄伙伴交往的真实感受回答。良好的同伴关系是青少年健康成长的重要资源，"
        "本问卷帮助你了解自己在同伴关系中的状况。",
        "interpersonal")
    _addq(db, q, [
        # ---- 友谊质量 (4题) ----
        {"title": "我有一个或多个可以倾诉心事的好朋友", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我的好朋友会在我遇到困难时帮助我", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我和好朋友之间互相信任、彼此尊重", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我和好朋友之间经常发生矛盾和不愉快", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": freq5},

        # ---- 同伴接纳 (3题) ----
        {"title": "在班级里，我感到被同学们接纳和欢迎", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "同学们愿意和我一起参加集体活动", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "休息时间或课外，我常常独自一人，没有人和我一起",
         "type": "scale", "dimension": DIM_INTERPERSONAL, "options": freq5},

        # ---- 孤独感 (3题) ----
        {"title": "我感到自己被同伴群体排斥在外", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "我经常感到孤独，即使身边有人也还是觉得孤单", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "本题为注意力检测题，请选择「完全不符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "完全不符合",
         "dimension": DIM_INTERPERSONAL, "options": att_check5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷16：学业压力综合评估 (15题)
    # 学业负担、考试压力、成绩焦虑、学习动力，含注意力检测题
    # ================================================================
    q = _mkq(db, "学业压力综合评估",
        "请根据最近一个月在学习方面的真实感受回答。适度的学业压力是正常的，"
        "但过度的压力可能影响身心健康。本问卷帮助全面评估你的学业压力状况。",
        "academic_pressure")
    _addq(db, q, [
        # ---- 学业负担 (4题) ----
        {"title": "我觉得每天的作业量太大，经常做到很晚", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "我需要参加很多课外辅导班，感觉时间完全不够用", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": freq5},
        {"title": "我觉得学校的学习任务超出了我的承受能力", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "我能够合理规划和完成学习任务", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},

        # ---- 考试压力 (4题) ----
        {"title": "考试前一周，我会变得非常紧张、焦虑", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "我经常梦到考试失利或做不完题目的场景", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": freq5},
        {"title": "因为担心成绩，我考前会出现身体不适（如头痛、胃痛）",
         "type": "scale", "dimension": DIM_ACADEMIC, "options": freq5},
        {"title": "考试对我来说只是检验学习效果的一种方式，不会过度紧张",
         "type": "scale", "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},

        # ---- 成绩焦虑 (4题) ----
        {"title": "我经常担心考试成绩达不到家长或老师的期望", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "看到别人成绩比我好时，我会感到焦虑和自卑", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "我因为成绩问题而受到了家长的批评或惩罚", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},
        {"title": "我对自己的学习成绩和进步感到满意", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「比较符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "比较符合",
         "dimension": DIM_ACADEMIC, "options": att_check5},

        # ---- 学习动力 (3题) ----
        {"title": "我对学习充满热情和兴趣", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "学习让我感到充实和有成就感", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "因为学习压力，我曾经有过不想上学的想法", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": freq5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷17：考试焦虑量表-TAS精简版 (10题)
    # 考试前/中/后的焦虑表现
    # ================================================================
    q = _mkq(db, "考试焦虑量表-TAS精简版",
        "请根据你在考试情境下的真实感受回答。考试焦虑是许多学生面临的常见问题，"
        "适度的焦虑有助于发挥，但过度焦虑可能影响考试表现。",
        "academic_pressure")
    _addq(db, q, [
        # ---- 考前焦虑 (3题) ----
        {"title": "考试前几天，我就开始感到紧张不安，难以集中复习", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "想到即将到来的考试，我晚上睡不好觉", "type": "scale",
         "dimension": DIM_SLEEP, "options": scale5},
        {"title": "考前我能冷静地制定复习计划并按计划执行", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},

        # ---- 考中焦虑 (4题) ----
        {"title": "考试时，我会感到心跳加快、手心出汗", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "考试过程中，我的脑子会一片空白，想不起复习过的内容",
         "type": "scale", "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "考试时我会反复查看时间，担心做不完", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "考试过程中我能保持专注，不受周围环境影响", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},

        # ---- 考后焦虑 (3题) ----
        {"title": "考试结束后，我会反复回想做错的题目，长时间无法释怀",
         "type": "scale", "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "考完试等待成绩期间，我会感到极度焦虑", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "本题为注意力检测题，请选择「一般」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "一般",
         "dimension": DIM_ACADEMIC, "options": att_check5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷18：中学生积极心理健康量表 (24题)
    # 基于北大2025年版，4维度：人际和谐、学业胜任、自我控制、自我满足
    # 得分越高越健康（与传统量表反向）
    # ================================================================
    q = _mkq(db, "中学生积极心理健康量表",
        "请根据最近一个月的实际情况回答。本量表关注你的积极心理品质和健康资源，"
        "帮助你发现自身的优势和潜能。得分越高表示心理越健康。",
        "mental_health")
    _addq(db, q, [
        # ---- 人际和谐 (6题) ----
        {"title": "我能够与同学和睦相处，互帮互助", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我善于倾听他人的想法和感受", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我能够理解并尊重与自己观点不同的人", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我在集体中能够较好地配合和协作", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "我经常与家人分享我的生活和感受", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "当我需要帮助时，我愿意向身边的人求助", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},

        # ---- 学业胜任 (6题) ----
        {"title": "我对学习新知识充满兴趣和动力", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "遇到学习困难时，我会主动想办法解决", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "我能够较好地安排学习时间和计划", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "我相信通过努力可以提高自己的学习成绩", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "我在课堂上能够认真听讲并积极思考", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "我对自己的学习方法和效率感到满意", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},

        # ---- 注意力检测题 ----
        {"title": "本题为注意力检测题，请选择「一般」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "一般",
         "dimension": DIM_EMOTION, "options": att_check5},

        # ---- 自我控制 (6题) ----
        {"title": "我能够较好地控制自己的情绪，不轻易发怒", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "即使面对诱惑，我也能坚持完成应该做的事情", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我能够合理控制上网和娱乐的时间", "type": "scale",
         "dimension": DIM_INTERNET, "is_reverse": True, "options": scale5r},
        {"title": "遇到突发事件时，我能够保持冷静和理智", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我能够遵守纪律和规则，不轻易违规", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "我通常会三思而后行，不冲动做决定", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},

        # ---- 自我满足 (6题) ----
        {"title": "我对现在的自己感到基本满意", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我对未来充满了希望和期待", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我觉得自己的生活有明确的目标和方向", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我能够从日常生活的小事中找到快乐", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "我对自己的成长和进步感到欣慰", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "总体来说，我是一个幸福的人", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷19：睡眠质量评估量表 (7题)
    # 基于T/JPMA标准，含注意力检测题
    # ================================================================
    q = _mkq(db, "睡眠质量评估量表",
        "请根据最近一个月的睡眠情况如实回答。良好的睡眠对学习和健康都非常重要，"
        "本量表帮助评估你的睡眠质量。",
        "mental_health")
    _addq(db, q, [
        {"title": "最近一个月，我入睡困难（超过30分钟才能睡着）", "type": "scale",
         "dimension": DIM_SLEEP, "options": sleep_opts},
        {"title": "最近一个月，我夜间容易醒来或醒得太早", "type": "scale",
         "dimension": DIM_SLEEP, "options": sleep_opts},
        {"title": "最近一个月，我早上醒来时感到精力充沛、休息充分",
         "type": "scale", "dimension": DIM_SLEEP, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我对自己的整体睡眠质量不满意", "type": "scale",
         "dimension": DIM_SLEEP, "options": scale5},
        {"title": "最近一个月，睡眠问题已经影响了我的学习和生活", "type": "scale",
         "dimension": DIM_SLEEP, "options": scale5},
        {"title": "最近一个月，我需要借助药物或其他方式才能入睡",
         "type": "scale", "dimension": DIM_SLEEP, "options": freq5},
        {"title": "本题为注意力检测题，请选择「比较符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "比较符合",
         "dimension": DIM_SLEEP, "options": att_check5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 问卷20：青少年综合风险筛查完整版 (30题)
    # 涵盖全部8个维度，多组矛盾题，多道注意力检测题
    # ================================================================
    q = _mkq(db, "青少年综合风险筛查完整版",
        "本问卷是一个综合性评估工具，涵盖心理健康、睡眠、学业压力、人际关系、"
        "家庭支持、校园安全、网络使用和自我保护八大方面。请根据最近一个月的实际"
        "情况如实回答。你的作答将帮助我们全面了解你的状况，提供更有针对性的支持。",
        "custom")
    _addq(db, q, [
        # ---- 情绪 (4题) ----
        {"title": "最近一个月，我大多数时候心情愉快", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我经常感到情绪低落、提不起精神", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "最近一个月，我对未来感到迷茫或没有希望", "type": "scale",
         "dimension": DIM_EMOTION, "options": scale5},
        {"title": "最近一个月，我能够有效处理自己的负面情绪", "type": "scale",
         "dimension": DIM_EMOTION, "is_reverse": True, "options": scale5r},

        # ---- 睡眠 (3题) ----
        {"title": "最近一个月，我作息规律，睡眠充足", "type": "scale",
         "dimension": DIM_SLEEP, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我经常因为各种原因熬夜或失眠", "type": "scale",
         "dimension": DIM_SLEEP, "options": freq5},
        {"title": "最近一个月，因为睡眠问题我白天上课时总是犯困", "type": "scale",
         "dimension": DIM_SLEEP, "options": freq5},

        # ---- 注意力检测题1 ----
        {"title": "本题为注意力检测题，请选择「从未」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "从未",
         "dimension": DIM_EMOTION, "options": att_check_freq5},

        # ---- 学业压力 (4题) ----
        {"title": "最近一个月，我觉得学习给了我很大的心理负担", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": scale5},
        {"title": "最近一个月，我因为压力大而有过不想上学的念头", "type": "scale",
         "dimension": DIM_ACADEMIC, "options": freq5},
        {"title": "我对自己的学习进步感到满意和自豪", "type": "scale",
         "dimension": DIM_ACADEMIC, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，考试或成绩方面的担忧严重影响了我的日常生活",
         "type": "scale", "dimension": DIM_ACADEMIC, "options": scale5},

        # ---- 人际关系 (4题) ----
        {"title": "最近一个月，我有可以倾诉烦恼的好朋友", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我经常感到被同学排斥或忽视", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},
        {"title": "最近一个月，我和同学之间的关系总体是融洽的", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我因为人际关系问题而苦恼", "type": "scale",
         "dimension": DIM_INTERPERSONAL, "options": scale5},

        # ---- 家庭支持 (4题) ----
        {"title": "最近一个月，我和家人的关系总体是和睦的", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，家庭问题让我感到痛苦或压力很大", "type": "scale",
         "dimension": DIM_FAMILY, "options": scale5},
        {"title": "遇到困难时，我的家人会给我有力的支持和帮助", "type": "scale",
         "dimension": DIM_FAMILY, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，在家时我经常感到紧张或害怕", "type": "scale",
         "dimension": DIM_FAMILY, "options": freq5},

        # ---- 注意力检测题2 ----
        {"title": "本题为注意力检测题，请选择「完全符合」", "type": "single_choice",
         "is_attention_check": True, "attention_correct_answer": "完全符合",
         "dimension": DIM_EMOTION, "options": att_check5},

        # ---- 校园安全 (4题) ----
        {"title": "最近一个月，我在学校感到安全和被尊重", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，有同学故意伤害、威胁或孤立过我", "type": "scale",
         "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "最近一个月，我在学校遇到过让我害怕的人或事", "type": "scale",
         "dimension": DIM_CAMPUS, "options": freq5},
        {"title": "我相信学校能够保障我的安全", "type": "scale",
         "dimension": DIM_CAMPUS, "is_reverse": True, "options": scale5r},

        # ---- 网络使用 (4题) ----
        {"title": "最近一个月，我经常因为上网或玩游戏而耽误正事", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "最近一个月，没有网络时我会感到焦虑或烦躁", "type": "scale",
         "dimension": DIM_INTERNET, "options": scale5},
        {"title": "我能够很好地控制自己的上网时间", "type": "scale",
         "dimension": DIM_INTERNET, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，网络使用对我的学习成绩产生了负面影响",
         "type": "scale", "dimension": DIM_ACADEMIC, "options": scale5},

        # ---- 自我保护 (3题) ----
        {"title": "遇到个人安全问题时，我知道如何保护自己", "type": "scale",
         "dimension": DIM_SELF_SAFETY, "is_reverse": True, "options": scale5r},
        {"title": "最近一个月，我有过自我伤害的念头或行为", "type": "scale",
         "dimension": DIM_SELF_SAFETY, "options": freq5},
        {"title": "最近一个月，我为了寻求刺激而做过危险的事情", "type": "scale",
         "dimension": DIM_SELF_SAFETY, "options": freq5},
    ])
    questionnaires.append(q)

    # ================================================================
    # 设置矛盾题组
    # ================================================================
    q_ids = [qq.id for qq in questionnaires]

    # 问卷内矛盾题组
    _add_cg(db, q_ids=q_ids, pairs_by_q={
        # 问卷0 (MSSMHS): 各因子内的正反向题对
        0: [
            ("我脑子中反复出现一些不必要的想法或念头，无法摆脱",
             "我能接受一些事情做得不够完美，不会太纠结", "opposite"),
            ("我觉得大多数人是不可信任的",
             "我相信大多数人都是善意的，不会故意伤害我", "opposite"),
            ("我容易发怒或情绪激动",
             "即使生气，我也能控制住自己的言行", "opposite"),
            ("我特别在意别人对我的看法和评价",
             "我能自然地与他人相处，不会想太多", "opposite"),
            ("我感到心情低落或郁闷",
             "我对生活充满热情和期待", "opposite"),
            ("我无缘无故地感到紧张或焦虑",
             "我能保持内心的平静和放松", "opposite"),
            ("我感到学习负担太重，压得喘不过气来",
             "我能够应对目前的学习任务，不会感到过度压力", "opposite"),
            ("我不适应学校的规章制度",
             "我能够较好地适应学校生活和学习节奏", "opposite"),
            ("我的情绪忽好忽坏，变化很快",
             "我能够较好地管理自己的情绪，不会大起大落", "opposite"),
            ("我经常觉得不公平，凭什么别人比我过得好",
             "我能真心为他人的成功感到高兴", "opposite"),
        ],
        # 问卷1 (DASS-21): 抑郁维度正反向
        1: [
            ("我觉得很难从任何事情中感受到快乐",
             "我能够从日常生活中找到乐趣和满足", "opposite"),
            ("我感到神经紧张，很难放松下来",
             "我能够冷静地面对遇到的困难", "opposite"),
        ],
        # 问卷4 (情绪问题综合筛查): 矛盾题组
        4: [
            ("最近一个月，我多数时间感到心情愉快",
             "最近一个月，我经常因为一些小事就心烦意乱", "opposite"),
            ("我觉得自己是个有价值的人",
             "我对未来感到悲观，看不到希望", "opposite"),
        ],
        # 问卷6 (校园欺凌): 反向题对
        6: [
            ("最近一个月，有同学故意推搡、打或踢我",
             "我在学校里感到安全、被尊重", "opposite"),
        ],
        # 问卷7 (校园人际关系安全): 矛盾题组
        7: [
            ("我在班级里有可以信任的同学",
             "我在班级里几乎没有可以说话的人", "opposite"),
            ("我觉得自己被排斥在班级的主流圈子之外",
             "总体来说，我对在校的人际关系感到满意", "opposite"),
        ],
        # 问卷8 (网络成瘾IAT): 矛盾题组
        8: [
            ("我多次尝试减少上网时间，但都失败了",
             "我能够合理安排上网和学习、休息的时间", "opposite"),
        ],
        # 问卷9 (手机依赖): 矛盾题组
        9: [
            ("我曾多次尝试减少手机使用时间但没有成功",
             "我能控制自己使用手机的时间，不影响正常生活", "opposite"),
        ],
        # 问卷10 (家庭支持): 矛盾题组
        10: [
            ("我感到在家中不被理解或不被重视",
             "总体来说，我对我的家庭关系感到满意", "opposite"),
        ],
        # 问卷14 (社交能力): 矛盾题组
        14: [
            ("我会主动与新同学打招呼或交谈",
             "我很少主动与人交流，宁愿一个人待着", "opposite"),
            ("我担心自己在社交场合说错话或做错事",
             "总体来说，我对自己的社交能力感到满意", "opposite"),
        ],
        # 问卷15 (同伴关系): 矛盾题组
        15: [
            ("在班级里，我感到被同学们接纳和欢迎",
             "我感到自己被同伴群体排斥在外", "opposite"),
        ],
        # 问卷16 (学业压力): 矛盾题组
        16: [
            ("我觉得学校的学习任务超出了我的承受能力",
             "我能够合理规划和完成学习任务", "opposite"),
        ],
        # 问卷17 (考试焦虑TAS): 矛盾题组
        17: [
            ("考试前几天，我就开始感到紧张不安，难以集中复习",
             "考前我能冷静地制定复习计划并按计划执行", "opposite"),
        ],
        # 问卷19 (综合风险筛查): 多组矛盾题
        19: [
            ("最近一个月，我大多数时候心情愉快",
             "最近一个月，我经常感到情绪低落、提不起精神", "opposite"),
            ("最近一个月，我作息规律，睡眠充足",
             "最近一个月，我经常因为各种原因熬夜或失眠", "opposite"),
            ("最近一个月，我有可以倾诉烦恼的好朋友",
             "最近一个月，我经常感到被同学排斥或忽视", "opposite"),
            ("最近一个月，我和家人的关系总体是和睦的",
             "最近一个月，家庭问题让我感到痛苦或压力很大", "opposite"),
            ("最近一个月，我在学校感到安全和被尊重",
             "最近一个月，有同学故意伤害、威胁或孤立过我", "opposite"),
            ("我能够很好地控制自己的上网时间",
             "最近一个月，我经常因为上网或玩游戏而耽误正事", "opposite"),
        ],
    })

    # 跨问卷矛盾题组（问卷18积极题 vs 各消极量表）
    q18_id = q_ids[18]  # 积极心理健康量表
    q_phq9_id = q_ids[2]    # PHQ-9 (index 2)
    q_gad7_id = q_ids[3]    # GAD-7 (index 3)
    q_dass_id = q_ids[1]    # DASS-21 (index 1)
    q_emotion_id = q_ids[4] # 青少年情绪问题综合筛查 (index 4)

    # 积极 vs 抑郁(PHQ-9)
    _add_cross_cg(db, q18_id, q_phq9_id,
        "我对现在的自己感到基本满意",
        "觉得自己很糟——或觉得自己很失败，让自己或家人失望")
    _add_cross_cg(db, q18_id, q_phq9_id,
        "我对未来充满了希望和期待",
        "感到心情低落、沮丧或绝望")
    # 积极 vs 抑郁(DASS-21)
    _add_cross_cg(db, q18_id, q_dass_id,
        "我能够从日常生活的小事中找到快乐",
        "我觉得很难从任何事情中感受到快乐")
    # 积极 vs 焦虑(GAD-7)
    _add_cross_cg(db, q18_id, q_gad7_id,
        "我能够较好地控制自己的情绪，不轻易发怒",
        "感觉紧张、焦虑或急切")
    # 情绪综合筛查 vs PHQ-9
    _add_cross_cg(db, q_emotion_id, q_phq9_id,
        "我觉得自己是个有价值的人",
        "觉得自己很糟——或觉得自己很失败，让自己或家人失望")

    return questionnaires


# ============================================================
# 模拟答卷生成
# ============================================================
def _create_mock_answer(db: Session, task: Task, student: User, school_id: int):
    """模拟答卷 - 含正常/风险/质量异常多种模式"""
    questions = db.query(Question).filter(
        Question.questionnaire_id == task.questionnaire_id
    ).order_by(Question.sort_order).all()
    profile = random.choices(
        ["normal", "medium", "high", "quality_issue"],
        weights=[38, 30, 17, 15]
    )[0]

    sheet = AnswerSheet(
        task_id=task.id, student_id=student.id,
        questionnaire_id=task.questionnaire_id,
        question_order=[q.id for q in questions], status="submitted",
        started_at=datetime.now(tz) - timedelta(minutes=random.randint(5, 30)),
        submitted_at=datetime.now(tz),
    )
    db.add(sheet); db.flush()

    sheet.total_duration_seconds = (
        random.randint(30, 90) if profile == "quality_issue"
        else random.randint(180, 600)
    )
    total_score = 0
    dim_scores = {}
    scores_list = []

    for idx, q in enumerate(questions):
        options = db.query(Option).filter(
            Option.question_id == q.id
        ).order_by(Option.sort_order).all()
        if not options:
            continue

        if q.is_attention_check and profile == "quality_issue":
            chosen = random.choice(options)
        elif q.is_attention_check:
            correct = [o for o in options if o.content == q.attention_correct_answer]
            chosen = correct[0] if correct else options[0]
        elif profile == "high":
            chosen = max(options, key=lambda o: o.score)
        elif profile == "quality_issue" and random.random() < 0.6:
            chosen = options[0]
        else:
            chosen = random.choice(options)

        score = chosen.score
        if q.is_reverse:
            scores = [o.score for o in options]
            score = max(scores) + min(scores) - score
        total_score += score
        scores_list.append(score)
        dim_scores[q.dimension or "general"] = (
            dim_scores.get(q.dimension or "general", 0) + score
        )

        duration = (
            random.randint(1, 8) if profile == "quality_issue"
            else random.randint(3, 20)
        )
        db.add(AnswerRecord(
            answer_sheet_id=sheet.id, question_id=q.id,
            question_type=q.type,
            answer_content={"selected_option_id": chosen.id},
            score=score, duration_seconds=duration,
            displayed_order=idx,
        ))

    avg = total_score / max(len(questions), 1)
    risk_level = (
        "high" if profile == "high"
        else ("medium" if profile == "medium" or avg > 50 else "low")
    )
    db.add(ScoringResult(
        answer_sheet_id=sheet.id, total_score=total_score,
        dimension_scores=dim_scores, risk_level=risk_level,
        risk_type="心理健康风险" if risk_level != "low" else "",
        risk_description="", triggered_rules=[],
    ))

    if profile == "quality_issue":
        qs_val = random.randint(20, 50)
        ql = "severe_anomaly" if qs_val < 40 else "moderate_anomaly"
        retest = True
    else:
        qs_val = random.randint(75, 100)
        ql = "normal" if qs_val >= 80 else "mild_anomaly"
        retest = False

    db.add(QualityAssessment(
        answer_sheet_id=sheet.id, quality_level=ql,
        validity="questionable" if retest else "valid",
        quality_score=qs_val,
        total_duration_seconds=sheet.total_duration_seconds,
        fast_question_count=random.randint(0, 5) if profile == "quality_issue" else 0,
        attention_passed=profile != "quality_issue",
        suggest_retest=retest,
    ))

    if risk_level in ("medium", "high"):
        db.add(RiskAlert(
            school_id=school_id, student_id=student.id,
            answer_sheet_id=sheet.id, task_id=task.id,
            risk_level=risk_level, risk_type="心理健康风险",
            trigger_method="total_score", status="pending",
        ))
