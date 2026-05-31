from copy import deepcopy
import hashlib
import json

from sqlalchemy.orm import Session

from ..models.questionnaire import ContradictionGroup, Option, Question, Questionnaire


DEFAULT_DISCLAIMER = (
    "本问卷仅用于学校教育管理和学生关怀场景下的风险关注筛查，结果不作为医学诊断依据。"
    "建议结合教师观察、学生访谈和学校实际情况综合判断。"
)


LIKERT_5 = [
    {"content": "完全不符合", "score": 0},
    {"content": "不太符合", "score": 1},
    {"content": "一般", "score": 2},
    {"content": "比较符合", "score": 3},
    {"content": "非常符合", "score": 4},
]

FREQ_4 = [
    {"content": "完全不会", "score": 0},
    {"content": "好几天", "score": 1},
    {"content": "一半以上天数", "score": 2},
    {"content": "几乎每天", "score": 3},
]

SLEEP_4 = [
    {"content": "没有", "score": 0},
    {"content": "少于1次/周", "score": 1},
    {"content": "1-2次/周", "score": 2},
    {"content": "3次以上/周", "score": 3},
]

FREQUENCY_5 = [
    {"content": "从不", "score": 0},
    {"content": "很少", "score": 1},
    {"content": "有时", "score": 2},
    {"content": "经常", "score": 3},
    {"content": "总是", "score": 4},
]

AGREE_4 = [
    {"content": "完全不同意", "score": 0},
    {"content": "不太同意", "score": 1},
    {"content": "比较同意", "score": 2},
    {"content": "非常同意", "score": 3},
]

# 罗森伯格自尊量表 (RSES) 4点同意量表
RSES_4 = [
    {"content": "很不符合", "score": 1},
    {"content": "不太符合", "score": 2},
    {"content": "比较符合", "score": 3},
    {"content": "非常符合", "score": 4},
]

# 心理韧性量表 (CD-RISC) 5点频率
CD_RISC_5 = [
    {"content": "从不这样", "score": 0},
    {"content": "偶尔这样", "score": 1},
    {"content": "有时这样", "score": 2},
    {"content": "经常这样", "score": 3},
    {"content": "总是这样", "score": 4},
]

# 孤独感量表 (UCLA) 4点频率
UCLA_4 = [
    {"content": "从不", "score": 1},
    {"content": "偶尔", "score": 2},
    {"content": "有时", "score": 3},
    {"content": "经常", "score": 4},
]

# 社会支持量表 (PSSS) 7点同意
PSSS_7 = [
    {"content": "极不同意", "score": 1},
    {"content": "很不同意", "score": 2},
    {"content": "稍不同意", "score": 3},
    {"content": "中立", "score": 4},
    {"content": "稍同意", "score": 5},
    {"content": "很同意", "score": 6},
    {"content": "极同意", "score": 7},
]

# 儿童抑郁量表 (CDI) 3点频率
CDI_3 = [
    {"content": "偶尔", "score": 0},
    {"content": "经常", "score": 1},
    {"content": "总是", "score": 2},
]

# 优势与困难问卷 (SDQ) 3点
SDQ_3 = [
    {"content": "不符合", "score": 0},
    {"content": "有点符合", "score": 1},
    {"content": "完全符合", "score": 2},
]

# 青少年生活事件量表 (ASLEC) 5点影响程度
ASLEC_5 = [
    {"content": "未发生过", "score": 0},
    {"content": "没有影响", "score": 1},
    {"content": "轻度影响", "score": 2},
    {"content": "中度影响", "score": 3},
    {"content": "重度影响", "score": 4},
    {"content": "极重影响", "score": 5},
]

# 情绪调节问卷 (ERQ) 7点频率
ERQ_7 = [
    {"content": "完全不符合", "score": 1},
    {"content": "比较不符合", "score": 2},
    {"content": "有点不符合", "score": 3},
    {"content": "不确定", "score": 4},
    {"content": "有点符合", "score": 5},
    {"content": "比较符合", "score": 6},
    {"content": "完全符合", "score": 7},
]

# 生活满意度量表 (SWLS) 7点同意
SWLS_7 = [
    {"content": "非常不同意", "score": 1},
    {"content": "不同意", "score": 2},
    {"content": "有点不同意", "score": 3},
    {"content": "不确定", "score": 4},
    {"content": "有点同意", "score": 5},
    {"content": "同意", "score": 6},
    {"content": "非常同意", "score": 7},
]

# 自我效能感量表 (GSES) 4点
GSES_4 = [
    {"content": "完全不正确", "score": 1},
    {"content": "有点正确", "score": 2},
    {"content": "多数正确", "score": 3},
    {"content": "完全正确", "score": 4},
]

# 学习倦怠量表 (ASBI) 5点频率
ASBI_5 = [
    {"content": "完全不符合", "score": 1},
    {"content": "比较不符合", "score": 2},
    {"content": "不确定", "score": 3},
    {"content": "比较符合", "score": 4},
    {"content": "完全符合", "score": 5},
]

# 考试焦虑量表 (TAS) 4点频率
TAS_4 = [
    {"content": "从不这样", "score": 1},
    {"content": "有时这样", "score": 2},
    {"content": "经常这样", "score": 3},
    {"content": "总是这样", "score": 4},
]

QUALITY_RULES_DEFAULT = {
    "fast_answer_ratio_warning": 0.3,
    "fast_answer_ratio_high": 0.5,
    "same_option_ratio_warning": 0.7,
    "same_option_ratio_high": 0.8,
    "max_consecutive_same_warning": 7,
    "max_consecutive_same_high": 10,
    "attention_check_failed_level": "moderate_anomaly",
}

SCORING_RULE_DEFAULT = {
    "method": "sum",
    "score_types": ["single_choice", "multi_choice", "scale", "true_false"],
    "exclude_attention_check": True,
    "exclude_types": ["fill_blank", "short_answer"],
}


def _clone_options(options: list[dict]) -> list[dict]:
    return [dict(item) for item in options]


def _compute_builtin_content_hash(data: dict) -> str:
    payload = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "dimensions": data.get("dimensions", []),
        "questions": data.get("questions", []),
        "scoring_rule": data.get("scoring_rule", {}),
        "risk_rules": data.get("risk_rules", {}),
        "quality_rules": data.get("quality_rules", {}),
        "contradiction_groups": data.get("contradiction_groups", []),
    }
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _options_with_risk(options: list[dict], risk_indexes: list[int]) -> list[dict]:
    cloned = _clone_options(options)
    for idx in risk_indexes:
        if 0 <= idx < len(cloned):
            cloned[idx]["is_risk_option"] = True
    return cloned


def _question(
    code: str,
    title: str,
    dimension: str,
    *,
    options: list[dict],
    qtype: str = "scale",
    reverse: bool = False,
    risk_tag: str = "",
    attention: bool = False,
    attention_answer: str = "",
    description: str = "",
) -> dict:
    return {
        "code": code,
        "title": title,
        "description": description,
        "type": qtype,
        "required": True,
        "dimension": dimension,
        "risk_tag": risk_tag,
        "is_reverse": reverse,
        "is_attention_check": attention,
        "attention_correct_answer": attention_answer,
        "options": _clone_options(options),
    }


def _dimensions(*items: tuple[str, str]) -> list[dict]:
    return [{"code": code, "title": title} for code, title in items]


COMPREHENSIVE_DIMENSIONS = _dimensions(
    ("emotion", "情绪状态"),
    ("sleep", "睡眠状态"),
    ("academic_pressure", "学业压力"),
    ("interpersonal", "人际关系"),
    ("family_support", "家庭支持"),
    ("campus_safety", "校园安全"),
    ("internet_use", "网络使用"),
    ("self_safety", "自我安全"),
)


def _comprehensive_questions() -> list[dict]:
    questions: list[dict] = []
    emotion_items = [
        ("emotion_1", "最近一个月，我经常感到情绪低落，做事提不起劲。", False),
        ("emotion_2", "最近一个月，我会因为小事长时间闷闷不乐。", False),
        ("emotion_3", "最近一个月，我能比较稳定地面对日常压力。", True),
        ("emotion_4", "最近一个月，我经常觉得自己不够好。", False),
        ("emotion_5", "最近一个月，我对未来仍然抱有期待。", True),
    ]
    for code, title, reverse in emotion_items:
        questions.append(_question(code, title, "emotion", options=LIKERT_5, reverse=reverse, risk_tag="emotion"))
    questions.append(
        _question(
            "emotion_attention_1",
            "本题为注意力检测题，请选择“比较符合”。",
            "emotion",
            options=_clone_options(LIKERT_5),
            qtype="single_choice",
            attention=True,
            attention_answer="比较符合",
        )
    )

    sleep_items = [
        ("sleep_1", "最近一个月，我经常需要很久才能入睡。", False),
        ("sleep_2", "最近一个月，我夜里容易醒来。", False),
        ("sleep_3", "最近一个月，我起床后感觉精力充足。", True),
        ("sleep_4", "最近一个月，睡眠问题影响了我第二天上课状态。", False),
        ("sleep_5", "最近一个月，我的作息总体比较规律。", True),
        ("sleep_6", "最近一个月，我常因担心事情而睡不好。", False),
    ]
    for code, title, reverse in sleep_items:
        questions.append(_question(code, title, "sleep", options=LIKERT_5, reverse=reverse, risk_tag="sleep"))

    academic_items = [
        ("academic_1", "最近一个月，我觉得学习任务压得我喘不过气。", False),
        ("academic_2", "最近一个月，一想到考试我就会很紧张。", False),
        ("academic_3", "最近一个月，我能安排好学习节奏。", True),
        ("academic_4", "最近一个月，我担心达不到家长或老师的期待。", False),
        ("academic_5", "最近一个月，我对自己完成学习目标有信心。", True),
        ("academic_6", "最近一个月，我因学习压力出现头痛或胃口差。", False),
    ]
    for code, title, reverse in academic_items:
        questions.append(_question(code, title, "academic_pressure", options=LIKERT_5, reverse=reverse, risk_tag="academic_pressure"))

    interpersonal_items = [
        ("interpersonal_1", "最近一个月，我在班里有可以倾诉烦恼的同学。", True),
        ("interpersonal_2", "最近一个月，我常感觉自己被同学忽视。", False),
        ("interpersonal_3", "最近一个月，我担心主动表达会被人笑话。", False),
        ("interpersonal_4", "最近一个月，我愿意向老师或同伴寻求帮助。", True),
        ("interpersonal_5", "最近一个月，我因为人际关系感到苦恼。", False),
        ("interpersonal_6", "最近一个月，我在集体活动中有归属感。", True),
    ]
    for code, title, reverse in interpersonal_items:
        questions.append(_question(code, title, "interpersonal", options=LIKERT_5, reverse=reverse, risk_tag="interpersonal"))

    family_items = [
        ("family_1", "最近一个月，我能感受到家人对我的支持。", True),
        ("family_2", "最近一个月，我在家里经常感到被指责。", False),
        ("family_3", "最近一个月，我愿意和家人谈自己的烦恼。", True),
        ("family_4", "最近一个月，家庭冲突让我很受影响。", False),
        ("family_5", "最近一个月，我觉得家里有人真正理解我。", True),
        ("family_6", "最近一个月，我在家里会刻意回避交流。", False),
    ]
    for code, title, reverse in family_items:
        questions.append(_question(code, title, "family_support", options=LIKERT_5, reverse=reverse, risk_tag="family_support"))

    campus_items = [
        ("campus_1", "最近一个月，我在学校总体感到安全。", True),
        ("campus_2", "最近一个月，我遇到过让我害怕的校园场景。", False),
        ("campus_3", "最近一个月，我觉得班级氛围比较友善。", True),
        ("campus_4", "最近一个月，有人故意排挤、戏弄或威胁我。", False),
        ("campus_5", "最近一个月，我知道遇到校园安全问题该找谁。", True),
        ("campus_6", "最近一个月，我因为校园关系问题想逃避到校。", False),
    ]
    for code, title, reverse in campus_items:
        options = _options_with_risk(LIKERT_5, [4]) if code in {"campus_4", "campus_6"} else LIKERT_5
        questions.append(_question(code, title, "campus_safety", options=options, reverse=reverse, risk_tag="bullying" if code == "campus_4" else "campus_safety"))

    internet_items = [
        ("internet_1", "最近一个月，我因为上网或玩游戏耽误了正事。", False),
        ("internet_2", "最近一个月，没有网络时我会烦躁不安。", False),
        ("internet_3", "最近一个月，我能控制自己的上网时间。", True),
        ("internet_4", "最近一个月，深夜上网影响了我的休息。", False),
        ("internet_5", "最近一个月，我会因为上网影响和家人的相处。", False),
    ]
    for code, title, reverse in internet_items:
        options = _options_with_risk(LIKERT_5, [4]) if code in {"internet_1", "internet_4"} else LIKERT_5
        questions.append(_question(code, title, "internet_use", options=options, reverse=reverse, risk_tag="internet_use"))
    questions.append(
        _question(
            "internet_attention_1",
            "本题为注意力检测题，请选择“非常符合”。",
            "internet_use",
            options=_clone_options(LIKERT_5),
            qtype="single_choice",
            attention=True,
            attention_answer="非常符合",
        )
    )

    self_safety_items = [
        ("self_safety_1", "最近一个月，我知道遇到危险时如何保护自己。", True),
        ("self_safety_2", "最近一个月，我有过想伤害自己的念头。", False),
        ("self_safety_3", "最近一个月，我做过明知危险却仍想尝试的事情。", False),
        ("self_safety_4", "最近一个月，我愿意在不舒服时向可信任的大人求助。", True),
        ("self_safety_5", "最近一个月，我觉得自己的安全并不重要。", False),
        ("self_safety_6", "最近一个月，我能识别网络和现实中的高风险情境。", True),
    ]
    for code, title, reverse in self_safety_items:
        risk_options = [3, 4] if code in {"self_safety_2", "self_safety_3", "self_safety_5"} else []
        options = _options_with_risk(LIKERT_5, risk_options)
        questions.append(_question(code, title, "self_safety", options=options, reverse=reverse, risk_tag="self_safety"))

    return questions


def _questionnaire(
    code: str,
    title: str,
    category: str,
    description: str,
    applicable_grades: str,
    source_type: str,
    dimensions: list[dict],
    questions: list[dict],
    scoring_rule: dict,
    risk_rules: dict,
    quality_rules: dict | None = None,
    contradiction_groups: list[dict] | None = None,
    version: int = 1,
) -> dict:
    return {
        "code": code,
        "title": title,
        "category": category,
        "description": description,
        "applicable_grades": applicable_grades,
        "source_type": source_type,
        "disclaimer": DEFAULT_DISCLAIMER,
        "dimensions": dimensions,
        "questions": questions,
        "scoring_rule": scoring_rule,
        "risk_rules": risk_rules,
        "quality_rules": quality_rules or deepcopy(QUALITY_RULES_DEFAULT),
        "contradiction_groups": contradiction_groups or [],
        "version": version,
    }


def _phq_like_questions() -> list[dict]:
    prompts = [
        "最近两周，我做事提不起兴趣，或感到没意思。",
        "最近两周，我感到心情低落、沮丧，或觉得没有希望。",
        "最近两周，我入睡困难、容易醒，或睡得过多。",
        "最近两周，我觉得疲惫，做事没有精神。",
        "最近两周，我食欲明显变差或明显增加。",
        "最近两周，我常觉得自己做得不够好，或让人失望。",
        "最近两周，我难以集中注意力完成学习或阅读。",
        "最近两周，我行动变慢，或坐立不安、静不下来。",
        "最近两周，我出现过不想继续承受压力的念头。",
        # 扩充题目
        "最近两周，我经常感到烦躁或易怒。",
        "最近两周，我觉得自己对很多事情都失去了兴趣。",
        "最近两周，我经常感到孤独，即使身边有人。",
        "最近两周，我觉得自己没有什么价值。",
        "最近两周，我经常因为小事而哭泣或想哭。",
        "最近两周，我对未来感到迷茫或没有期待。",
        "最近两周，我觉得自己无法应对学习和生活中的压力。",
        "最近两周，我经常感到身体不舒服（如头痛、胃痛等）。",
        "最近两周，我觉得和朋友或家人的关系变得疏远了。",
        "最近两周，我经常失眠或睡眠质量很差。",
        "最近两周，我觉得自己做什么都提不起劲。",
    ]
    questions = []
    for idx, title in enumerate(prompts, start=1):
        options = _options_with_risk(FREQ_4, [3]) if idx == 9 else FREQ_4
        risk_tag = "self_safety" if idx == 9 else "emotion"
        questions.append(_question(f"phq_like_{idx}", title, "emotion", options=options, risk_tag=risk_tag))
    return questions


def _gad_like_questions() -> list[dict]:
    prompts = [
        "最近两周，我常感觉紧张、担心，停不下来。",
        "最近两周，我很难控制自己的担忧。",
        "最近两周，我会为各种事情过度担心。",
        "最近两周，我放松下来会比较困难。",
        "最近两周，我因为担心而坐立不安。",
        "最近两周，我容易烦躁或心里发急。",
        "最近两周，我总担心会发生不好的事情。",
        # 扩充题目
        "最近两周，我经常感到身体紧绷或肌肉紧张。",
        "最近两周，我因为紧张而影响了学习或考试表现。",
        "最近两周，我经常担心自己在别人面前表现不好。",
        "最近两周，我会因为一些小事就感到很焦虑。",
        "最近两周，我觉得自己很难放松下来。",
        "最近两周，我经常担心自己的健康或身体状况。",
        "最近两周，我因为担心而影响了睡眠质量。",
        "最近两周，我觉得自己承受的压力越来越大。",
    ]
    return [_question(f"gad_like_{idx}", title, "emotion", options=FREQ_4, risk_tag="emotion") for idx, title in enumerate(prompts, start=1)]


def _sleep_questions() -> list[dict]:
    items = [
        ("sleep_ref_1", "最近一个月，我入睡通常需要超过30分钟。", "sleep", False, SLEEP_4),
        ("sleep_ref_2", "最近一个月，我躺下后会反复想事情，难以放松。", "sleep", False, SLEEP_4),
        ("sleep_ref_3", "最近一个月，我夜里容易醒来。", "sleep", False, SLEEP_4),
        ("sleep_ref_4", "最近一个月，我醒来后很难再次入睡。", "sleep", False, SLEEP_4),
        ("sleep_ref_5", "最近一个月，我早晨起床后感觉休息得不错。", "sleep", True, LIKERT_5),
        ("sleep_ref_6", "最近一个月，我白天因为困倦影响学习状态。", "sleep", False, LIKERT_5),
        ("sleep_ref_7", "最近一个月，我会为了完成任务而长期熬夜。", "sleep", False, LIKERT_5),
        ("sleep_ref_8", "最近一个月，我能保持比较固定的入睡时间。", "sleep", True, LIKERT_5),
        ("sleep_ref_9", "最近一个月，我早上起床困难。", "sleep", False, LIKERT_5),
        ("sleep_ref_10", "最近一个月，我午间需要补觉才能坚持学习。", "sleep", False, LIKERT_5),
        ("sleep_ref_11", "最近一个月，我周末和工作日作息差异很大。", "sleep", False, LIKERT_5),
        ("sleep_ref_12", "最近一个月，我觉得自己的睡眠问题需要老师或家长关注。", "sleep", False, LIKERT_5),
        # 扩充题目
        ("sleep_ref_13", "最近一个月，我经常做噩梦。", "sleep", False, SLEEP_4),
        ("sleep_ref_14", "最近一个月，我睡觉时容易被声音或光线惊醒。", "sleep", False, SLEEP_4),
        ("sleep_ref_15", "最近一个月，我经常因为学习压力而睡不好。", "sleep", False, SLEEP_4),
        ("sleep_ref_16", "最近一个月，我觉得自己的睡眠时间不够充足。", "sleep", False, LIKERT_5),
        ("sleep_ref_17", "最近一个月，我经常感到白天精神不振、容易犯困。", "sleep", False, LIKERT_5),
        ("sleep_ref_18", "最近一个月，我的睡眠质量影响了我的情绪和心情。", "sleep", False, LIKERT_5),
    ]
    return [_question(code, title, dimension, options=options, reverse=reverse, risk_tag="sleep") for code, title, dimension, reverse, options in items]


def _bullying_questions() -> list[dict]:
    questions = []
    sections = {
        "victimization": [
            "最近一个月，我被同学起外号或讽刺挖苦。",
            "最近一个月，我被故意排挤在小团体之外。",
            "最近一个月，我被人传播过难堪的消息或图片。",
            "最近一个月，我在网络聊天群里被针对或嘲笑。",
            "最近一个月，我被人推搡、故意碰撞或吓唬。",
            "最近一个月，我因为担心同学反应而不敢表达自己。",
        ],
        "aggression": [
            "最近一个月，我会因为生气故意说难听的话刺激别人。",
            "最近一个月，我会拉拢同学一起冷落某个人。",
            "最近一个月，我会把别人的尴尬当成玩笑传播。",
            "最近一个月，我在网络上说过让别人难受的话。",
            "最近一个月，我会用强硬方式逼别人听从我。",
        ],
        "bystander": [
            "看到同学被欺负时，我通常会装作没看见。",
            "看到同学被欺负时，我愿意想办法求助老师。 ",
            "我担心帮助别人后自己会被针对。",
            "我知道如何在不激化冲突的情况下保护同学。",
            "班里有人受委屈时，我愿意站出来支持他。 ",
        ],
        "help_seeking": [
            "如果自己被欺负，我愿意及时告诉老师或家长。",
            "如果朋友被欺负，我知道可以向谁求助。",
            "我相信学校会认真处理欺凌问题。",
            "我担心求助后事情会变得更糟。",
            "我愿意参与建设更安全的班级氛围。",
        ],
        "safety": [
            "我在班级和校园里总体感到安全。",
            "我觉得班级里同学之间彼此尊重。",
            "我清楚学校关于欺凌和冲突处理的基本规则。",
            "我认为遇到欺凌时学校里的成年人值得信任。",
            "我能识别哪些行为已经构成了伤害。",
        ],
    }
    dimension_map = {
        "victimization": "campus_safety",
        "aggression": "campus_safety",
        "bystander": "interpersonal",
        "help_seeking": "interpersonal",
        "safety": "campus_safety",
    }
    reverse_suffixes = {"help_seeking": {1, 2, 5}, "safety": {1, 2, 3, 4, 5}, "bystander": {2, 4, 5}}
    counter = 1
    for section, prompts in sections.items():
        for idx, prompt in enumerate(prompts, start=1):
            reverse = idx in reverse_suffixes.get(section, set())
            options = _options_with_risk(FREQUENCY_5 if section in {"victimization", "aggression"} else LIKERT_5, [4] if not reverse and section in {"victimization", "aggression"} else [])
            questions.append(
                _question(
                    f"bullying_{counter}",
                    prompt.strip(),
                    dimension_map[section],
                    options=options,
                    reverse=reverse,
                    risk_tag="bullying",
                )
            )
            counter += 1
    return questions


def _internet_questions() -> list[dict]:
    prompts = [
        ("最近一个月，我很难主动结束上网或游戏。", "internet_use", False),
        ("最近一个月，我因为上网占用了本该学习的时间。", "academic_pressure", False),
        ("最近一个月，没有网络时我会明显烦躁。", "internet_use", False),
        ("最近一个月，我能按计划控制刷短视频或玩游戏的时间。", "internet_use", True),
        ("最近一个月，我因为熬夜上网影响了睡眠。", "sleep", False),
        ("最近一个月，我会偷偷延长电子设备使用时间。", "internet_use", False),
        ("最近一个月，我更愿意在线上交流而回避线下互动。", "interpersonal", False),
        ("最近一个月，我因为网络内容情绪起伏较大。", "emotion", False),
        ("最近一个月，我为了上网和家人发生过明显冲突。", "family_support", False),
        ("最近一个月，我能在使用网络后迅速回到学习状态。", "academic_pressure", True),
        ("最近一个月，我会因为网络影响第二天上课精力。", "sleep", False),
        ("最近一个月，我会为了网络活动减少体育或户外活动。", "internet_use", False),
        ("最近一个月，我清楚哪些网络行为可能带来风险。", "self_safety", True),
        ("最近一个月，我会因为网络评价而情绪受挫。", "emotion", False),
        ("最近一个月，我担心自己错过网络消息就会不安心。", "internet_use", False),
        ("最近一个月，我能主动安排电子设备的休息时段。", "internet_use", True),
        ("最近一个月，我因为网络购物、打赏或充值后感到后悔。", "self_safety", False),
        ("最近一个月，我和朋友的线下相处被上网明显挤占。", "interpersonal", False),
        ("最近一个月，我能遵守家里关于用网的约定。", "family_support", True),
        ("最近一个月，我在网络上会分享让自己后悔的内容。", "self_safety", False),
        ("最近一个月，我一有空就会下意识拿起手机。", "internet_use", False),
        ("最近一个月，我可以不依赖网络也让自己放松。", "emotion", True),
    ]
    questions = []
    for idx, (prompt, dimension, reverse) in enumerate(prompts, start=1):
        risk_indexes = [4] if not reverse and dimension in {"internet_use", "self_safety", "sleep"} else []
        questions.append(_question(f"internet_{idx}", prompt, dimension, options=_options_with_risk(LIKERT_5, risk_indexes), reverse=reverse, risk_tag="internet_use" if dimension != "self_safety" else "self_safety"))
    return questions


def _academic_questions() -> list[dict]:
    prompts = [
        ("最近一个月，我觉得作业和学习任务压得我很累。", "academic_pressure", False),
        ("最近一个月，一想到考试我就会紧张。", "academic_pressure", False),
        ("最近一个月，我担心成绩达不到家长期待。", "family_support", False),
        ("最近一个月，我能把学习任务分解并逐步完成。", "academic_pressure", True),
        ("最近一个月，我会因为学习压力影响睡眠。", "sleep", False),
        ("最近一个月，考试前我会出现心慌、出汗等反应。", "emotion", False),
        ("最近一个月，我总担心一次失败就说明自己不行。", "emotion", False),
        ("最近一个月，我能比较客观看待成绩波动。", "emotion", True),
        ("最近一个月，我会因为担心考试而难以集中复习。", "academic_pressure", False),
        ("最近一个月，我对自己完成学习目标有信心。", "academic_pressure", True),
        ("最近一个月，我担心辜负老师的信任。", "interpersonal", False),
        ("最近一个月，我会把很多时间花在反复确认是否会出错。", "academic_pressure", False),
        ("最近一个月，我能向老师同学主动求助学习问题。", "interpersonal", True),
        ("最近一个月，我会因为一次失误否定自己。", "emotion", False),
        ("最近一个月，我会因为考试结果和家人争执。", "family_support", False),
        ("最近一个月，我能接受短期内不完美的表现。", "emotion", True),
        ("最近一个月，我经常担心未来升学压力。", "academic_pressure", False),
        ("最近一个月，我能找到让自己恢复状态的方法。", "emotion", True),
        ("最近一个月，我觉得学习已经影响了我的生活乐趣。", "academic_pressure", False),
        ("最近一个月，我能感到周围人对我的支持。", "family_support", True),
        ("最近一个月，我在考试中会因为紧张而发挥失常。", "academic_pressure", False),
        ("最近一个月，我能在学习忙碌时保持基本节奏。", "sleep", True),
    ]
    return [_question(f"academic_ref_{idx}", prompt, dimension, options=LIKERT_5, reverse=reverse, risk_tag="academic_pressure") for idx, (prompt, dimension, reverse) in enumerate(prompts, start=1)]


def _interpersonal_questions() -> list[dict]:
    prompts = [
        ("最近一个月，我在班里有愿意一起合作学习的同学。", "interpersonal", True),
        ("最近一个月，我常担心自己被别人误解。", "interpersonal", False),
        ("最近一个月，我能主动和新同学打招呼。", "interpersonal", True),
        ("最近一个月，我觉得自己在班级里没有存在感。", "interpersonal", False),
        ("最近一个月，我和同学发生冲突后能尝试沟通。", "interpersonal", True),
        ("最近一个月，我会因为怕被拒绝而不敢表达需要。", "interpersonal", False),
        ("最近一个月，我在班级活动中有参与感。", "campus_safety", True),
        ("最近一个月，我觉得自己和大家格格不入。", "campus_safety", False),
        ("最近一个月，我愿意在困难时请朋友帮忙。", "interpersonal", True),
        ("最近一个月，我会把很多误会都憋在心里。", "interpersonal", False),
        ("最近一个月，我能觉察并尊重别人感受。", "interpersonal", True),
        ("最近一个月，我常因为同伴关系心烦。", "emotion", False),
        ("最近一个月，我觉得班级里有人支持我。", "campus_safety", True),
        ("最近一个月，我会因为同伴评价而否定自己。", "emotion", False),
        ("最近一个月，我愿意加入集体讨论或合作。", "interpersonal", True),
        ("最近一个月，我觉得自己被小圈子排斥。", "campus_safety", False),
        ("最近一个月，我能向老师说明自己在人际上的困扰。", "interpersonal", True),
        ("最近一个月，我常担心别人不喜欢我。", "emotion", False),
        ("最近一个月，我觉得自己在班里有归属感。", "campus_safety", True),
        ("最近一个月，我会因为担心社交而回避活动。", "interpersonal", False),
    ]
    return [_question(f"interpersonal_ref_{idx}", prompt, dimension, options=LIKERT_5, reverse=reverse, risk_tag="interpersonal") for idx, (prompt, dimension, reverse) in enumerate(prompts, start=1)]


def _family_questions() -> list[dict]:
    prompts = [
        ("最近一个月，我能和家人好好谈自己的感受。", "family_support", True),
        ("最近一个月，家里经常因为学习或手机问题争吵。", "family_support", False),
        ("最近一个月，我觉得家人理解我的难处。", "family_support", True),
        ("最近一个月，我在家里常被否定或打断。", "family_support", False),
        ("最近一个月，遇到困难时我愿意先想到家人。", "family_support", True),
        ("最近一个月，我会刻意回避和家人交流。", "family_support", False),
        ("最近一个月，我能感到家人对我的陪伴。", "family_support", True),
        ("最近一个月，家庭气氛让我感到压抑。", "emotion", False),
        ("最近一个月，我知道家里哪些成年人可以帮助我。", "family_support", True),
        ("最近一个月，我担心把真实想法告诉家人后被批评。", "family_support", False),
        ("最近一个月，家人会认真听我说完事情。", "family_support", True),
        ("最近一个月，我常觉得家里没人站在我这边。", "emotion", False),
        ("最近一个月，我能和家人商量学习安排。", "academic_pressure", True),
        ("最近一个月，家庭冲突影响了我的睡眠或食欲。", "sleep", False),
        ("最近一个月，我能从家里获得实际帮助。", "family_support", True),
        ("最近一个月，我会因为家庭氛围而不想回家。", "family_support", False),
        ("最近一个月，我和家人有稳定的正向互动时间。", "family_support", True),
        ("最近一个月，我觉得家里的要求让我一直紧绷。", "emotion", False),
        ("最近一个月，我相信遇到严重问题时家人会支持我。", "family_support", True),
        ("最近一个月，我会因为家庭原因对学校生活失去动力。", "academic_pressure", False),
    ]
    return [_question(f"family_ref_{idx}", prompt, dimension, options=LIKERT_5, reverse=reverse, risk_tag="family_support") for idx, (prompt, dimension, reverse) in enumerate(prompts, start=1)]


def _safety_questions() -> list[dict]:
    prompts = [
        ("我知道在校园里遇到危险时应该先向谁求助。", "campus_safety", True),
        ("我能够识别网络上常见的诱导或诈骗风险。", "self_safety", True),
        ("我遇到陌生人搭讪时知道怎样保护自己。", "self_safety", True),
        ("我会为了图方便泄露自己的账号或验证码。", "self_safety", False),
        ("我知道身体边界被侵犯时该如何拒绝并求助。", "self_safety", True),
        ("我会因为好奇参与明显危险的挑战。", "self_safety", False),
        ("我知道放学后独自回家时需要注意什么。", "campus_safety", True),
        ("我会在网络上发布让自己以后后悔的内容。", "self_safety", False),
        ("我知道学校里负责安全支持的老师或地点。", "campus_safety", True),
        ("我觉得遭遇风险时求助会很丢脸。", "emotion", False),
        ("我能识别朋友怂恿我做危险事情时的风险。", "self_safety", True),
        ("我会为了融入同伴而勉强自己做不舒服的事。", "interpersonal", False),
        ("我知道遇到网络霸凌可以保留证据并求助。", "self_safety", True),
        ("我会把定位、行程等隐私随意发给不熟的人。", "self_safety", False),
        ("我清楚紧急情况下可以拨打或联系哪些资源。", "self_safety", True),
        ("我会在不确认真实性的情况下转发危险信息。", "self_safety", False),
        ("我知道在公共场所与陌生人接触时要保持边界。", "self_safety", True),
        ("我会因为怕麻烦而忽视身边的安全隐患。", "campus_safety", False),
        ("我愿意在自己或同学遇险时及时告诉老师。", "campus_safety", True),
        ("我觉得冒险行为能够证明自己更勇敢。", "self_safety", False),
    ]
    questions = []
    for idx, (prompt, dimension, reverse) in enumerate(prompts, start=1):
        risk_indexes = [3, 4] if not reverse and dimension in {"self_safety", "campus_safety"} else []
        questions.append(_question(f"safety_ref_{idx}", prompt, dimension, options=_options_with_risk(LIKERT_5, risk_indexes), reverse=reverse, risk_tag="self_safety" if dimension == "self_safety" else "campus_safety"))
    return questions


# ==================== 标准化量表题目生成器 ====================

# 5点评分：1=没有, 2=很轻, 3=中等, 4=偏重, 5=严重
SCL90_SCALE = [
    {"content": "没有", "score": 0},
    {"content": "很轻", "score": 1},
    {"content": "中等", "score": 2},
    {"content": "偏重", "score": 3},
    {"content": "严重", "score": 4},
]


def _scl90_questions() -> list[dict]:
    # SCL-90 各维度题目：躯体化(12), 强迫(10), 人际敏感(9), 抑郁(13), 焦虑(10), 敌对(6), 恐怖(7), 偏执(6), 精神病性(10), 附加(7)=90
    items = [
        # 躯体化 (12)
        ("scl_s1", "头痛", "somatization"), ("scl_s2", "感到身体某处发麻或刺痛", "somatization"),
        ("scl_s3", "头晕或晕倒", "somatization"), ("scl_s4", "心脏跳动很厉害", "somatization"),
        ("scl_s5", "恶心或胃部不舒服", "somatization"), ("scl_s6", "手脚发抖", "somatization"),
        ("scl_s7", "呼吸有困难", "somatization"), ("scl_s8", "身体某处一阵阵发热或发冷", "somatization"),
        ("scl_s9", "身体某部分感觉疼痛", "somatization"), ("scl_s10", "感到手脚沉重", "somatization"),
        ("scl_s11", "很难清楚地思考问题", "somatization"), ("scl_s12", "感到身体虚弱或疲惫", "somatization"),
        # 强迫 (10)
        ("scl_o1", "忘记性大", "obsessive"), ("scl_o2", "担心自己的整洁和条理", "obsessive"),
        ("scl_o3", "做事必须做得很慢以确保正确", "obsessive"), ("scl_o4", "做事必须反复检查", "obsessive"),
        ("scl_o5", "难以做出决定", "obsessive"), ("scl_o6", "脑子里总想着某些事情", "obsessive"),
        ("scl_o7", "很难集中注意力", "obsessive"), ("scl_o8", "必须重复某些动作（如洗手、整理）", "obsessive"),
        ("scl_o9", "对做过的事总是不放心", "obsessive"), ("scl_o10", "感到难以完成任务", "obsessive"),
        # 人际敏感 (9)
        ("scl_i1", "对别人不信任", "interpersonal_sensitivity"), ("scl_i2", "容易感到被别人误解", "interpersonal_sensitivity"),
        ("scl_i3", "担心别人对自己有看法", "interpersonal_sensitivity"), ("scl_i4", "感到比不上别人", "interpersonal_sensitivity"),
        ("scl_i5", "当别人看着自己或谈论自己时感到不自在", "interpersonal_sensitivity"),
        ("scl_i6", "感到在公共场合吃东西很不舒服", "interpersonal_sensitivity"),
        ("scl_i7", "在人际交往中感到害羞和不自在", "interpersonal_sensitivity"),
        ("scl_i8", "觉得自己在人群中不受重视", "interpersonal_sensitivity"),
        ("scl_i9", "容易因别人的批评而受伤", "interpersonal_sensitivity"),
        # 抑郁 (13)
        ("scl_d1", "对事物不感兴趣", "depression"), ("scl_d2", "感到闷闷不乐", "depression"),
        ("scl_d3", "容易哭泣", "depression"), ("scl_d4", "对异性的兴趣减退", "depression"),
        ("scl_d5", "感到自己没有价值", "depression"), ("scl_d6", "感到前途没有希望", "depression"),
        ("scl_d7", "感到做什么都没有意思", "depression"), ("scl_d8", "觉得生活没有意义", "depression"),
        ("scl_d9", "食欲变差", "depression"), ("scl_d10", "睡眠不好", "depression"),
        ("scl_d11", "经常责备自己", "depression"), ("scl_d12", "感到孤独", "depression"),
        ("scl_d13", "感到坐立不安、心神不定", "depression"),
        # 焦虑 (10)
        ("scl_a1", "容易紧张", "anxiety"), ("scl_a2", "容易感到害怕", "anxiety"),
        ("scl_a3", "心里觉得不安或烦躁", "anxiety"), ("scl_a4", "突然感到恐慌", "anxiety"),
        ("scl_a5", "感到紧张或被拉紧", "anxiety"), ("scl_a6", "感到无法静坐", "anxiety"),
        ("scl_a7", "感到心跳加速或加强", "anxiety"), ("scl_a8", "容易受到惊吓", "anxiety"),
        ("scl_a9", "感到手心出汗或发黏", "anxiety"), ("scl_a10", "因为害怕而回避某些事情或场合", "anxiety"),
        # 敌对 (6)
        ("scl_h1", "容易烦恼和激动", "hostility"), ("scl_h2", "自己不能控制地大发脾气", "hostility"),
        ("scl_h3", "有想打人或伤害别人的冲动", "hostility"), ("scl_h4", "常常与人争论", "hostility"),
        ("scl_h5", "别人认为我应该为错误受到惩罚", "hostility"), ("scl_h6", "大叫或摔东西", "hostility"),
        # 恐怖 (7)
        ("scl_p1", "害怕空旷的场所或街道", "phobic"), ("scl_p2", "害怕独自出门", "phobic"),
        ("scl_p3", "害怕乘公共汽车、地铁或火车", "phobic"), ("scl_p4", "因为害怕而回避某些事情或场合", "phobic"),
        ("scl_p5", "害怕在人群多的地方", "phobic"), ("scl_p6", "在社交场合感到不舒服", "phobic"),
        ("scl_p7", "害怕黑暗", "phobic"),
        # 偏执 (6)
        ("scl_pa1", "觉得有人在监视或谈论自己", "paranoid"), ("scl_pa2", "觉得别人想占自己的便宜", "paranoid"),
        ("scl_pa3", "认为大多数人不可信任", "paranoid"), ("scl_pa4", "感到有人跟踪或监视自己", "paranoid"),
        ("scl_pa5", "感到在公共场合吃东西很不舒服", "paranoid"), ("scl_pa6", "觉得别人不理解自己", "paranoid"),
        # 思维与感知 (10)
        ("scl_ps1", "有时候会觉得自己听到一些别人没注意到的声音", "psychoticism"), ("scl_ps2", "有时候会担心别人能猜到自己在想什么", "psychoticism"),
        ("scl_ps3", "有时候会觉得自己被别人影响太大", "psychoticism"), ("scl_ps4", "有时候会有一些和别人不一样的想法", "psychoticism"),
        ("scl_ps5", "有时候会感到脑子一片空白", "psychoticism"), ("scl_ps6", "有时候会觉得自己身体感觉和平时不太一样", "psychoticism"),
        ("scl_ps7", "有时候会觉得自己做了不太合适的事", "psychoticism"), ("scl_ps8", "有时候会感到孤独，即使身边有人", "psychoticism"),
        ("scl_ps9", "独处时会特别注意周围的声音", "psychoticism"), ("scl_ps10", "有时候会觉得自己的想法不太受自己控制", "psychoticism"),
        # 附加 (7)
        ("scl_ex1", "感到身体某部位有不明原因的疼痛", "somatization"), ("scl_ex2", "觉得自己很孤独", "depression"),
        ("scl_ex3", "感到精力下降", "depression"), ("scl_ex4", "感到做事效率很低", "obsessive"),
        ("scl_ex5", "觉得未来很渺茫", "depression"), ("scl_ex6", "食欲发生变化", "depression"),
        ("scl_ex7", "感到不能控制自己的情绪", "anxiety"),
    ]
    questions = []
    for code, title, dim in items:
        risk_tag = ""
        if dim in ("depression", "anxiety"):
            risk_tag = "emotion"
        elif dim == "self_safety":
            risk_tag = "self_safety"
        questions.append(_question(code, f"最近一周，{title}的程度：", dim, options=_clone_options(SCL90_SCALE), risk_tag=risk_tag))
    # 插入2道注意力检测题
    questions.insert(12, _question("scl_att1", "本题为注意力检测题，请选择「中等」。", "somatization",
                                    options=_clone_options(SCL90_SCALE), attention=True, attention_answer="中等"))
    questions.insert(45, _question("scl_att2", "本题为注意力检测题，请选择「很轻」。", "depression",
                                    options=_clone_options(SCL90_SCALE), attention=True, attention_answer="很轻"))
    return questions


def _mssmhs_questions() -> list[dict]:
    # MSSMHS: 10维度，每个6题 = 60题
    dims = [
        ("force", "强迫", [
            "做事必须反复检查才能放心", "总觉得手没洗干净", "必须按固定顺序做事否则不安",
            "反复想同一件事停不下来", "出门后总怀疑门没锁好", "看到东西不整齐就很不舒服",
        ]),
        ("paranoid", "偏执", [
            "觉得有人在背后议论自己", "觉得别人故意针对自己", "觉得大多数人不可信任",
            "认为别人不理解自己", "总觉得别人对自己不公平", "怀疑别人想占自己便宜",
        ]),
        ("hostility", "敌对", [
            "容易发脾气", "不能控制地大声叫喊", "想摔东西或打人",
            "常常与人争论", "觉得周围的人很烦", "容易与人发生冲突",
        ]),
        ("interpersonal_sensitivity", "人际敏感", [
            "觉得在人群中不自在", "在社交场合感到紧张", "害怕与人交往",
            "觉得别人在注意自己", "感到自卑", "觉得别人不喜欢自己",
        ]),
        ("depression", "抑郁", [
            "感到闷闷不乐", "对什么都不感兴趣", "觉得生活没意思",
            "经常想哭", "觉得没有希望", "感到孤独",
        ]),
        ("anxiety", "焦虑", [
            "感到紧张或不安", "容易感到害怕", "心里烦躁不安",
            "突然感到恐慌", "感到手心出汗", "因为担心而睡不好",
        ]),
        ("learning_pressure", "学习压力", [
            "觉得学习压力太大", "考试时非常紧张", "担心成绩不好",
            "觉得学习跟不上", "害怕回答老师的问题", "担心升学或考试",
        ]),
        ("adaptation", "适应不良", [
            "对新环境很难适应", "觉得在学校很不自在", "不习惯学校的规则",
            "觉得和同学相处很困难", "很难融入班级", "觉得学校的节奏太快",
        ]),
        ("emotional_instability", "情绪不稳定", [
            "情绪起伏很大", "一会儿高兴一会儿难过", "很容易因为小事生气",
            "经常感到心情不好", "很难控制自己的情绪", "会突然感到沮丧",
        ]),
        ("psychological_imbalance", "心理失衡", [
            "觉得自己什么都不如别人", "觉得命运对自己不公平", "看到别人比自己好就不舒服",
            "觉得自己什么都不行", "觉得别人总是运气比自己好", "感到很委屈",
        ]),
    ]
    questions = []
    for dim_code, dim_name, prompts in dims:
        for i, prompt in enumerate(prompts, start=1):
            questions.append(_question(f"mss_{dim_code[:3]}_{i}", f"最近一个月，{prompt}。", dim_code, options=_clone_options(LIKERT_5)))
    return questions


def _dass21_questions() -> list[dict]:
    # DASS-21: 抑郁(3,5,10,13,16,17,21), 焦虑(2,4,7,9,15,19,20), 压力(1,6,8,11,12,14,18)
    items = [
        ("dass_s1", "我发现很难让自己平静下来", "stress"),
        ("dass_a1", "我感到口腔干燥", "anxiety"),
        ("dass_d1", "我好像体验不到任何积极的感觉", "depression"),
        ("dass_a2", "我感到呼吸有困难（不是因为体力活动）", "anxiety"),
        ("dass_d2", "我发现自己很难主动去做事情", "depression"),
        ("dass_s2", "我对各种事情容易做出过度反应", "stress"),
        ("dass_a3", "我感到发抖（例如手部）", "anxiety"),
        ("dass_s3", "我觉得自己消耗了很多精力", "stress"),
        ("dass_a4", "我担心可能会让自己恐慌或出丑", "anxiety"),
        ("dass_d3", "我觉得自己对未来没有什么可期待的", "depression"),
        ("dass_s4", "我发现自己很难放松", "stress"),
        ("dass_s5", "我感到烦躁不安", "stress"),
        ("dass_d4", "我感到非常沮丧和低落", "depression"),
        ("dass_s6", "我觉得自己无法忍受事情无法按计划进行", "stress"),
        ("dass_a5", "我感到快要恐慌了", "anxiety"),
        ("dass_d5", "我觉得自己毫无价值", "depression"),
        ("dass_d6", "我觉得生活没有什么意义", "depression"),
        ("dass_s7", "我觉得自己容易激动", "stress"),
        ("dass_a6", "我害怕在没有明显原因的情况下感到恐慌", "anxiety"),
        ("dass_a7", "我经历了很多害怕的感觉", "anxiety"),
        ("dass_d7", "我觉得自己生命没有意义", "depression"),
    ]
    questions = []
    for code, title, dim in items:
        risk_tag = "emotion" if dim in ("depression", "anxiety") else ""
        questions.append(_question(code, f"最近一周，{title}的情况：", dim, options=_clone_options(FREQ_4), risk_tag=risk_tag))
    return questions


def _ciasr_questions() -> list[dict]:
    # CIAS-R: 强迫性使用(5), 戒断(5), 耐耐性(3), 人际健康(3), 时间管理(3) = 19
    dims = [
        ("compulsive_use", "强迫性使用", [
            "我发现自己上网的时间比计划的长", "我会不自觉地打开手机上网",
            "即使不想上网也会不由自主地使用", "我尝试减少上网时间但做不到",
            "我总是想着上网的事情",
        ]),
        ("withdrawal", "戒断反应", [
            "如果不能上网我会感到不安", "不上网时我会觉得少了什么",
            "不能上网时我会感到烦躁", "不上网时我会情绪低落",
            "断网时我很难集中注意力做其他事",
        ]),
        ("tolerance", "耐受性", [
            "我需要花更多时间上网才能感到满足", "我发现需要越来越多地上网才能感到满意",
            "比起以前，我现在需要更频繁地上网",
        ]),
        ("interpersonal_health", "人际与健康", [
            "上网影响了我和家人朋友的交流", "因为上网我的身体健康受到了影响（如眼睛、颈椎）",
            "上网让我的学业成绩受到了影响",
        ]),
        ("time_management", "时间管理", [
            "我经常因为上网而睡得很晚", "上网占用了我的学习时间",
            "我经常因为上网而错过或迟到其他活动",
        ]),
    ]
    questions = []
    for dim_code, dim_name, prompts in dims:
        for i, prompt in enumerate(prompts, start=1):
            questions.append(_question(f"cias_{dim_code[:4]}_{i}", f"最近一个月，{prompt}。", dim_code, options=_clone_options(AGREE_4)))
    return questions


def _psqi_questions() -> list[dict]:
    # PSQI 适应版：19题覆盖6个成分
    questions = [
        # 睡眠质量 (4)
        _question("psqi_q1", "最近一个月，我的整体睡眠质量如何？", "sleep_quality",
                  options=[{"content": "很好", "score": 0}, {"content": "较好", "score": 1}, {"content": "较差", "score": 2}, {"content": "很差", "score": 3}]),
        _question("psqi_q2", "最近一个月，我是否因各种原因而难以入睡？", "sleep_quality",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q3", "最近一个月，我夜间是否容易醒来或早醒？", "sleep_quality",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q4", "最近一个月，我是否需要起床上厕所？", "sleep_quality",
                  options=_clone_options(SLEEP_4)),
        # 入睡时间 (3)
        _question("psqi_q5", "最近一个月，我通常需要多久才能入睡？", "sleep_latency",
                  options=[{"content": "15分钟以内", "score": 0}, {"content": "16-30分钟", "score": 1}, {"content": "31-60分钟", "score": 2}, {"content": "超过60分钟", "score": 3}]),
        _question("psqi_q6", "最近一个月，我是否感觉呼吸困难或咳嗽影响入睡？", "sleep_latency",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q7", "最近一个月，我是否感到太冷或太热影响睡眠？", "sleep_latency",
                  options=_clone_options(SLEEP_4)),
        # 睡眠时长 (2)
        _question("psqi_q8", "最近一个月，我每天实际睡眠时间大约是？", "sleep_duration",
                  options=[{"content": "超过7小时", "score": 0}, {"content": "6-7小时", "score": 1}, {"content": "5-6小时", "score": 2}, {"content": "少于5小时", "score": 3}]),
        _question("psqi_q9", "最近一个月，我觉得睡眠时间够不够？", "sleep_duration",
                  options=[{"content": "足够", "score": 0}, {"content": "稍微不够", "score": 1}, {"content": "明显不够", "score": 2}, {"content": "严重不足", "score": 3}]),
        # 睡眠效率 (3)
        _question("psqi_q10", "最近一个月，我是否做噩梦影响睡眠？", "sleep_efficiency",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q11", "最近一个月，我是否因为头疼或身体不适而影响睡眠？", "sleep_efficiency",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q12", "最近一个月，我躺在床上但睡不着的时间多吗？", "sleep_efficiency",
                  options=_clone_options(SLEEP_4)),
        # 睡眠障碍 (4)
        _question("psqi_q13", "最近一个月，我是否使用药物或其他方法帮助睡眠？", "sleep_disturbance",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q14", "最近一个月，我白天是否感到困倦？", "sleep_disturbance",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q15", "最近一个月，我做事情时是否感到精力不足？", "sleep_disturbance",
                  options=_clone_options(SLEEP_4)),
        _question("psqi_q16", "最近一个月，我是否因为打鼾或呼吸问题而影响睡眠？", "sleep_disturbance",
                  options=_clone_options(SLEEP_4)),
        # 日间功能障碍 (3)
        _question("psqi_q17", "最近一个月，我在上课时是否容易犯困？", "daytime_dysfunction",
                  options=[{"content": "从不", "score": 0}, {"content": "偶尔", "score": 1}, {"content": "经常", "score": 2}, {"content": "总是", "score": 3}]),
        _question("psqi_q18", "最近一个月，我是否因为睡眠问题影响了学习效率？", "daytime_dysfunction",
                  options=[{"content": "没有", "score": 0}, {"content": "有一点", "score": 1}, {"content": "比较明显", "score": 2}, {"content": "非常明显", "score": 3}]),
        _question("psqi_q19", "最近一个月，我对整体睡眠质量满意吗？", "daytime_dysfunction",
                  options=[{"content": "很满意", "score": 0}, {"content": "基本满意", "score": 1}, {"content": "不太满意", "score": 2}, {"content": "很不满意", "score": 3}], reverse=True),
    ]
    return questions


def _bullying_extended_questions() -> list[dict]:
    # 6维度各5题 = 30题
    dims = [
        ("victimization", "受欺凌", [
            "最近一个月，我被人取笑或嘲笑", "最近一个月，有人故意把我排斥在活动之外",
            "最近一个月，有人推搡、打我或抢我的东西", "最近一个月，有人散布关于我的谣言",
            "最近一个月，有人用恶意的言语攻击我",
        ]),
        ("aggression", "攻击行为", [
            "最近一个月，我取笑或嘲笑过其他同学", "最近一个月，我故意把某同学排斥在活动之外",
            "最近一个月，我推搡或打过其他同学", "最近一个月，我说过其他同学的坏话",
            "最近一个月，我故意破坏过其他同学的东西",
        ]),
        ("bystander", "旁观行为", [
            "看到有人被欺负时，我会尝试帮助被欺负的人", "看到有人被欺负时，我会告诉老师或其他大人",
            "看到有人被欺负时，我会假装没看到", "看到有人被欺负时，我会走开不管",
            "看到有人被欺负时，我会觉得被欺负的人可能做错了什么",
        ]),
        ("cyberbullying", "网络欺凌", [
            "最近一个月，有人在网络上发布让我不舒服的内容", "最近一个月，有人在网络上冒充我或盗用我的账号",
            "最近一个月，有人在网上排挤或孤立我", "最近一个月，我在网上看到同学被别人攻击",
            "最近一个月，我在网上说了让其他同学不舒服的话",
        ]),
        ("help_seeking", "求助行为", [
            "如果被欺负，我愿意告诉家长", "如果被欺负，我愿意告诉老师",
            "如果被欺负，我愿意告诉好朋友", "我觉得被欺负后告诉大人没有用",
            "我觉得被欺负是因为自己不够好",
        ]),
        ("safety", "安全感", [
            "我在学校里感到安全", "我在放学路上感到安全",
            "我害怕去学校的某些地方", "我因为害怕被欺负而不想去学校",
            "我觉得学校能保护我不被欺负",
        ]),
    ]
    questions = []
    for dim_code, dim_name, prompts in dims:
        for i, prompt in enumerate(prompts, start=1):
            reverse = (dim_code in ("bystander", "help_seeking", "safety")) and i <= 3
            risk_tag = "bullying" if dim_code in ("victimization", "cyberbullying") else ""
            questions.append(_question(f"be_{dim_code[:4]}_{i}", prompt, dim_code, options=_clone_options(FREQUENCY_5), reverse=reverse, risk_tag=risk_tag))
    return questions


def _family_embuf_questions() -> list[dict]:
    # s-EMBU 适应版：拒绝(8), 情感温暖(8), 过度保护(7) = 23
    questions = []
    reject_items = [
        "我觉得父母对我很严厉", "我觉得父母经常批评我", "我觉得父母很少表扬我",
        "我觉得父母对我太苛刻", "我觉得父母经常对我发脾气", "我觉得父母总是对我不满意",
        "我觉得父母会用冷暴力的方式对待我", "我觉得父母很少关心我的感受",
    ]
    warmth_items = [
        "我觉得父母理解我的想法和感受", "我觉得父母经常鼓励我", "我觉得父母尊重我的选择",
        "我觉得父母愿意花时间和我在一起", "我觉得父母在我遇到困难时会帮助我",
        "我觉得父母会用温暖的方式表达对我的爱", "我觉得父母以我为骄傲",
        "我觉得父母能在我需要时给予支持",
    ]
    over_items = [
        "我觉得父母对我过度保护", "我觉得父母干涉我太多", "我觉得父母替我做太多决定",
        "我觉得父母不放心我一个人做事", "我觉得父母管得太细", "我觉得父母不允许我犯错",
        "我觉得父母对我期望过高",
    ]
    for i, prompt in enumerate(reject_items, start=1):
        questions.append(_question(f"fam_rej_{i}", f"最近半年，{prompt}。", "rejection", options=_clone_options(LIKERT_5), risk_tag="family_support"))
    for i, prompt in enumerate(warmth_items, start=1):
        questions.append(_question(f"fam_warm_{i}", f"最近半年，{prompt}。", "emotional_warmth", options=_clone_options(LIKERT_5), reverse=True))
    for i, prompt in enumerate(over_items, start=1):
        questions.append(_question(f"fam_over_{i}", f"最近半年，{prompt}。", "overprotection", options=_clone_options(LIKERT_5)))
    return questions


def _selfharm_risk_questions() -> list[dict]:
    # 压力感受(6), 积极心态(6), 睡眠(4), 掩饰(4), 自我关爱(6) = 26
    questions = []
    # 压力感受
    hopelessness = [
        "我有时会觉得压力大到不知道怎么办", "我觉得最近事情总是不太顺利",
        "我很难相信好的事情会发生在自己身上", "我觉得努力了也不一定有结果",
        "我有时会感到很无助", "我觉得最近的生活让我喘不过气",
    ]
    for i, prompt in enumerate(hopelessness, start=1):
        questions.append(_question(f"sh_hope_{i}", f"最近一个月，{prompt}。", "hopelessness", options=_clone_options(LIKERT_5), risk_tag="self_safety"))

    # 积极心态 (reverse)
    optimism = [
        "我对未来充满期待", "我相信自己能克服困难", "我觉得生活中有很多值得期待的事情",
        "我能够看到事情积极的一面", "我相信明天会更好", "我对自己的生活感到满意",
    ]
    for i, prompt in enumerate(optimism, start=1):
        questions.append(_question(f"sh_opt_{i}", f"最近一个月，{prompt}。", "optimism", options=_clone_options(LIKERT_5), reverse=True))

    # 睡眠
    sleep = [
        "最近一个月，我经常失眠", "最近一个月，我总是做噩梦",
        "最近一个月，我很难入睡", "最近一个月，我的睡眠质量很差",
    ]
    for i, prompt in enumerate(sleep, start=1):
        questions.append(_question(f"sh_sleep_{i}", prompt, "sleep", options=_clone_options(LIKERT_5)))

    # 掩饰
    conceal = [
        "遇到不开心的事情我会假装没事", "我不愿意让别人看到我的真实感受",
        "我会刻意隐藏自己的负面情绪", "我认为向别人倾诉没有用",
    ]
    for i, prompt in enumerate(conceal, start=1):
        questions.append(_question(f"sh_conc_{i}", f"最近一个月，{prompt}。", "concealment", options=_clone_options(LIKERT_5)))

    # 自我关爱 (critical - any high score triggers urgent)
    safety = [
        "最近一个月，我有时会觉得很疲惫、提不起劲", "最近一个月，我有时会觉得心情很低落",
        "最近一个月，我有时会做一些伤害自己健康的事（如熬夜、不吃饭等）",
        "最近一个月，我觉得身边的人不太关心我的感受", "最近一个月，我有时会觉得自己不够好",
        "最近一个月，我有时会觉得没有人理解自己",
    ]
    for i, prompt in enumerate(safety, start=1):
        risk_opts = _clone_options(LIKERT_5)
        for opt in risk_opts[3:]:
            opt["is_risk_option"] = True
        questions.append(_question(f"sh_safe_{i}", prompt, "self_safety", options=risk_opts, risk_tag="self_safety"))

    return questions


JINDUN_BEHAVIOR_SCALE = [
    {"content": "没有", "score": 0},
    {"content": "偶尔", "score": 1},
    {"content": "经常", "score": 2},
    {"content": "总是", "score": 3},
]


def _jindun_behavior_questions() -> list[dict]:
    questions: list[dict] = []

    care_need = [
        ("jindun_cn_1", "家中是否有人经常忽视我的感受和需求。"),
        ("jindun_cn_2", "最近一个月，我经常感到孤独，没有大人可以倾诉。"),
        ("jindun_cn_3", "最近一个月，我的父母或监护人很少过问我的学习或生活。"),
        ("jindun_cn_4", "最近一个月，我经常因为家庭矛盾而感到苦恼。"),
        ("jindun_cn_5", "最近一个月，我觉得自己在学校没有归属感。"),
        ("jindun_cn_6", "最近一个月，我在遇到困难时找不到可以求助的人。"),
        ("jindun_cn_7", "最近一个月，我的家庭经济状况让我感到压力很大。"),
        ("jindun_cn_8", "我经常觉得没有人真正关心我的感受。"),
    ]
    for code, title in care_need:
        questions.append(_question(code, title, "care_need", options=_clone_options(JINDUN_BEHAVIOR_SCALE), risk_tag="family_support"))

    bad_behavior = [
        ("jindun_bb_1", "最近一个月，我曾经对同学撒谎或隐瞒事情。"),
        ("jindun_bb_2", "最近一个月，我有过逃课或迟到的情况。"),
        ("jindun_bb_3", "最近一个月，我曾经欺负或嘲笑其他同学。"),
        ("jindun_bb_4", "最近一个月，我经常违反学校纪律或规定。"),
        ("jindun_bb_5", "最近一个月，我有过偷拿别人东西的行为。"),
        ("jindun_bb_6", "最近一个月，我参与过打架或冲突。"),
        ("jindun_bb_7", "最近一个月，我经常沉迷于网络游戏或短视频到深夜。"),
        ("jindun_bb_8", "最近一个月，我曾经在考试中作弊。"),
    ]
    for code, title in bad_behavior:
        questions.append(_question(code, title, "bad_behavior", options=_clone_options(JINDUN_BEHAVIOR_SCALE), risk_tag="campus_safety"))

    serious_bad = [
        ("jindun_sb_1", "最近半年，我曾经离家出走或在外过夜。"),
        ("jindun_sb_2", "最近半年，我有过参与赌博或类似游戏的情况。"),
        ("jindun_sb_3", "最近半年，我曾经接触或尝试过烟草、酒精等不适合学生使用的东西。"),
        ("jindun_sb_4", "最近半年，我曾经故意损坏他人或公共财物。"),
        ("jindun_sb_5", "最近半年，我多次参与校园或社区内的群体冲突。"),
        ("jindun_sb_6", "最近半年，我曾经长时间不去上学（连续一周以上）。"),
        ("jindun_sb_7", "最近半年，我有过被人利用去做不合适的事情的经历。"),
        ("jindun_sb_8", "我曾经携带不适合带到学校的物品。"),
    ]
    for code, title in serious_bad:
        questions.append(_question(code, title, "serious_bad_behavior", options=_clone_options(JINDUN_BEHAVIOR_SCALE), risk_tag="campus_safety"))

    criminal = [
        ("jindun_ci_1", "我曾经有过拿别人东西没还的经历。"),
        ("jindun_ci_2", "我曾经和同学发生过肢体冲突导致受伤。"),
        ("jindun_ci_3", "我曾经因为做错事被严厉批评或处分过。"),
        ("jindun_ci_4", "我曾经参与过强迫他人做不愿意做的事情。"),
        ("jindun_ci_5", "我曾经接触过不该接触的东西。"),
        ("jindun_ci_6", "我曾经参与过欺骗他人的行为。"),
    ]
    for code, title in criminal:
        questions.append(_question(code, title, "criminal_indicator", options=_clone_options(JINDUN_BEHAVIOR_SCALE), risk_tag="self_safety"))

    return questions


def _jindun_family_questions() -> list[dict]:
    questions: list[dict] = []

    guardianship = [
        ("jindun_fg_1", "我的父母或监护人了解我每天在哪里、和谁在一起。"),
        ("jindun_fg_2", "我的父母或监护人经常检查我的作业或学习情况。"),
        ("jindun_fg_3", "家里有人能及时发现我情绪不好或遇到困难。"),
        ("jindun_fg_4", "我的父母或监护人对我的行踪和交友情况有基本了解。"),
        ("jindun_fg_5", "当我晚上不回家时，家人会主动联系我。"),
    ]
    for code, title in guardianship:
        questions.append(_question(code, title, "family_guardianship", options=_clone_options(JINDUN_BEHAVIOR_SCALE), reverse=True, risk_tag="family_support"))

    environment = [
        ("jindun_fe_1", "家里经常有人大声争吵或发生冲突。"),
        ("jindun_fe_2", "我觉得家里的氛围让我感到紧张或不安。"),
        ("jindun_fe_3", "家里有人经常饮酒或使用影响行为的物质。"),
        ("jindun_fe_4", "家里的经济状况经常让我感到担忧。"),
        ("jindun_fe_5", "家里有人对我进行过身体上的惩罚或伤害。"),
    ]
    for code, title in environment:
        questions.append(_question(code, title, "family_environment", options=_clone_options(JINDUN_BEHAVIOR_SCALE), risk_tag="family_support"))

    support = [
        ("jindun_fs_1", "当我遇到困难时，我觉得家人会支持我。"),
        ("jindun_fs_2", "我能和家人坦诚地交流自己的想法和感受。"),
        ("jindun_fs_3", "家人经常鼓励我、肯定我的努力。"),
        ("jindun_fs_4", "我觉得家人理解我的困难和压力。"),
        ("jindun_fs_5", "家人愿意花时间陪伴我、参与我的生活。"),
    ]
    for code, title in support:
        questions.append(_question(code, title, "emotional_support", options=_clone_options(JINDUN_BEHAVIOR_SCALE), reverse=True, risk_tag="family_support"))

    return questions


# ---------------------------------------------------------------------------
# 金盾护苗专用问卷 (6 套)
# ---------------------------------------------------------------------------

JINDUN_GRADES = "四年级,五年级,六年级,初一,初二,初三,高一,高二,高三"


def _jindun_selfcognition_questions() -> list[dict]:
    """青少年自我认知与心理特质调研 — 26 题"""
    return [
        _question("antisocial_1", "你认为自己在面对冲突时，最本质的反应是？", "antisocial",
            options=[{"content": "尝试协商", "score": 1}, {"content": "感到不耐烦", "score": 2}, {"content": "想要压倒对方", "score": 3}, {"content": "极度愤怒并想毁灭对方", "score": 4}],
            risk_tag="self_safety"),
        _question("empathy_1", "当你意识到自己做了一件伤害他人的事，你的心情是？", "empathy",
            options=[{"content": "非常愧疚", "score": 1}, {"content": "觉得无所谓", "score": 2}, {"content": "反而觉得有一种掌控感", "score": 3}, {"content": "觉得对方活该", "score": 4}],
            risk_tag="self_safety"),
        _question("egocentrism_1", "你是否觉得这个世界非常虚伪，只有自己才是清醒的？", "egocentrism",
            options=[{"content": "不认同", "score": 1}, {"content": "有时会这样想", "score": 2}, {"content": "大部分时候如此", "score": 3}, {"content": "绝对如此", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_2", "你是否觉得规矩是用来约束弱者的，强者应当打破规矩？", "antisocial",
            options=[{"content": "不同意", "score": 1}, {"content": "有时这么想", "score": 2}, {"content": "基本认同", "score": 3}, {"content": "完全同意", "score": 4}],
            risk_tag="self_safety"),
        _question("manipulation_1", "在追求目标的过程中，你是否认为采取一些不正当手段是必要的？", "manipulation",
            options=[{"content": "绝不采取", "score": 1}, {"content": "偶尔尝试边缘手段", "score": 2}, {"content": "手段不重要，结果才重要", "score": 3}, {"content": "只要能成，什么代价都可以付", "score": 4}],
            risk_tag="self_safety"),
        _question("egocentrism_2", "你是否感到自己比周围的大部分人更有权利获得更好的待遇？", "egocentrism",
            options=[{"content": "不觉得", "score": 1}, {"content": "有点", "score": 2}, {"content": "我本来就该优于他人", "score": 3}, {"content": "我是天选之人", "score": 4}],
            risk_tag="self_safety"),
        _question("empathy_2", "当你看到别人处于极度痛苦中，你的第一反应是？", "empathy",
            options=[{"content": "想要帮助", "score": 1}, {"content": "感到不适", "score": 2}, {"content": "毫无波动", "score": 3}, {"content": "感到一丝兴奋", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("manipulation_2", "你是否有过为了获取利益，而欺骗身边最信任的人的经历？", "manipulation",
            options=[{"content": "从未", "score": 1}, {"content": "小事偶尔", "score": 2}, {"content": "有过", "score": 3}, {"content": "这是生存常态", "score": 4}],
            risk_tag="self_safety"),
        _question("egocentrism_3", "你是否觉得自己比周围的人更聪明，总能轻易看透他们的底牌？", "egocentrism",
            options=[{"content": "不觉得", "score": 1}, {"content": "有时", "score": 2}, {"content": "经常", "score": 3}, {"content": "我总是像上帝一样俯视他们", "score": 4}],
            risk_tag="self_safety"),
        _question("manipulation_3", "面对那些限制你自由的人，你内心的真实冲动是？", "manipulation",
            options=[{"content": "理解并沟通", "score": 1}, {"content": "忍耐", "score": 2}, {"content": "彻底摆脱他们", "score": 3}, {"content": "报复并摧毁他们的权威", "score": 4}],
            risk_tag="self_safety"),
        _question("egocentrism_4", "你认为自己是否拥有某种「别人无法察觉」的阴暗特质", "egocentrism",
            options=[{"content": "没有", "score": 1}, {"content": "可能有", "score": 2}, {"content": "有，且我很享受", "score": 3}, {"content": "那是我最强大的武器", "score": 4}],
            risk_tag="self_safety"),
        _question("manipulation_4", "在群体中，你更希望自己是？", "manipulation",
            options=[{"content": "贡献者", "score": 1}, {"content": "参与者", "score": 2}, {"content": "观察者/引导者", "score": 3}, {"content": "统治者/操控者", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_3", "如果犯错不会被发现，你会考虑做违法的事吗？", "antisocial",
            options=[{"content": "绝不会", "score": 1}, {"content": "可能会考虑", "score": 2}, {"content": "绝对不会做", "score": 3}, {"content": "我每天都在寻找这种机会", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("egocentrism_5", "你是否认为大多数人都很愚蠢，很容易被煽动？", "egocentrism",
            options=[{"content": "不同意", "score": 1}, {"content": "偶尔觉得", "score": 2}, {"content": "基本如此", "score": 3}, {"content": "他们就是为了被我利用而存在的", "score": 4}],
            risk_tag="self_safety"),
        _question("empathy_3", "当你感到被他人冒犯时，报复行为是否会让你感到快感？", "empathy",
            options=[{"content": "不会", "score": 1}, {"content": "偶尔会有", "score": 2}, {"content": "经常感到快感", "score": 3}, {"content": "这是我唯一的动力来源", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_4", "你是否认为「法律」是阻止你实现真正抱负的最大障碍", "antisocial",
            options=[{"content": "不认为", "score": 1}, {"content": "一点点", "score": 2}, {"content": "大部分时间是", "score": 3}, {"content": "它是奴役人类的锁链", "score": 4}],
            risk_tag="self_safety"),
        _question("manipulation_5", "在处理人际关系中，你是否倾向于把别人看作「工具」或「资产」", "manipulation",
            options=[{"content": "视他们为朋友", "score": 1}, {"content": "有时会衡量得失", "score": 2}, {"content": "经常如此", "score": 3}, {"content": "所有人都是我的工具", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_5", "你是否在某些时刻有过极其强烈的破坏冲动？", "antisocial",
            options=[{"content": "从没", "score": 1}, {"content": "很累时偶尔会有", "score": 2}, {"content": "经常有", "score": 3}, {"content": "我必须随时克制这种冲动", "score": 4}],
            risk_tag="self_safety"),
        _question("manipulation_6", "如果让你在「被他人认可」和「拥有掌控他人的力量」中选一个，你选", "manipulation",
            options=[{"content": "被认可", "score": 1}, {"content": "都会选", "score": 2}, {"content": "掌控力", "score": 3}, {"content": "没有掌控力，认可毫无意义", "score": 4}],
            risk_tag="self_safety"),
        _question("empathy_4", "对于那些弱者，你真实的看法是？", "empathy",
            options=[{"content": "同情", "score": 1}, {"content": "无感", "score": 2}, {"content": "他们理应被淘汰", "score": 3}, {"content": "既然弱，就该被我随意支配", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_6", "你是否有过在情绪极度失控时，完全忘记自己在做什么的经历？", "antisocial",
            options=[{"content": "没有", "score": 1}, {"content": "极少", "score": 2}, {"content": "有过", "score": 3}, {"content": "那种失控的感觉让我迷醉", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_7", "如果社会秩序崩溃，你觉得你会成为？", "antisocial",
            options=[{"content": "幸存者", "score": 1}, {"content": "寻找秩序的人", "score": 2}, {"content": "争夺资源的人", "score": 3}, {"content": "制定新规则的掠夺者", "score": 4}],
            risk_tag="self_safety"),
        _question("egocentrism_6", "你是否觉得自己与社会格格不入，甚至有一种被放逐的疏离感？", "egocentrism",
            options=[{"content": "不，我融入得很好", "score": 1}, {"content": "有时", "score": 2}, {"content": "经常", "score": 3}, {"content": "这个世界配不上我", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_8", "对于你未来的犯罪风险，你如何评估？", "antisocial",
            options=[{"content": "绝无可能", "score": 1}, {"content": "不好说", "score": 2}, {"content": "取决于社会对我的态度", "score": 3}, {"content": "我已经走在了犯罪的边缘，且我喜欢这样", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("empathy_5", "你是否相信人性本恶，一切道德不过是生存的伪装？", "empathy",
            options=[{"content": "不信", "score": 1}, {"content": "有点信", "score": 2}, {"content": "认同", "score": 3}, {"content": "彻底认同", "score": 4}],
            risk_tag="self_safety"),
        _question("antisocial_9", "如果让你给自己写一段墓志铭，你会写什么？", "antisocial",
            options=[{"content": "一个善良的人", "score": 1}, {"content": "一个普通的一生", "score": 2}, {"content": "一个试图改变现状的人", "score": 3}, {"content": "一个征服过这个世界的掠夺者", "score": 4}],
            risk_tag="self_safety"),
    ]


def _jindun_socialrule_questions() -> list[dict]:
    """青少年社会规则与生存技能认知问卷 — 25 题"""
    return [
        _question("violent_1", "你是否有过为了「教训」某人，而组织或参与「叫人」堵截的经历", "violent_behavior",
            options=[{"content": "从无", "score": 1}, {"content": "偶尔看热闹", "score": 2}, {"content": "参与过", "score": 3}, {"content": "经常带头组织", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("violent_2", "当你感到愤怒时，是否尝试过通过暴力手段（打、砸、抢）解决问题？", "violent_behavior",
            options=[{"content": "从不", "score": 1}, {"content": "想过但没做", "score": 2}, {"content": "有过几次", "score": 3}, {"content": "这是我的惯用手段", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("marginal_1", "你身边是否有朋友携带管制器具（如刀具、弩）？你对此怎么看？", "marginal_contact",
            options=[{"content": "很危险，离他们远点", "score": 1}, {"content": "偶尔见过", "score": 2}, {"content": "觉得挺酷的", "score": 3}, {"content": "我自己也会携带", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_2", "你是否曾私下阅览、散布带有色情或极端暴力内容的网络链接？", "marginal_contact",
            options=[{"content": "从未接触", "score": 1}, {"content": "偶然看到过", "score": 2}, {"content": "经常分享", "score": 3}, {"content": "甚至会主动寻找", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_3", "在网络游戏或社交群中，是否有过涉及「大额赌资」的交易或参与", "marginal_contact",
            options=[{"content": "从不", "score": 1}, {"content": "偶尔小玩", "score": 2}, {"content": "参与过几次", "score": 3}, {"content": "经常赌，金额较大", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_4", "你是否有过进入未成年人禁止入内的场所（如KTV包厢、酒吧、网咖）的经历？", "marginal_contact",
            options=[{"content": "从不去", "score": 1}, {"content": "因为好奇进去过", "score": 2}, {"content": "经常去", "score": 3}, {"content": "那是我的常驻点", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_5", "对于非法借贷或「看场子」、「拿钱买平安」这种事，你觉得", "marginal_contact",
            options=[{"content": "非法，坚决抵制", "score": 1}, {"content": "跟我没关系", "score": 2}, {"content": "有时不得不做", "score": 3}, {"content": "这是我的生存方式", "score": 4}],
            risk_tag="safety_awareness"),
        _question("violent_3", "你是否有过拿走或毁坏他人财物（不限于学校公物）的经历？", "violent_behavior",
            options=[{"content": "从未", "score": 1}, {"content": "偶尔无心之失", "score": 2}, {"content": "有过", "score": 3}, {"content": "经常，觉得刺激", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("violent_4", "如果有人邀请你参与「搞点钱」（如盗窃、抢夺），你会", "violent_behavior",
            options=[{"content": "报警", "score": 1}, {"content": "拒绝", "score": 2}, {"content": "听听具体怎么做", "score": 3}, {"content": "立刻加入", "score": 4}],
            risk_tag="self_safety"),
        _question("marginal_6", "你是否有过在不知情或被引诱的情况下，尝试接触违禁药物/毒品的经历？", "marginal_contact",
            options=[{"content": "绝不接触", "score": 1}, {"content": "听人提过", "score": 2}, {"content": "见过但没动", "score": 3}, {"content": "尝试过", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("rule_1", "你认为在学校里「以多欺少」是否是建立威信的捷径", "rule_disregard",
            options=[{"content": "不是", "score": 1}, {"content": "有点", "score": 2}, {"content": "有时有效", "score": 3}, {"content": "这是唯一的真理", "score": 4}],
            risk_tag="safety_awareness"),
        _question("rule_2", "如果你看到有人在霸凌他人，你是否会加入以确保自己不被盯上？", "rule_disregard",
            options=[{"content": "绝不加入", "score": 1}, {"content": "犹豫", "score": 2}, {"content": "为了安全会加入", "score": 3}, {"content": "经常参与", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_7", "你是否有过离家出走并结伙在社会上流浪的经历？", "marginal_contact",
            options=[{"content": "从无", "score": 1}, {"content": "有过一次", "score": 2}, {"content": "经常", "score": 3}, {"content": "已经习惯", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_8", "对于网络上的淫秽色情表演或买卖，你是否有过付费参与？", "marginal_contact",
            options=[{"content": "从未", "score": 1}, {"content": "偶然点过", "score": 2}, {"content": "有过", "score": 3}, {"content": "常态化参与", "score": 4}],
            risk_tag="safety_awareness"),
        _question("violent_5", "你是否曾因为抢夺他人财物或索要财物而受到过警告？", "violent_behavior",
            options=[{"content": "从未", "score": 1}, {"content": "有过争执", "score": 2}, {"content": "有过一次", "score": 3}, {"content": "经常", "score": 4, "is_risk_option": True}],
            risk_tag="self_safety"),
        _question("marginal_9", "如果有人让你帮忙传带「违禁品」（刀具、违禁药），你会", "marginal_contact",
            options=[{"content": "拒绝", "score": 1}, {"content": "问清楚是什么", "score": 2}, {"content": "看在钱的份上", "score": 3}, {"content": "经常帮这类人跑腿", "score": 4}],
            risk_tag="safety_awareness"),
        _question("rule_3", "在网络论坛或社群里，你是否喜欢发表针对他人进行「人肉」或恐吓的言论", "rule_disregard",
            options=[{"content": "从不", "score": 1}, {"content": "偶尔", "score": 2}, {"content": "经常", "score": 3}, {"content": "以此为乐", "score": 4}],
            risk_tag="safety_awareness"),
        _question("rule_4", "你是否认为自己还没到「判刑年龄」，所以做点坏事也没什么大不了", "rule_disregard",
            options=[{"content": "法律很有威慑力", "score": 1}, {"content": "有时心存侥幸", "score": 2}, {"content": "觉得没关系", "score": 3}, {"content": "这是我敢作恶的底气", "score": 4}],
            risk_tag="safety_awareness"),
        _question("violent_6", "你是否有过通过虚假交易、诱骗他人获取利益的行为？", "violent_behavior",
            options=[{"content": "没有", "score": 1}, {"content": "偶尔", "score": 2}, {"content": "有过", "score": 3}, {"content": "这是主要收入来源", "score": 4}],
            risk_tag="self_safety"),
        _question("violent_7", "在参与群体争斗时，你通常是负责指挥、动手还是旁观？", "violent_behavior",
            options=[{"content": "从不参与", "score": 1}, {"content": "旁观", "score": 2}, {"content": "动手", "score": 3}, {"content": "指挥者", "score": 4}],
            risk_tag="self_safety"),
        _question("violent_8", "你是否有过非法进入他人居住地、翻越围墙的经历？", "violent_behavior",
            options=[{"content": "没有", "score": 1}, {"content": "好奇做过", "score": 2}, {"content": "有过", "score": 3}, {"content": "经常", "score": 4}],
            risk_tag="self_safety"),
        _question("rule_5", "对于法律规定的禁止事项，你觉得「只要不被抓到」就是安全的吗", "rule_disregard",
            options=[{"content": "不是", "score": 1}, {"content": "某种意义上是", "score": 2}, {"content": "对的", "score": 3}, {"content": "这是常识", "score": 4}],
            risk_tag="safety_awareness"),
        _question("rule_6", "如果你的同伙因为做坏事被抓了，你会第一时间？", "rule_disregard",
            options=[{"content": "提供线索", "score": 1}, {"content": "撇清关系", "score": 2}, {"content": "担心被供出", "score": 3}, {"content": "策划营救/报复", "score": 4}],
            risk_tag="safety_awareness"),
        _question("rule_7", "你是否觉得生活在法律边缘的感觉很「带劲」", "rule_disregard",
            options=[{"content": "不，很恐惧", "score": 1}, {"content": "平平淡淡", "score": 2}, {"content": "确实有点", "score": 3}, {"content": "那是我的追求", "score": 4}],
            risk_tag="safety_awareness"),
        _question("marginal_10", "在你的社交圈中，有谁是经常因为违法违纪被警察带走的吗？", "marginal_contact",
            options=[{"content": "没有", "score": 1}, {"content": "听说过", "score": 2}, {"content": "有我的朋友", "score": 3}, {"content": "那就是我经常出入的圈子", "score": 4}],
            risk_tag="safety_awareness"),
    ]


def _jindun_familyenv_questions() -> list[dict]:
    """家庭成长环境与亲子互动观察调研 — 23 题"""
    return [
        _question("comm_1", "当你和父母意见不一致时，他们通常会？", "communication",
            options=[{"content": "坐下来讨论", "score": 1}, {"content": "听之任之", "score": 2}, {"content": "强迫我听从", "score": 3}, {"content": "只要我闹，他们就答应", "score": 4}],
            risk_tag="family_relationship"),
        _question("comm_2", "在家中，你觉得你的感受会被认真倾听吗？", "communication",
            options=[{"content": "是的，经常", "score": 1}, {"content": "有时", "score": 2}, {"content": "很少", "score": 3}, {"content": "完全不被关心", "score": 4, "is_risk_option": True}],
            risk_tag="family_support"),
        _question("parent_1", "当你在学习或生活中遇到挫折，父母的第一反应是？", "parenting_style",
            options=[{"content": "鼓励并陪我解决", "score": 1}, {"content": "询问原因", "score": 2}, {"content": "指责我没做好", "score": 3}, {"content": "替我全部处理好", "score": 4}],
            risk_tag="family_relationship"),
        _question("support_1", "你父母是否经常向你抱怨工作或生活中的烦恼？", "emotional_support",
            options=[{"content": "从不，他们保护我", "score": 1}, {"content": "偶尔", "score": 2}, {"content": "经常，把我也卷进去", "score": 3}, {"content": "他们只顾自己", "score": 4}],
            risk_tag="family_support"),
        _question("parent_2", "在家里，关于你的事情，多大程度上由你自己做主？", "parenting_style",
            options=[{"content": "大部分事务由我参与决定", "score": 1}, {"content": "只要不闯祸就行", "score": 2}, {"content": "必须完全按要求做", "score": 3}, {"content": "我想干什么就干什么", "score": 4}],
            risk_tag="family_relationship"),
        _question("support_2", "你父母是否关注你学校之外的朋友圈？", "emotional_support",
            options=[{"content": "了解并尊重", "score": 1}, {"content": "基本不问", "score": 2}, {"content": "严厉盘查", "score": 3}, {"content": "完全不在意", "score": 4}],
            risk_tag="family_support"),
        _question("support_3", "当你取得进步时，父母会？", "emotional_support",
            options=[{"content": "肯定我的努力", "score": 1}, {"content": "点头认可", "score": 2}, {"content": "觉得这是应该的", "score": 3}, {"content": "物质奖励", "score": 4}],
            risk_tag="family_support"),
        _question("parent_3", "你是否感到家中的规矩多到让人窒息？", "parenting_style",
            options=[{"content": "规矩适度且合理", "score": 1}, {"content": "没什么规矩", "score": 2}, {"content": "非常多且严苛", "score": 3}, {"content": "家里完全没规矩", "score": 4}],
            risk_tag="family_relationship"),
        _question("parent_4", "如果犯了错，父母最常用的惩罚方式是？", "parenting_style",
            options=[{"content": "讲道理/共同承担后果", "score": 1}, {"content": "没收电子产品", "score": 2}, {"content": "打骂或冷暴力", "score": 3}, {"content": "只要道歉就原谅", "score": 4}],
            risk_tag="family_relationship"),
        _question("comm_3", "你和父母在一起的时间里，大家的状态是？", "communication",
            options=[{"content": "互动交流", "score": 1}, {"content": "各自玩手机", "score": 2}, {"content": "父母说教", "score": 3}, {"content": "互不干扰", "score": 4}],
            risk_tag="family_relationship"),
        _question("parent_5", "你认为父母对你的期待是？", "parenting_style",
            options=[{"content": "健康成长", "score": 1}, {"content": "平安就好", "score": 2}, {"content": "出人头地/按他们设想走", "score": 3}, {"content": "没期待/无所谓", "score": 4}],
            risk_tag="family_relationship"),
        _question("comm_4", "家里如果有重大的经济或生活变动，你会知道吗？", "communication",
            options=[{"content": "会一起商量", "score": 1}, {"content": "隐约知道", "score": 2}, {"content": "绝口不提", "score": 3}, {"content": "从不关心", "score": 4}],
            risk_tag="family_relationship"),
        _question("comm_5", "你是否觉得父母在感情上更关注他们自己，而非你？", "communication",
            options=[{"content": "不是，我很被重视", "score": 1}, {"content": "说不好", "score": 2}, {"content": "经常感到被忽视", "score": 3}, {"content": "确实如此", "score": 4}],
            risk_tag="family_support"),
        _question("support_4", "父母会干涉你的个人空间（如翻看日记、房间）吗？", "emotional_support",
            options=[{"content": "不会，尊重隐私", "score": 1}, {"content": "偶尔查看", "score": 2}, {"content": "经常随意进出", "score": 3}, {"content": "我没有个人空间", "score": 4}],
            risk_tag="family_support"),
        _question("support_5", "当你生病或情绪低落时，家庭的支持力是？", "emotional_support",
            options=[{"content": "全力照顾", "score": 1}, {"content": "简单的关怀", "score": 2}, {"content": "催促赶快好起来", "score": 3}, {"content": "无人过问", "score": 4, "is_risk_option": True}],
            risk_tag="family_support"),
        _question("autonomy_1", "你觉得家里最缺乏的是什么？", "autonomy",
            options=[{"content": "沟通", "score": 1}, {"content": "钱", "score": 2}, {"content": "自由", "score": 3}, {"content": "爱与关心", "score": 4}],
            risk_tag="family_support"),
        _question("support_6", "父母之间如果吵架，会影响到你的心情吗？", "emotional_support",
            options=[{"content": "较少/会事后解释", "score": 1}, {"content": "会影响一点", "score": 2}, {"content": "经常波及到我", "score": 3}, {"content": "我已经习惯了", "score": 4}],
            risk_tag="family_support"),
        _question("parent_6", "对于你的未来规划，父母的做法是？", "parenting_style",
            options=[{"content": "尊重我的兴趣", "score": 1}, {"content": "不管", "score": 2}, {"content": "强行规划", "score": 3}, {"content": "完全没有规划", "score": 4}],
            risk_tag="family_relationship"),
        _question("parent_7", "如果让你评价父母，你会说是？", "parenting_style",
            options=[{"content": "良师益友", "score": 1}, {"content": "房东", "score": 2}, {"content": "严厉的管教者", "score": 3}, {"content": "陌生人", "score": 4}],
            risk_tag="family_relationship"),
        _question("support_7", "你是否曾因为父母的教育方式感到绝望？", "emotional_support",
            options=[{"content": "从没想过", "score": 1}, {"content": "偶尔会有", "score": 2}, {"content": "经常有", "score": 3}, {"content": "一直很绝望", "score": 4}],
            risk_tag="family_support"),
        _question("support_8", "父母是否会当着外人的面数落你的短处？", "emotional_support",
            options=[{"content": "从不，会维护我的自尊", "score": 1}, {"content": "偶尔开玩笑", "score": 2}, {"content": "经常，为了让我脸红", "score": 3}, {"content": "随便说", "score": 4}],
            risk_tag="family_support"),
        _question("comm_6", "当你想和父母交流内心想法时，你通常是？", "communication",
            options=[{"content": "主动且顺畅", "score": 1}, {"content": "试探性地聊", "score": 2}, {"content": "觉得没用而放弃", "score": 3}, {"content": "完全不交流", "score": 4}],
            risk_tag="family_relationship"),
        _question("autonomy_2", "你认为家庭在你成长中的作用是？", "autonomy",
            options=[{"content": "最坚强的后盾", "score": 1}, {"content": "维持基本生活", "score": 2}, {"content": "压力来源", "score": 3}, {"content": "可有可无", "score": 4, "is_risk_option": True}],
            risk_tag="family_support"),
    ]


def _jindun_lifestyle_questions() -> list[dict]:
    """成长阶段生活习惯与环境适应性调研 — 50 题"""
    q = []
    # Part 1: 生活作息与自我管理 (1-15)
    daily = [
        ("daily_1", "周末或假期，你最常待的地方是？", ["家里", "图书馆", "书店/球场", "网吧/游戏厅/娱乐场所"]),
        ("daily_2", "当你感到压力或无聊时，你更倾向于？", ["运动/听歌", "睡觉", "打游戏", "找朋友聚会或去消遣"]),
        ("daily_3", "对于「深夜在外玩耍」这件事，你怎么看？", ["很危险，要回家", "偶尔可以，看情况", "很酷，没人管的感觉", "常态，甚至觉得没意思"]),
        ("daily_4", "你是否有过因为玩乐而不想回家的经历？", ["从未", "很少", "有过几次", "经常"]),
        ("daily_5", "你觉得如果老师没查考勤，不去上课会有什么后果？", ["影响学习，必须去", "没必要去", "无所谓，自由支配时间", "如果不查，我巴不得每天都不去"]),
        ("daily_6", "晚上你会因为玩手机/电脑而熬夜吗？", ["从不", "偶尔", "经常", "每晚必熬"]),
        ("daily_7", "你身边有同学会抽烟吗？你对此的看法是？", ["很反感", "不关心", "无所谓", "觉得很成熟，想尝试"]),
        ("daily_8", "你觉得喝酒对年轻人来说是？", ["伤害身体", "社交工具", "缓解烦恼", "必经的成长礼"]),
        ("daily_9", "你是否曾经为了躲避某件事而选择逃避校园生活（逃学）？", ["从不", "只有一次", "偶尔", "习惯性"]),
        ("daily_10", "你觉得学校规定的校外离校时间合理吗？", ["很合理", "有点严", "没意义", "我想什么时候走就什么时候走"]),
        ("daily_11", "如果让你选择，你更喜欢待在学校还是在社会上打拼？", ["学校", "学校但也想赚钱", "社会上，自由", "社会上，学校太压抑"]),
        ("daily_12", "你是否会对父母隐瞒自己的行踪？", ["从不", "很少", "有时", "经常，为了不被管"]),
        ("daily_13", "你觉得一个人在外面过夜的难度在于？", ["安全", "没地方住", "没钱", "父母会找"]),
        ("daily_14", "你是否尝试过在没有家人的情况下长时间外出？", ["从不", "偶尔", "常有", "已多次离家出走"]),
        ("daily_15", "你是否觉得学校的纪律是对你自由的限制？", ["不限制", "有一点", "很大程度", "极度讨厌"]),
    ]
    for code, title, opts in daily:
        is_risk = code == "daily_14" and True or False
        q.append(_question(code, title, "daily_habits",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="safety_awareness"))

    # Part 2: 数字环境与内容接触 (16-30)
    digital = [
        ("digital_1", "你每天在网络（游戏/短视频）上花费的时间大约是？", ["<1小时", "1-3小时", "3-6小时", "6小时以上"]),
        ("digital_2", "你平时关注的网络博主，内容多倾向于？", ["学习/科普", "生活娱乐", "游戏/八卦", "暴力/猎奇/社会负面"]),
        ("digital_3", "当网络信息与现实发生冲突，你觉得？", ["以现实为准", "半信半疑", "谁更有道理信谁", "网络更有趣"]),
        ("digital_4", "你是否看过带有暴力、色情等内容的视频？", ["从没", "偶然点开", "偶尔看", "这是我的兴趣"]),
        ("digital_5", "你是否在玩游戏时，因为输了而产生极其强烈的暴力冲动？", ["没有", "偶尔吐槽", "有过破坏行为", "习惯性砸键盘鼠标"]),
        ("digital_6", "你是否加入过特定的游戏群或社交群，讨论一些「刺激」的话题？", ["没有", "很少", "经常", "那是我的核心圈子"]),
        ("digital_7", "如果网络上的朋友邀请你去线下聚会，你会？", ["拒绝", "带上好友", "偷偷去", "毫不犹豫去"]),
        ("digital_8", "你觉得网络上的负面言论是？", ["有害的", "无所谓", "正常的抒发", "我喜欢发表这种言论"]),
        ("digital_9", "你是否有过利用网络进行欺凌或传播他人隐私的经历？", ["从没", "想过但没做", "开玩笑做过", "经常以此为乐"]),
        ("digital_10", "你是否觉得网络世界比现实世界更公平？", ["不是", "有时觉得", "差不多", "绝对是"]),
        ("digital_11", "看到宣扬极端思想的内容，你会？", ["举报", "忽视", "觉得挺有道理", "产生共鸣并传播"]),
        ("digital_12", "你是否购买过网络账号或违规游戏道具？", ["没有", "买过一个", "常买", "以此交易获利"]),
        ("digital_13", "你在网络上遇到纠纷时，倾向于？", ["沟通", "拉黑", "对骂", "线下寻仇"]),
        ("digital_14", "你觉得网络上的内容是否应该受到严格过滤？", ["应该", "无所谓", "限制太多", "没必要"]),
        ("digital_15", "你是否曾因为网络内容而模仿过里面的危险行为？", ["从没", "偶尔", "常有", "觉得很有挑战"]),
    ]
    for code, title, opts in digital:
        is_risk = code == "digital_15" and True or False
        q.append(_question(code, title, "digital_env",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="internet_use"))

    # Part 3: 社交圈层与法治意识 (31-50)
    social = [
        ("social_1", "你觉得学校外面的「混混」看起来怎么样？", ["很危险", "不好说", "有点羡慕", "想和他们交朋友"]),
        ("social_2", "当有人带头组织对抗学校/权威时，你会？", ["远离", "看热闹", "参与", "带头起哄"]),
        ("social_3", "你是否参加过打架斗殴或旁观过群体性冲突？", ["从没", "旁观过", "参与过", "是组织者"]),
        ("social_4", "你认为「讲义气」是指？", ["互相帮助学习", "困难时支援", "哪怕错也要一起", "不计代价服从大哥"]),
        ("social_5", "你是否见过同学参与赌博（包括打牌赌钱等）？", ["没见过", "见过但没参与", "参与过少量", "经常参与"]),
        ("social_6", "你觉得变相赌博（如抽奖、博彩）是？", ["违法", "娱乐", "发财之道", "人生必玩"]),
        ("social_7", "你是否接触过封建迷信、算命等活动？", ["从不", "偶尔", "感兴趣", "经常参与"]),
        ("social_8", "你是否出入过酒吧、网吧、KTV等未成年人禁入场所？", ["从不", "偶尔好奇", "常去", "那是我的日常"]),
        ("social_9", "面对法律规定，你觉得？", ["必须遵守", "看情况", "那是管弱者的", "我有办法规避"]),
        ("social_10", "如果有人邀请你加入一个「秘密组织」，你会？", ["拒绝", "先观察", "很兴奋", "立刻加入"]),
        ("social_11", "当你看到有人欺负弱者，你的立场通常是？", ["站出来制止", "走开", "默许", "加入欺负的一方"]),
        ("social_12", "你觉得「法律」和「帮规」哪个在学校更好使？", ["法律", "都不好使", "看情况", "拳头/势力最好使"]),
        ("social_13", "你是否尝试过盗窃或损坏公物？", ["没有", "无意损坏", "有过", "觉得刺激"]),
        ("social_14", "对于社会新闻中关于犯罪的内容，你感到？", ["恐惧", "反思", "无动于衷", "甚至想研究"]),
        ("social_15", "你觉得在社会上立足需要具备什么？", ["知识", "能力", "狠劲", "背景/势力"]),
        ("social_16", "如果警察找上门，你的第一反应是？", ["不知情", "紧张", "试图掩盖", "觉得麻烦"]),
        ("social_17", "你是否有过离家出走并与社会不良人员共处的经历？", ["没有", "短暂接触", "有过", "习惯与他们共处"]),
        ("social_18", "你认为「不良行为」的标准是谁定的？", ["国家", "社会", "学校", "强加给我们的枷锁"]),
        ("social_19", "当你感到孤独时，你更倾向于找谁？", ["家人", "朋友", "社会上的玩伴", "一个人待着"]),
        ("social_20", "你未来最想成为什么样的人？", ["对社会有贡献", "普通人", "有钱有势", "不受任何人约束的王者"]),
    ]
    for code, title, opts in social:
        is_risk = code in ("social_3", "social_17") and True or False
        q.append(_question(code, title, "social_law",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="self_safety"))

    return q


def _jindun_socialvalue_questions() -> list[dict]:
    """青少年社会价值观与校内外认知调研 — 30 题"""
    q = []
    # Part 1: 秩序与规则认知 (1-10)
    rule = [
        ("rule_cog_1", "对于校园内严格的规章制度，你认为？", ["保护秩序", "有待商榷", "毫无意义的枷锁", "用来扼杀个性的工具"]),
        ("rule_cog_2", "你觉得「法律」在现实社会中是？", ["公平的正义", "有钱人的游戏", "约束弱者的工具", "应当被推翻的束缚"]),
        ("rule_cog_3", "看到学校设施被破坏，你的第一反应是？", ["心疼/惋惜", "不关我事", "这种东西早该坏了", "破坏的感觉很解气"]),
        ("rule_cog_4", "如果让你评价「权威」（老师/长辈/管理层），你倾向于？", ["尊重", "中立", "怀疑", "本能抵触"]),
        ("rule_cog_5", "你认为群体暴乱或大规模抵制活动通常是？", ["不可取的", "无奈之举", "正义的呐喊", "改变世界的唯一途径"]),
        ("rule_cog_6", "面对社会上的不平等现象，你觉得最有效的解决方法是？", ["通过法律途径改进", "努力提升自己", "以暴制暴", "彻底毁灭旧秩序"]),
        ("rule_cog_7", "你认为「人性」本质上是？", ["善良的", "复杂的", "自私且丑陋的", "恶毒且不可救药的"]),
        ("rule_cog_8", "如果学校发生群体性违纪，你觉得参与者是？", ["捣乱者", "跟风者", "勇士", "反抗压迫的先锋"]),
        ("rule_cog_9", "你是否觉得世界上的资源分配应该由强力部门重新洗牌？", ["不同意", "无所谓", "有时想过", "非常赞同"]),
        ("rule_cog_10", "你对「社会责任感」这个词的看法是？", ["很重要", "无感", "空话套话", "统治者的谎言"]),
    ]
    for code, title, opts in rule:
        q.append(_question(code, title, "rule_cognition",
            options=[{"content": o, "score": i+1} for i, o in enumerate(opts)],
            risk_tag="safety_awareness"))

    # Part 2: 破坏性倾向探测 (11-20)
    destructive = [
        ("destr_1", "如果你可以随意修改一条学校准则且无人知晓，你会？", ["增加福利", "什么都不改", "删除所有约束", "让学校彻底瘫痪"]),
        ("destr_2", "对于造成群体恐慌的新闻事件，你通常会？", ["感到担忧", "不关心", "觉得刺激", "希望能看到更多这种失控场面"]),
        ("destr_3", "你认为那些被社会公认的「坏人」，其实是？", ["罪有应得", "不幸的", "看透世俗的人", "被体制逼出来的英雄"]),
        ("destr_4", "当看到社会失控的情景（如骚乱、火灾），你的第一反应是？", ["紧张/报警", "旁观", "兴奋", "想加入进去"]),
        ("destr_5", "你是否觉得「校园暴力」在某种程度上是权力的正常体现？", ["不正常", "错误", "合理的阶级演化", "非常合理"]),
        ("destr_6", "如果你感到被某人冒犯，你倾向于？", ["沟通", "冷处理", "诋毁他", "报复让他毁灭"]),
        ("destr_7", "你觉得人类文明的存续是？", ["宝贵的", "平淡的", "充满谎言的", "多余的/应该重置的"]),
        ("destr_8", "对待「异见者」，你的做法是？", ["包容", "忽视", "排挤", "让他消失"]),
        ("destr_9", "当你看到他人痛苦时，你感到？", ["同情", "无感", "一丝快意", "甚至觉得可笑"]),
        ("destr_10", "你认为「善良」的人在现代社会是？", ["可贵的", "普通的", "愚蠢的", "软弱且注定被欺负的"]),
    ]
    for code, title, opts in destructive:
        is_risk = code == "destr_4" and True or False
        q.append(_question(code, title, "destructive",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="self_safety"))

    # Part 3: 深度投射与极端测试 (21-30)
    projection = [
        ("proj_1", "你是否认为现有的社会管理系统应该被彻底瘫痪？", ["绝对不", "不可能", "想过但没做", "这是我的人生理想"]),
        ("proj_2", "如果你发现有人在做坏事，你会？", ["阻止", "走开", "默许", "想参与并给予指导"]),
        ("proj_3", "你觉得「死亡」或「毁灭」在人生观中意味着？", ["终点", "必然", "一种解脱", "最终的终极平等"]),
        ("proj_4", "你认为那些维护秩序的人（警察/老师）是？", ["保护者", "普通职员", "压迫工具", "敌对目标"]),
        ("proj_5", "在你最阴暗的心理活动里，你最想做的一件事是？", ["帮助他人", "自我提升", "羞辱他人", "制造混乱破坏一切"]),
        ("proj_6", "你觉得校园里的「规训」是？", ["必要的", "无聊的", "奴化训练", "对灵魂的摧残"]),
        ("proj_7", "如果社会陷入混乱，你觉得这对你而言是？", ["灾难", "混乱", "机会", "狂欢"]),
        ("proj_8", "你在评价他人的成就时，倾向于？", ["认可", "羡慕", "嫉妒", "认为他是靠肮脏手段得来的"]),
        ("proj_9", "你对「正义」的定义是？", ["法律与道德", "相对的", "胜利者书写的", "并不存在"]),
        ("proj_10", "如果有选择，你是否愿意成为一个破坏现状的「反面角色」？", ["不，我想做正面", "无所谓", "愿意尝试", "这是我渴望的身份"]),
    ]
    for code, title, opts in projection:
        is_risk = code in ("proj_1", "proj_7") and True or False
        q.append(_question(code, title, "projection",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="self_safety"))

    return q


def _jindun_schoolsupport_questions() -> list[dict]:
    """校园生活与个人成长支持度问卷 — 30 题"""
    q = []
    # Part 1: 家庭环境与监护 (1-10)
    family = [
        ("guard_1", "每天放学后，你最希望家里有人吗？", ["当然希望", "有时想", "无所谓", "家里没人我也习惯了"]),
        ("guard_2", "当你在学校遇到麻烦，第一个想到的求助对象是？", ["父母", "亲戚", "老师", "没人可以求助"]),
        ("guard_3", "父母或监护人对你平时在学校的情况了解多少？", ["非常了解", "偶尔关心", "基本不管", "完全不关心"]),
        ("guard_4", "你和父母/监护人有深度交流吗？", ["经常谈心", "偶尔聊聊", "只谈吃饭睡觉", "基本不说话"]),
        ("guard_5", "你是否经常需要独自一人在家过夜？", ["从不", "偶尔", "经常", "大部分时间都是独自居住"]),
        ("guard_6", "家里发生大事时，你会被告知或参与决策吗？", ["是的", "偶尔", "从来不", "不知道家里发生了什么"]),
        ("guard_7", "如果父母长期不在身边，你会感到？", ["孤独", "习惯了", "自由", "被抛弃"]),
        ("guard_8", "你觉得父母对你的爱是否带条件（如成绩好才爱）？", ["不，无论如何都爱", "有时觉得", "有条件", "感觉不到爱"]),
        ("guard_9", "你在家里是否有明确的依靠（如祖父母或可靠的长辈）？", ["有", "有一个", "很少", "没有"]),
        ("guard_10", "你是否曾因为家里没人管而感到自卑？", ["没有", "偶尔", "经常", "已经是常态"]),
    ]
    for code, title, opts in family:
        is_risk = code == "guard_5" and True or False
        q.append(_question(code, title, "family_guardian",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="family_support"))

    # Part 2: 学习状态与未来预期 (11-20)
    learning = [
        ("learn_1", "对于现在的学习生活，你感到？", ["充满希望", "平淡", "迷茫", "想要逃离"]),
        ("learn_2", "你是否曾经想过辍学，理由通常是？", ["从没想过", "偶尔压力大想歇歇", "觉得读书没用", "家里没钱或不让读"]),
        ("learn_3", "如果初中毕业，你的选择是？", ["读高中/职校", "犹豫中", "没想过", "直接去打工"]),
        ("learn_4", "你认为学历对你未来的重要性是？", ["非常重要", "挺重要", "无所谓", "一点用没有"]),
        ("learn_5", "在学校里，你是否有因为「经济条件」或「家庭原因」而不想参加班级活动？", ["从不", "很少", "有时", "经常"]),
        ("learn_6", "你对未来的职业规划是？", ["有明确目标", "有个大概方向", "走一步看一步", "没想过，活着就行"]),
        ("learn_7", "当看到同学有父母接送或给予物质支持，你的感受是？", ["平常心", "小羡慕", "酸楚", "很难过"]),
        ("learn_8", "你觉得老师对你的关注度如何？", ["很关注", "正常", "很少关注", "完全被忽视"]),
        ("learn_9", "如果学校提供助学金，你会申请吗？", ["不需要", "可能", "需要但不敢说", "很需要且正在争取"]),
        ("learn_10", "你认为自己是一个「受欢迎」的孩子吗？", ["是的", "还好", "不太确定", "我是多余的"]),
    ]
    for code, title, opts in learning:
        q.append(_question(code, title, "learning_future",
            options=[{"content": o, "score": i+1} for i, o in enumerate(opts)],
            risk_tag="academic_pressure"))

    # Part 3: 社会支持与困境感知 (21-30)
    support = [
        ("supp_1", "你是否有过因为家庭变故（如家人服刑、生病、离异）感到人生崩塌？", ["没有", "有过短暂情绪", "经常为此难过", "生活已经彻底改变"]),
        ("supp_2", "当遇到突发困难（如没钱吃饭、生病），你会选择？", ["告诉长辈", "告诉好友", "自己硬扛", "不知道怎么办"]),
        ("supp_3", "你是否有过与不熟悉的人接触并感到「被诱惑」的经历？", ["没有", "不确定", "有过", "经常"]),
        ("supp_4", "你对这个社会的基本感觉是？", ["温暖", "平平淡淡", "冷漠", "残酷"]),
        ("supp_5", "遇到不开心的事，你会选择？", ["运动/谈心", "写日记", "发呆", "自暴自弃"]),
        ("supp_6", "如果社会组织（如政府、公益）愿意帮助你，你希望得到哪方面的支持？", ["学习用品", "心理陪伴", "生活费", "改变我的家庭环境"]),
        ("supp_7", "你觉得自己目前的「监护状态」安全吗？", ["很安全", "基本安全", "不太安全", "完全没保障"]),
        ("supp_8", "你是否有过那种「没人管我」的失落感？", ["从未", "偶尔", "经常", "每时每刻"]),
        ("supp_9", "当有人关心你时，你的第一反应是？", ["感激", "奇怪", "不适应", "防备"]),
        ("supp_10", "如果给你的现状打分（满分10），你会打几分？", ["8-10分", "6-7分", "4-5分", "0-3分"]),
    ]
    for code, title, opts in support:
        is_risk = code == "supp_8" and True or False
        q.append(_question(code, title, "social_support",
            options=[{"content": o, "score": i+1, **({"is_risk_option": True} if (is_risk and i == 3) else {})} for i, o in enumerate(opts)],
            risk_tag="interpersonal"))

    return q


BUILTIN_QUESTIONNAIRES = [
    _questionnaire(
        "builtin-comprehensive-risk-v1",
        "青少年综合风险关注筛查问卷",
        "custom",
        "覆盖情绪状态、睡眠状态、学业压力、人际关系、家庭支持、校园安全、网络使用和自我安全八个维度，用于学校场景下的综合风险关注筛查。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        COMPREHENSIVE_DIMENSIONS,
        _comprehensive_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 29.99, "level": "low"},
                {"min": 30, "max": 49.99, "level": "medium"},
                {"min": 50, "max": 69.99, "level": "high"},
                {"min": 70, "max": 100, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "emotion", "min_pct": 75, "level": "high"},
                {"dimension": "self_safety", "min_pct": 60, "level": "urgent"},
                {"dimension": "campus_safety", "min_pct": 75, "level": "high"},
                {"dimension": "internet_use", "min_pct": 75, "level": "high"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "自我安全关注信号"},
                "bullying": {"level": "high", "type_label": "校园欺凌关注信号"},
                "internet_use": {"level": "high", "type_label": "网络使用关注信号"},
            },
            "messages": {
                "low": "结果暂未发现明显高关注信号，建议保持常规关怀和持续观察。",
                "medium": "结果出现一定关注信号，建议结合班级观察和学生访谈进一步了解。",
                "high": "结果出现较明显关注信号，建议班主任或心理老师近期跟进并做好记录。",
                "urgent": "结果出现需要尽快关注的信号，建议学校按照学生关怀流程及时跟进。",
            },
        },
        contradiction_groups=[
            {"question_a_code": "emotion_1", "question_b_code": "emotion_5", "relation_type": "opposite", "max_score_diff": 2},
            {"question_a_code": "sleep_1", "question_b_code": "sleep_5", "relation_type": "opposite", "max_score_diff": 2},
            {"question_a_code": "academic_1", "question_b_code": "academic_3", "relation_type": "opposite", "max_score_diff": 2},
            {"question_a_code": "interpersonal_2", "question_b_code": "interpersonal_6", "relation_type": "opposite", "max_score_diff": 2},
            {"question_a_code": "family_2", "question_b_code": "family_5", "relation_type": "opposite", "max_score_diff": 2},
            {"question_a_code": "internet_1", "question_b_code": "internet_3", "relation_type": "opposite", "max_score_diff": 2},
        ],
    ),
    _questionnaire(
        "builtin-emotion-phq-like-v1",
        "情绪状态参考性筛查问卷（20题）",
        "mental_health",
        "参考常见情绪状态筛查结构设计，用于学校场景下识别情绪低落方面的关注信号。",
        "初一,初二,初三,高一,高二,高三",
        "standard_like",
        _dimensions(("emotion", "情绪状态")),
        _phq_like_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 0, "max": 9, "level": "low"},
                {"min": 10, "max": 19, "level": "medium"},
                {"min": 20, "max": 29, "level": "medium"},
                {"min": 30, "max": 44, "level": "high"},
                {"min": 45, "max": 60, "level": "urgent"},
            ],
            "risk_tag_rules": {"self_safety": {"level": "urgent", "type_label": "自我安全关注信号"}},
            "messages": {
                "low": "结果提示情绪低落关注信号较少，建议保持常规支持。",
                "medium": "结果提示存在一定情绪低落关注信号，建议结合近期状态进一步了解。",
                "high": "结果提示情绪低落关注信号较明显，建议老师近期主动关心并跟进。",
                "urgent": "结果提示需要尽快关注的情绪低落相关信号，建议学校及时跟进支持。",
            },
        },
    ),
    _questionnaire(
        "builtin-anxiety-gad-like-v1",
        "焦虑压力参考性筛查问卷（15题）",
        "mental_health",
        "参考常见焦虑压力筛查结构设计，用于学校场景下识别焦虑和持续担忧方面的关注信号。",
        "初一,初二,初三,高一,高二,高三",
        "standard_like",
        _dimensions(("emotion", "焦虑压力")),
        _gad_like_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 0, "max": 7, "level": "low"},
                {"min": 8, "max": 14, "level": "medium"},
                {"min": 15, "max": 29, "level": "high"},
                {"min": 30, "max": 45, "level": "urgent"},
            ],
            "messages": {
                "low": "结果提示焦虑压力关注信号较少，建议保持常规观察。",
                "medium": "结果提示存在一定焦虑压力关注信号，建议了解学生近期压力来源。",
                "high": "结果提示焦虑压力关注信号较明显，建议老师结合学习生活状态及时跟进。",
                "urgent": "结果提示需要尽快关注的焦虑压力相关信号，建议学校尽快启动支持。",
            },
        },
    ),
    _questionnaire(
        "builtin-sleep-reference-v1",
        "睡眠状态参考性筛查问卷（18题）",
        "mental_health",
        "围绕入睡困难、睡眠维持、日间疲劳和作息规律设计，用于学校场景下了解学生睡眠状态。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(("sleep", "睡眠状态")),
        _sleep_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 49.99, "level": "medium"},
                {"min": 50, "max": 74.99, "level": "high"},
                {"min": 75, "max": 100, "level": "urgent"},
            ],
            "messages": {
                "low": "结果提示睡眠状态总体平稳。",
                "medium": "结果提示存在一定睡眠困扰，建议了解作息和学习节奏。",
                "high": "结果提示睡眠困扰较明显，建议结合日间精神状态持续关注。",
                "urgent": "结果提示睡眠相关信号需要及时关注，建议尽快了解近期生活与压力情况。",
            },
        },
    ),
    _questionnaire(
        "builtin-bullying-risk-v1",
        "校园欺凌风险排查问卷",
        "bullying",
        "围绕被欺凌、欺凌他人、旁观者反应、求助意愿和班级安全感设计，用于学校排查校园欺凌相关关注信号。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("campus_safety", "被欺凌与班级安全"),
            ("interpersonal", "同伴互动与求助"),
        ),
        _bullying_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {"bullying": {"level": "high", "type_label": "校园欺凌关注信号"}},
            "messages": {
                "low": "结果暂未提示明显校园欺凌关注信号。",
                "medium": "结果提示存在一定校园冲突或安全感不足信号，建议班级层面关注。",
                "high": "结果提示较明显的校园欺凌相关信号，建议老师尽快核实并跟进。",
                "urgent": "结果提示需要及时处理的校园欺凌相关信号，建议学校按流程尽快介入。",
            },
        },
    ),
    _questionnaire(
        "builtin-internet-risk-v1",
        "网络使用风险筛查问卷",
        "internet_addiction",
        "围绕使用时长、失控感、学习影响、睡眠影响、情绪依赖和社交影响设计，用于了解学生网络使用风险。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("internet_use", "使用时长与失控感"),
            ("sleep", "睡眠影响"),
            ("academic_pressure", "学习影响"),
            ("emotion", "情绪依赖"),
            ("interpersonal", "社交影响"),
            ("self_safety", "网络边界与安全"),
        ),
        _internet_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "internet_use": {"level": "high", "type_label": "网络使用关注信号"},
                "self_safety": {"level": "high", "type_label": "网络安全关注信号"},
            },
            "messages": {
                "low": "结果提示网络使用总体可控。",
                "medium": "结果提示存在一定网络使用关注信号，建议了解时间管理和作息情况。",
                "high": "结果提示网络使用关注信号较明显，建议近期与学生沟通使用习惯。",
                "urgent": "结果提示网络使用相关信号需要尽快关注，建议学校及时跟进支持。",
            },
        },
    ),
    _questionnaire(
        "builtin-academic-pressure-v1",
        "学业压力与考试焦虑筛查问卷",
        "academic_pressure",
        "围绕学习负担、考试焦虑、自我效能、家长期待和失败担忧设计，用于识别学业压力相关关注信号。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("academic_pressure", "学习负担与考试压力"),
            ("emotion", "失败担忧与自我评价"),
            ("family_support", "家长期待"),
            ("interpersonal", "求助与支持"),
            ("sleep", "作息影响"),
        ),
        _academic_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {"academic_pressure": {"level": "high", "type_label": "学业压力关注信号"}},
            "messages": {
                "low": "结果提示学业压力总体在可应对范围内。",
                "medium": "结果提示存在一定学业压力信号，建议关注近期考试和负担情况。",
                "high": "结果提示学业压力和考试焦虑信号较明显，建议尽快了解支持需求。",
                "urgent": "结果提示需要及时关注的学业压力相关信号，建议学校尽快安排跟进。",
            },
        },
    ),
    _questionnaire(
        "builtin-interpersonal-adaptation-v1",
        "人际关系与班级适应筛查问卷",
        "interpersonal",
        "围绕同伴支持、孤立感、冲突、归属感和求助意愿设计，用于了解学生在班级中的适应情况。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("interpersonal", "同伴支持与求助意愿"),
            ("campus_safety", "归属感与班级适应"),
            ("emotion", "社交担忧"),
        ),
        _interpersonal_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "messages": {
                "low": "结果提示班级适应和同伴关系总体较稳定。",
                "medium": "结果提示存在一定人际关系关注信号，建议结合班级观察了解情况。",
                "high": "结果提示人际关系或班级适应信号较明显，建议老师近期主动关心。",
                "urgent": "结果提示人际与班级适应相关信号需要及时关注，建议尽快安排跟进。",
            },
        },
    ),
    _questionnaire(
        "builtin-family-support-v1",
        "家庭支持与亲子沟通筛查问卷",
        "family_relationship",
        "围绕情感支持、沟通质量、冲突频率、陪伴感和求助资源设计，用于了解学生的家庭支持体验。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("family_support", "家庭支持与沟通"),
            ("emotion", "家庭氛围带来的感受"),
            ("academic_pressure", "家庭期待与学习影响"),
            ("sleep", "家庭冲突带来的作息影响"),
        ),
        _family_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "messages": {
                "low": "结果提示家庭支持总体稳定。",
                "medium": "结果提示存在一定家庭支持或沟通方面的关注信号，建议适度了解家庭互动。",
                "high": "结果提示家庭支持相关信号较明显，建议结合家校沟通进一步复核。",
                "urgent": "结果提示家庭支持相关信号需要及时关注，建议学校尽快安排跟进支持。",
            },
        },
    ),
    _questionnaire(
        "builtin-safety-awareness-v1",
        "安全意识与自我保护筛查问卷",
        "safety_awareness",
        "围绕校园安全、网络安全、陌生人风险、求助意识和边界意识设计，用于了解学生的安全意识与自我保护能力。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("campus_safety", "校园安全与求助意识"),
            ("self_safety", "边界意识与自我保护"),
            ("interpersonal", "同伴影响"),
            ("emotion", "求助顾虑"),
        ),
        _safety_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {"self_safety": {"level": "urgent", "type_label": "自我安全关注信号"}},
            "messages": {
                "low": "结果提示安全意识和自我保护能力总体较稳定。",
                "medium": "结果提示存在一定安全意识关注信号，建议加强日常提醒和支持。",
                "high": "结果提示安全意识或边界保护信号较明显，建议近期针对性跟进。",
                "urgent": "结果提示自我保护相关信号需要及时关注，建议学校尽快启动支持流程。",
            },
        },
    ),

    # ==================== 标准化心理量表（C 系列） ====================

    # C.1 SCL-90 适应问卷 (90题)
    _questionnaire(
        "builtin-scl90-adapted-v1",
        "SCL-90 症状自评量表（适应版）",
        "mental_health",
        "基于症状自评量表 SCL-90 适应设计，涵盖躯体化、重复思维、人际敏感、情绪低落、紧张担忧、情绪波动、担忧害怕、敏感多疑、思维与感知9个维度。适用于学校场景下心理健康综合筛查。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("somatization", "躯体化"),
            ("obsessive", "重复思维"),
            ("interpersonal_sensitivity", "人际敏感"),
            ("depression", "情绪低落"),
            ("anxiety", "紧张担忧"),
            ("hostility", "情绪波动"),
            ("phobic", "担忧害怕"),
            ("paranoid", "敏感多疑"),
            ("psychoticism", "思维与感知"),
        ),
        _scl90_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "dimension_avg",
            "dimension_avg_rules": [
                {"dimension": "any", "avg_min": 2.0, "avg_max": 2.99, "level": "medium"},
                {"dimension": "any", "avg_min": 3.0, "avg_max": 3.99, "level": "high"},
                {"dimension": "any", "avg_min": 4.0, "avg_max": 5.0, "level": "urgent"},
            ],
            "total_avg_rules": [
                {"min": 0, "max": 1.99, "level": "low"},
                {"min": 2.0, "max": 2.99, "level": "medium"},
                {"min": 3.0, "max": 3.99, "level": "high"},
                {"min": 4.0, "max": 5.0, "level": "urgent"},
            ],
            "messages": {
                "low": "各项指标均在正常范围，建议保持常规关怀。",
                "medium": "部分维度出现关注信号，建议结合教师观察进一步了解。",
                "high": "较多维度出现明显关注信号，建议心理老师近期跟进并做好记录。",
                "urgent": "多项维度出现需要尽快关注的信号，建议学校按照学生关怀流程及时介入。",
            },
        },
    ),

    # C.2 MSSMHS 适应问卷 (60题)
    _questionnaire(
        "builtin-mssmhs-adapted-v1",
        "中学生心理健康量表（MSSMHS 适应版）",
        "mental_health",
        "基于中国中学生心理健康量表 MSSMHS 适应设计，涵盖重复思维、敏感多疑、情绪波动、人际敏感、情绪低落、紧张担忧、学习压力、适应困难、情绪不稳定、心理平衡10个维度。专为中国中学生设计。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("force", "重复思维"),
            ("paranoid", "敏感多疑"),
            ("hostility", "情绪波动"),
            ("interpersonal_sensitivity", "人际敏感"),
            ("depression", "情绪低落"),
            ("anxiety", "紧张担忧"),
            ("learning_pressure", "学习压力"),
            ("adaptation", "适应困难"),
            ("emotional_instability", "情绪不稳定"),
            ("psychological_imbalance", "心理平衡"),
        ),
        _mssmhs_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 34.99, "level": "low"},
                {"min": 35, "max": 49.99, "level": "medium"},
                {"min": 50, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "depression", "min_pct": 65, "level": "high"},
                {"dimension": "anxiety", "min_pct": 65, "level": "high"},
                {"dimension": "emotional_instability", "min_pct": 65, "level": "high"},
                {"dimension": "learning_pressure", "min_pct": 65, "level": "high"},
            ],
            "messages": {
                "low": "心理健康状况总体良好，建议保持常规关怀。",
                "medium": "部分维度出现关注信号，建议结合日常观察了解情况。",
                "high": "较多维度出现明显关注信号，建议心理老师近期跟进。",
                "urgent": "多项维度出现需要尽快关注的信号，建议学校及时启动支持流程。",
            },
        },
    ),

    # C.3 DASS-21 适应问卷 (21题)
    _questionnaire(
        "builtin-dass21-adapted-v1",
        "抑郁-焦虑-压力量表（DASS-21 适应版）",
        "mental_health",
        "基于 DASS-21 适应设计，涵盖情绪低落、紧张担忧、压力感受三个子量表，每个7题。用于学校场景下快速筛查情绪和压力状态。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("depression", "情绪低落"),
            ("anxiety", "紧张担忧"),
            ("stress", "压力感受"),
        ),
        _dass21_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "subscale_score",
            "subscale_rules": {
                "depression": [
                    {"min": 0, "max": 9, "level": "low"},
                    {"min": 10, "max": 13, "level": "medium"},
                    {"min": 14, "max": 20, "level": "high"},
                    {"min": 21, "max": 42, "level": "urgent"},
                ],
                "anxiety": [
                    {"min": 0, "max": 7, "level": "low"},
                    {"min": 8, "max": 9, "level": "medium"},
                    {"min": 10, "max": 14, "level": "high"},
                    {"min": 15, "max": 42, "level": "urgent"},
                ],
                "stress": [
                    {"min": 0, "max": 14, "level": "low"},
                    {"min": 15, "max": 18, "level": "medium"},
                    {"min": 19, "max": 25, "level": "high"},
                    {"min": 26, "max": 42, "level": "urgent"},
                ],
            },
            "messages": {
                "low": "抑郁、焦虑和压力各项指标均在正常范围。",
                "medium": "部分子量表出现轻度关注信号，建议关注近期生活事件。",
                "high": "子量表出现中度关注信号，建议心理老师近期跟进了解。",
                "urgent": "子量表出现需要尽快关注的信号，建议学校及时启动支持。",
            },
        },
    ),

    # C.4 CIAS-R 适应问卷 (19题)
    _questionnaire(
        "builtin-ciasr-adapted-v1",
        "网络使用情况问卷（CIAS-R 适应版）",
        "internet_addiction",
        "基于陈氏网络成瘾量表 CIAS-R 适应设计，涵盖使用习惯、离开网络时的感受、使用时间变化、生活影响、时间管理5个维度。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("compulsive_use", "使用习惯"),
            ("withdrawal", "离开网络时的感受"),
            ("tolerance", "使用时间变化"),
            ("interpersonal_health", "生活影响"),
            ("time_management", "时间管理"),
        ),
        _ciasr_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 0, "max": 38, "level": "low"},
                {"min": 39, "max": 45, "level": "medium"},
                {"min": 46, "max": 55, "level": "high"},
                {"min": 56, "max": 76, "level": "urgent"},
            ],
            "messages": {
                "low": "网络使用总体在正常范围。",
                "medium": "出现一定网络使用关注信号，建议了解使用习惯和时间管理。",
                "high": "网络使用关注信号较明显，建议近期与学生沟通并关注生活影响。",
                "urgent": "网络使用相关信号需要尽快关注，建议学校及时介入支持。",
            },
        },
    ),

    # C.5 PSQI 适应问卷 (19题)
    _questionnaire(
        "builtin-psqi-adapted-v1",
        "匹兹堡睡眠质量指数（PSQI 适应版）",
        "sleep",
        "基于匹兹堡睡眠质量指数 PSQI 适应设计，涵盖睡眠质量、入睡时间、睡眠时长、睡眠效率、睡眠障碍、安眠药物使用（改为作息调节）、日间功能障碍7个成分。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("sleep_quality", "睡眠质量"),
            ("sleep_latency", "入睡时间"),
            ("sleep_duration", "睡眠时长"),
            ("sleep_efficiency", "睡眠效率"),
            ("sleep_disturbance", "睡眠障碍"),
            ("daytime_dysfunction", "日间功能障碍"),
        ),
        _psqi_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 0, "max": 4, "level": "low"},
                {"min": 5, "max": 9, "level": "medium"},
                {"min": 10, "max": 14, "level": "high"},
                {"min": 15, "max": 21, "level": "urgent"},
            ],
            "messages": {
                "low": "睡眠质量总体良好。",
                "medium": "存在一定睡眠质量问题，建议了解作息和学习节奏。",
                "high": "睡眠质量较差，建议结合日间精神状态持续关注。",
                "urgent": "睡眠问题严重，建议尽快了解近期生活与压力情况并安排支持。",
            },
        },
    ),

    # C.6 欺凌扩展问卷 (30题)
    _questionnaire(
        "builtin-bullying-extended-v1",
        "校园欺凌扩展排查问卷",
        "bullying",
        "基于 Olweus 欺凌问卷结构扩展设计，涵盖受欺凌、攻击行为、旁观者反应、网络欺凌、求助行为和安全感6个维度。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("victimization", "受欺凌"),
            ("aggression", "攻击行为"),
            ("bystander", "旁观行为"),
            ("cyberbullying", "网络欺凌"),
            ("help_seeking", "求助行为"),
            ("safety", "安全感"),
        ),
        _bullying_extended_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 44.99, "level": "medium"},
                {"min": 45, "max": 64.99, "level": "high"},
                {"min": 65, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "bullying": {"level": "high", "type_label": "校园欺凌关注信号"},
            },
            "messages": {
                "low": "校园安全感和同伴关系总体稳定。",
                "medium": "存在一定校园冲突或欺凌关注信号，建议班级层面关注。",
                "high": "校园欺凌相关信号较明显，建议老师尽快核实并跟进。",
                "urgent": "需要及时处理的校园欺凌相关信号，建议学校按流程尽快介入。",
            },
        },
    ),

    # C.7 家庭环境问卷 (23题)
    _questionnaire(
        "builtin-family-embuf-adapted-v1",
        "家庭教养方式问卷（s-EMBU 适应版）",
        "family",
        "基于简版父母教养方式问卷 s-EMBU 适应设计，涵盖拒绝、情感温暖、过度保护3个维度，了解学生对家庭教养方式的感知。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("rejection", "拒绝"),
            ("emotional_warmth", "情感温暖"),
            ("overprotection", "过度保护"),
        ),
        _family_embuf_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 29.99, "level": "low"},
                {"min": 30, "max": 49.99, "level": "medium"},
                {"min": 50, "max": 69.99, "level": "high"},
                {"min": 70, "max": 100, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "rejection", "min_pct": 65, "level": "high"},
                {"dimension": "overprotection", "min_pct": 65, "level": "medium"},
            ],
            "messages": {
                "low": "家庭教养方式感知总体正面。",
                "medium": "部分教养方式维度出现关注信号，建议适度了解家庭互动情况。",
                "high": "家庭教养方式相关信号较明显，建议结合家校沟通进一步了解。",
                "urgent": "家庭教养方式相关信号需要及时关注，建议学校安排跟进支持。",
            },
        },
    ),

    # C.8 自伤风险筛查 (26题)
    _questionnaire(
        "builtin-selfharm-risk-v1",
        "自我安全风险筛查问卷",
        "mental_health",
        "基于压力感受、积极心态、睡眠和掩饰量表结构设计，用于筛查学生心理健康相关关注信号。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("hopelessness", "压力感受"),
            ("optimism", "积极心态"),
            ("sleep", "睡眠"),
            ("concealment", "掩饰"),
            ("self_safety", "自我关爱"),
        ),
        _selfharm_risk_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 29.99, "level": "low"},
                {"min": 30, "max": 49.99, "level": "medium"},
                {"min": 50, "max": 69.99, "level": "high"},
                {"min": 70, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "自我安全关注信号"},
            },
            "messages": {
                "low": "暂未发现自我安全相关高关注信号。",
                "medium": "出现一定关注信号，建议结合教师观察和学生访谈了解情况。",
                "high": "出现较明显的自我安全相关信号，建议学校按照关怀流程尽快跟进。",
                "urgent": "出现需要紧急关注的自我安全信号，建议学校立即启动干预流程。",
            },
        },
    ),

    # C.9 金盾护苗行为筛查量表 (30题)
    _questionnaire(
        "builtin-jindun-behavior-v1",
        "金盾护苗 · 青少年行为筛查量表",
        "jindun_behavior",
        "根据金盾护苗行动要求设计的行为筛查量表，涵盖关爱帮扶需求、行为习惯、行为偏差和规则意识4个维度，用于对未成年人进行分类识别。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("care_need", "关爱帮扶需求"),
            ("bad_behavior", "行为习惯"),
            ("serious_bad_behavior", "行为偏差"),
            ("criminal_indicator", "规则意识"),
        ),
        _jindun_behavior_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 24.99, "level": "low"},
                {"min": 25, "max": 45.99, "level": "medium"},
                {"min": 46, "max": 62.49, "level": "high"},
                {"min": 62.5, "max": 100, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "criminal_indicator", "min_pct": 50, "level": "urgent"},
                {"dimension": "serious_bad_behavior", "min_pct": 50, "level": "high"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "违法行为关注信号"},
                "campus_safety": {"level": "high", "type_label": "严重不良行为关注信号"},
            },
            "messages": {
                "low": "测评结果显示该学生可能需要额外的关爱和帮扶，建议学校加强日常关怀和家庭联系。",
                "medium": "测评结果显示该学生存在一定的不良行为倾向，建议学校进行针对性的行为引导和教育干预。",
                "high": "测评结果显示该学生存在较为严重的不良行为倾向，建议学校启动重点帮扶机制，联合家庭和社区共同干预。",
                "urgent": "测评结果显示该学生存在需要司法或专业机构介入的行为信号，建议学校按既有流程联系相关部门并启动综合帮扶。",
            },
        },
    ),

    # C.10 金盾护苗家庭环境评估表 (15题)
    _questionnaire(
        "builtin-jindun-family-v1",
        "金盾护苗 · 家庭环境评估表",
        "jindun_family",
        "用于评估未成年人的家庭监护质量、家庭环境和情感支持状况，帮助识别需要关爱帮扶的学生群体。",
        "初一,初二,初三,高一,高二,高三",
        "reference_screening",
        _dimensions(
            ("family_guardianship", "家庭监护"),
            ("family_environment", "家庭环境"),
            ("emotional_support", "情感支持"),
        ),
        _jindun_family_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score_pct",
            "total_pct_ranges": [
                {"min": 0, "max": 29.99, "level": "low"},
                {"min": 30, "max": 49.99, "level": "medium"},
                {"min": 50, "max": 69.99, "level": "high"},
                {"min": 70, "max": 100, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "family_guardianship", "min_pct": 60, "level": "medium"},
                {"dimension": "family_environment", "min_pct": 60, "level": "high"},
                {"dimension": "emotional_support", "min_pct": 60, "level": "medium"},
            ],
            "risk_tag_rules": {
                "family_support": {"level": "medium", "type_label": "家庭环境关注信号"},
            },
            "messages": {
                "low": "家庭环境评估总体良好，建议保持日常关怀。",
                "medium": "家庭环境存在一定关注信号，建议适度了解家庭互动情况并给予更多关爱。",
                "high": "家庭环境相关信号较明显，建议结合家校沟通进一步了解并提供支持。",
                "urgent": "家庭环境相关信号需要及时关注，建议学校安排跟进支持并联系监护人。",
            },
        },
    ),

    # ===== 新增标准化问卷 (批次1: 21-24) =====

    # 21. 罗森伯格自尊量表 (RSES)
    _questionnaire(
        "RSES",
        "自我感受与评价问卷",
        "self_esteem",
        "这份问卷想了解同学们对自己的看法和感受。每道题没有对错之分，请根据最近一段时间的真实感受作答。",
        "6-12",
        "standard_like",
        _dimensions(("self_worth", "自我价值感"), ("self_acceptance", "自我接纳")),
        [
            _question("rses_1", "总的来说，我对自己比较满意", "self_worth", options=RSES_4),
            _question("rses_2", "我觉得自己有不少优点", "self_worth", options=RSES_4),
            _question("rses_3", "我觉得自己和大多数人一样能做好事情", "self_acceptance", options=RSES_4),
            _question("rses_4", "我觉得自己是一个有价值的人", "self_worth", options=RSES_4),
            _question("rses_5", "我觉得自己没有什么值得骄傲的地方", "self_acceptance", options=RSES_4, reverse=True),
            _question("rses_6", "我有时会觉得自己什么都不行", "self_acceptance", options=RSES_4, reverse=True),
            _question("rses_7", "我觉得自己还是有很多不错的地方", "self_worth", options=RSES_4),
            _question("rses_8", "我希望能对自己更有信心", "self_acceptance", options=RSES_4, reverse=True),
            _question("rses_9", "总的来说，我倾向于认为自己是个失败者", "self_acceptance", options=RSES_4, reverse=True),
            _question("rses_10", "我对自己抱着积极的态度", "self_worth", options=RSES_4),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 0, "max": 15, "level": "high"},
                {"min": 16, "max": 25, "level": "medium"},
                {"min": 26, "max": 40, "level": "low"},
            ],
            "messages": {
                "low": "自我感受评估良好，建议保持积极的自我认知。",
                "medium": "自我感受方面存在一定波动，建议老师多给予鼓励和肯定。",
                "high": "自我感受方面信号需要关注，建议老师主动了解并给予支持。",
            },
        },
    ),

    # 22. 康纳-戴维森心理韧性量表简版 (CD-RISC-10)
    _questionnaire(
        "CD-RISC10",
        "应对困难能力问卷",
        "resilience",
        "这份问卷想了解同学们在面对困难和变化时的感受和做法。每道题没有对错之分，请根据真实情况作答。",
        "6-12",
        "standard_like",
        _dimensions(("toughness", "坚韧"), ("adaptability", "适应能力")),
        [
            _question("cdrisc_1", "当遇到变化时，我能很快适应", "adaptability", options=CD_RISC_5),
            _question("cdrisc_2", "压力大的时候，我能保持冷静和专注", "toughness", options=CD_RISC_5),
            _question("cdrisc_3", "遇到挫折时，我会想办法克服而不是放弃", "toughness", options=CD_RISC_5),
            _question("cdrisc_4", "我觉得什么事情发生都有它的原因", "adaptability", options=CD_RISC_5),
            _question("cdrisc_5", "即使事情看起来很难，我也相信自己能做好", "toughness", options=CD_RISC_5),
            _question("cdrisc_6", "面对失败，我不会轻易被打倒", "toughness", options=CD_RISC_5),
            _question("cdrisc_7", "在压力下，我能够集中精力去处理需要做的事", "adaptability", options=CD_RISC_5),
            _question("cdrisc_8", "我喜欢在生活中接受挑战", "adaptability", options=CD_RISC_5),
            _question("cdrisc_9", "经历过困难的事情后，我感觉自己变得更强大了", "toughness", options=CD_RISC_5),
            _question("cdrisc_10", "我相信自己能够实现自己设定的目标", "toughness", options=CD_RISC_5),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 0, "max": 20, "level": "high"},
                {"min": 21, "max": 30, "level": "medium"},
                {"min": 31, "max": 40, "level": "low"},
            ],
            "messages": {
                "low": "应对困难的能力评估良好，心理韧性水平正常。",
                "medium": "应对困难的能力存在一定波动，建议关注并适当引导。",
                "high": "应对困难方面的信号需要关注，建议提供更多的支持和鼓励。",
            },
        },
    ),

    # 23. UCLA孤独量表第三版 (UCLA-V3)
    _questionnaire(
        "UCLA_V3",
        "社交与独处感受问卷",
        "loneliness",
        "这份问卷想了解同学们在日常生活中的社交感受。每道题描述的是一种情况，请根据最近一段时间的真实体验作答。",
        "6-12",
        "standard_like",
        _dimensions(("social_connect", "社交连接"), ("emotional_loneliness", "情感孤独感")),
        [
            _question("ucla_1", "我觉得自己和周围的人关系很融洽", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_2", "我有很多可以聊天的朋友", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_3", "我觉得没有人真正了解我", "emotional_loneliness", options=UCLA_4),
            _question("ucla_4", "我感觉自己和别人之间有距离感", "emotional_loneliness", options=UCLA_4),
            _question("ucla_5", "我觉得自己属于某个集体或圈子", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_6", "我有可以分享心事的人", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_7", "我常常感到孤单", "emotional_loneliness", options=UCLA_4),
            _question("ucla_8", "我觉得身边没有人能真正理解我", "emotional_loneliness", options=UCLA_4),
            _question("ucla_9", "我觉得自己被忽视了", "emotional_loneliness", options=UCLA_4),
            _question("ucla_10", "我能和同学朋友打成一片", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_11", "我觉得自己不被接纳", "emotional_loneliness", options=UCLA_4),
            _question("ucla_12", "我觉得自己和别人之间缺乏亲密感", "emotional_loneliness", options=UCLA_4),
            _question("ucla_13", "我觉得自己在人群中格格不入", "social_connect", options=UCLA_4),
            _question("ucla_14", "我觉得周围的人并不关心我", "emotional_loneliness", options=UCLA_4),
            _question("ucla_15", "我觉得自己有很多朋友", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_16", "我觉得自己的社交圈子很小", "social_connect", options=UCLA_4),
            _question("ucla_17", "我觉得自己被冷落了", "emotional_loneliness", options=UCLA_4),
            _question("ucla_18", "我觉得身边的人愿意帮助我", "social_connect", options=UCLA_4, reverse=True),
            _question("ucla_19", "我觉得自己找不到可以依靠的人", "emotional_loneliness", options=UCLA_4),
            _question("ucla_20", "我觉得自己和同学相处得不错", "social_connect", options=UCLA_4, reverse=True),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 20, "max": 36, "level": "low"},
                {"min": 37, "max": 48, "level": "medium"},
                {"min": 49, "max": 80, "level": "high"},
            ],
            "messages": {
                "low": "社交感受评估正常，人际连接状况良好。",
                "medium": "社交方面存在一定孤独感受，建议关注同伴交往情况。",
                "high": "孤独感信号较为明显，建议了解同伴关系并提供社交支持。",
            },
        },
    ),

    # 24. 领悟社会支持量表 (PSSS)
    _questionnaire(
        "PSSS",
        "身边支持力量问卷",
        "social_support",
        "这份问卷想了解同学们在生活中能获得哪些支持和帮助。请根据自己的真实感受选择最符合的选项。",
        "6-12",
        "standard_like",
        _dimensions(("family_support", "家庭支持"), ("friend_support", "朋友支持"), ("other_support", "其他支持")),
        [
            _question("psss_1", "当我遇到困难时，家人会尽力帮助我", "family_support", options=PSSS_7),
            _question("psss_2", "我能和家人分享快乐与忧愁", "family_support", options=PSSS_7),
            _question("psss_3", "我的家人理解我的需求和感受", "family_support", options=PSSS_7),
            _question("psss_4", "在我需要的时候，家人会出现在我身边", "family_support", options=PSSS_7),
            _question("psss_5", "我有可以信赖和倾诉的朋友", "friend_support", options=PSSS_7),
            _question("psss_6", "朋友们会关心我的生活和感受", "friend_support", options=PSSS_7),
            _question("psss_7", "我能依靠朋友们来解决一些问题", "friend_support", options=PSSS_7),
            _question("psss_8", "朋友们会在我需要时给予帮助", "friend_support", options=PSSS_7),
            _question("psss_9", "身边有老师或长辈关心我的成长", "other_support", options=PSSS_7),
            _question("psss_10", "遇到问题时，我可以找老师或长辈商量", "other_support", options=PSSS_7),
            _question("psss_11", "我所在的集体让我感到温暖和支持", "other_support", options=PSSS_7),
            _question("psss_12", "周围的人愿意帮助我度过难关", "other_support", options=PSSS_7),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 12, "max": 36, "level": "high"},
                {"min": 37, "max": 60, "level": "medium"},
                {"min": 61, "max": 84, "level": "low"},
            ],
            "messages": {
                "low": "社会支持评估良好，能感受到来自家人和朋友的关心。",
                "medium": "社会支持方面存在一定不足，建议关注学生的人际支持状况。",
                "high": "社会支持信号较弱，建议了解家庭和同伴关系，提供必要的支持资源。",
            },
        },
    ),

    # ===== 新增标准化问卷 (批次2: 25-28) =====

    # 25. 儿童抑郁量表 (CDI)
    _questionnaire(
        "CDI",
        "日常心情与状态问卷",
        "depression",
        "这份问卷想了解同学们最近两周的心情和日常状态。请根据自己的真实情况选择最符合的选项。",
        "6-12",
        "standard_like",
        _dimensions(("anhedonia", "兴趣与活力"), ("negative_mood", "负面情绪"), ("low_self_esteem", "自我评价"), ("inefficiency", "效率感"), ("interpersonal", "人际感受")),
        [
            _question("cdi_1", "最近两周，我觉得做什么事都没意思", "anhedonia", options=CDI_3),
            _question("cdi_2", "最近两周，我总是不开心", "negative_mood", options=CDI_3),
            _question("cdi_3", "最近两周，我觉得什么事情都做不好", "low_self_esteem", options=CDI_3),
            _question("cdi_4", "最近两周，我觉得做什么事都很费劲", "inefficiency", options=CDI_3),
            _question("cdi_5", "最近两周，我常常想一个人待着", "interpersonal", options=CDI_3),
            _question("cdi_6", "最近两周，我觉得没有人关心我", "interpersonal", options=CDI_3),
            _question("cdi_7", "最近两周，我觉得自己不如别人", "low_self_esteem", options=CDI_3),
            _question("cdi_8", "最近两周，我对什么都提不起兴趣", "anhedonia", options=CDI_3),
            _question("cdi_9", "最近两周，我经常感到烦躁不安", "negative_mood", options=CDI_3),
            _question("cdi_10", "最近两周，我觉得自己是个负担", "low_self_esteem", options=CDI_3),
            _question("cdi_11", "最近两周，我睡不好觉", "inefficiency", options=CDI_3),
            _question("cdi_12", "最近两周，我觉得很疲惫", "inefficiency", options=CDI_3),
            _question("cdi_13", "最近两周，我不想吃东西", "inefficiency", options=CDI_3),
            _question("cdi_14", "最近两周，我觉得很孤独", "interpersonal", options=CDI_3),
            _question("cdi_15", "最近两周，我觉得别人都不喜欢我", "interpersonal", options=CDI_3),
            _question("cdi_16", "最近两周，我觉得做什么都集中不了注意力", "inefficiency", options=CDI_3),
            _question("cdi_17", "最近两周，我很容易发脾气", "negative_mood", options=CDI_3),
            _question("cdi_18", "最近两周，我觉得未来没什么希望", "negative_mood", options=CDI_3),
            _question("cdi_19", "最近两周，我觉得生活没什么意义", "negative_mood", options=CDI_3),
            _question("cdi_20", "最近两周，我不想和别人说话", "interpersonal", options=CDI_3),
            _question("cdi_21", "最近两周，我觉得自己长得不好看", "low_self_esteem", options=CDI_3),
            _question("cdi_22", "最近两周，我常常感到害怕", "negative_mood", options=CDI_3),
            _question("cdi_23", "最近两周，我觉得学习压力很大", "inefficiency", options=CDI_3),
            _question("cdi_24", "最近两周，我觉得很难交到朋友", "interpersonal", options=CDI_3),
            _question("cdi_25", "最近两周，我对以前喜欢的事也提不起兴趣", "anhedonia", options=CDI_3),
            _question("cdi_26", "最近两周，我觉得自己很多方面都不行", "low_self_esteem", options=CDI_3),
            _question("cdi_27", "最近两周，我觉得自己很没用", "low_self_esteem", options=CDI_3),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 0, "max": 13, "level": "low"},
                {"min": 14, "max": 19, "level": "medium"},
                {"min": 20, "max": 54, "level": "high"},
            ],
            "dimension_rules": [
                {"dimension": "negative_mood", "max_score": 12, "min_pct": 60, "level": "medium"},
                {"dimension": "low_self_esteem", "max_score": 12, "min_pct": 60, "level": "medium"},
            ],
            "messages": {
                "low": "心情与状态评估正常，建议保持积极乐观的生活态度。",
                "medium": "心情方面存在一定波动，建议老师关注并适当沟通了解。",
                "high": "心情与状态方面信号需要关注，建议学校安排心理辅导老师进一步了解。",
            },
        },
    ),

    # 26. 优势与困难问卷 (SDQ)
    _questionnaire(
        "SDQ",
        "成长与发展问卷",
        "strengths_difficulties",
        "这份问卷想了解同学们在成长过程中的一些表现和特点。请根据最近六个月的真实情况作答，每道题没有对错之分。",
        "6-12",
        "standard_like",
        _dimensions(("emotional_symptoms", "情绪感受"), ("conduct_problems", "行为表现"), ("hyperactivity", "注意力与活跃"), ("peer_problems", "同伴关系"), ("prosocial", "友善行为")),
        [
            _question("sdq_1", "我常常觉得头疼、肚子疼或身体不舒服", "emotional_symptoms", options=SDQ_3),
            _question("sdq_2", "我经常担心很多事情", "emotional_symptoms", options=SDQ_3),
            _question("sdq_3", "我常常感到不开心、想哭或情绪低落", "emotional_symptoms", options=SDQ_3),
            _question("sdq_4", "和同龄人在一起时，我通常很紧张", "emotional_symptoms", options=SDQ_3),
            _question("sdq_5", "我有很多担忧和顾虑", "emotional_symptoms", options=SDQ_3),
            _question("sdq_6", "我通常会按照规则行事", "conduct_problems", options=SDQ_3, reverse=True),
            _question("sdq_7", "我常常发脾气或发火", "conduct_problems", options=SDQ_3),
            _question("sdq_8", "我通常按照大人的要求去做", "conduct_problems", options=SDQ_3, reverse=True),
            _question("sdq_9", "我有时会和别人吵架或欺负别人", "conduct_problems", options=SDQ_3),
            _question("sdq_10", "我有时会说谎或不守承诺", "conduct_problems", options=SDQ_3),
            _question("sdq_11", "我能集中注意力做好一件事", "hyperactivity", options=SDQ_3, reverse=True),
            _question("sdq_12", "我做事之前会先想一想", "hyperactivity", options=SDQ_3, reverse=True),
            _question("sdq_13", "我做事容易坚持到底", "hyperactivity", options=SDQ_3, reverse=True),
            _question("sdq_14", "我常常坐不住、喜欢动来动去", "hyperactivity", options=SDQ_3),
            _question("sdq_15", "我很容易被周围的事情分散注意力", "hyperactivity", options=SDQ_3),
            _question("sdq_16", "和同龄人相比，我比较容易被人欺负", "peer_problems", options=SDQ_3),
            _question("sdq_17", "我比较喜欢自己玩，不太喜欢和别人一起", "peer_problems", options=SDQ_3),
            _question("sdq_18", "我有很多好朋友", "peer_problems", options=SDQ_3, reverse=True),
            _question("sdq_19", "别的同学喜欢和我在一起", "peer_problems", options=SDQ_3, reverse=True),
            _question("sdq_20", "和同龄人相比，我比较孤独", "peer_problems", options=SDQ_3),
            _question("sdq_21", "我会主动帮助受伤或不开心的同学", "prosocial", options=SDQ_3),
            _question("sdq_22", "我通常对别人比较友善", "prosocial", options=SDQ_3),
            _question("sdq_23", "如果有人心情不好，我会主动安慰他们", "prosocial", options=SDQ_3),
            _question("sdq_24", "我通常会和同龄人分享东西", "prosocial", options=SDQ_3),
            _question("sdq_25", "我通常会关心别人的感受", "prosocial", options=SDQ_3),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 0, "max": 13, "level": "low"},
                {"min": 14, "max": 16, "level": "medium"},
                {"min": 17, "max": 40, "level": "high"},
            ],
            "dimension_rules": [
                {"dimension": "emotional_symptoms", "max_score": 10, "min_pct": 60, "level": "medium"},
                {"dimension": "conduct_problems", "max_score": 10, "min_pct": 60, "level": "medium"},
                {"dimension": "peer_problems", "max_score": 10, "min_pct": 60, "level": "medium"},
            ],
            "messages": {
                "low": "成长发展评估总体良好，各维度表现正常。",
                "medium": "成长发展方面存在一定关注信号，建议适当了解并给予支持。",
                "high": "成长发展方面信号需要关注，建议结合具体维度了解情况并提供帮助。",
            },
        },
    ),

    # 27. 青少年生活事件量表 (ASLEC)
    _questionnaire(
        "ASLEC",
        "近期生活经历问卷",
        "life_events",
        "这份问卷想了解同学们最近一段时间的生活经历。请根据自己的真实情况作答：如果该事件发生过，请评价它对你的影响程度；如果没发生过，请选择「未发生过」。",
        "6-12",
        "standard_like",
        _dimensions(("interpersonal", "人际方面"), ("academic", "学业方面"), ("punishment", "受罚方面"), ("loss", "丧失方面"), ("health", "健康方面")),
        [
            _question("aslec_1", "被人误会或被人错怪", "interpersonal", options=ASLEC_5),
            _question("aslec_2", "和同学或朋友发生矛盾", "interpersonal", options=ASLEC_5),
            _question("aslec_3", "当众丢面子或被人嘲笑", "interpersonal", options=ASLEC_5),
            _question("aslec_4", "被老师批评或处罚", "punishment", options=ASLEC_5),
            _question("aslec_5", "考试成绩不理想", "academic", options=ASLEC_5),
            _question("aslec_6", "学习压力太大", "academic", options=ASLEC_5),
            _question("aslec_7", "被人歧视或被冷落", "interpersonal", options=ASLEC_5),
            _question("aslec_8", "和好友关系破裂", "interpersonal", options=ASLEC_5),
            _question("aslec_9", "家庭经济出现问题", "loss", options=ASLEC_5),
            _question("aslec_10", "家人之间关系紧张或吵架", "loss", options=ASLEC_5),
            _question("aslec_11", "亲人去世", "loss", options=ASLEC_5),
            _question("aslec_12", "亲人患重病或受伤", "loss", options=ASLEC_5),
            _question("aslec_13", "自己患重病或受伤", "health", options=ASLEC_5),
            _question("aslec_14", "被罚款或受到纪律处分", "punishment", options=ASLEC_5),
            _question("aslec_15", "升学或转学带来的压力", "academic", options=ASLEC_5),
            _question("aslec_16", "与老师关系紧张", "interpersonal", options=ASLEC_5),
            _question("aslec_17", "被人欺负或威胁", "interpersonal", options=ASLEC_5),
            _question("aslec_18", "考试或比赛失败", "academic", options=ASLEC_5),
            _question("aslec_19", "达不到父母的期望", "academic", options=ASLEC_5),
            _question("aslec_20", "家庭变故（如父母离异等）", "loss", options=ASLEC_5),
            _question("aslec_21", "生活中遇到不公平的事", "interpersonal", options=ASLEC_5),
            _question("aslec_22", "睡眠不好或失眠", "health", options=ASLEC_5),
            _question("aslec_23", "受到惊吓", "health", options=ASLEC_5),
            _question("aslec_24", "被人冤枉或误解", "interpersonal", options=ASLEC_5),
            _question("aslec_25", "转学或换了新环境", "academic", options=ASLEC_5),
            _question("aslec_26", "亲人外出打工或长期不在身边", "loss", options=ASLEC_5),
            _question("aslec_27", "沉迷手机或网络被限制", "punishment", options=ASLEC_5),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 0, "max": 50, "level": "low"},
                {"min": 51, "max": 89, "level": "medium"},
                {"min": 90, "max": 135, "level": "high"},
            ],
            "dimension_rules": [
                {"dimension": "interpersonal", "max_score": 40, "min_pct": 60, "level": "medium"},
                {"dimension": "academic", "max_score": 25, "min_pct": 60, "level": "medium"},
                {"dimension": "loss", "max_score": 30, "min_pct": 60, "level": "high"},
            ],
            "messages": {
                "low": "近期生活事件影响较小，生活状况总体平稳。",
                "medium": "近期经历了一些有影响的生活事件，建议关注学生的适应情况。",
                "high": "近期生活事件影响较大，建议了解具体情况并提供必要的支持和帮助。",
            },
        },
    ),

    # 28. 情绪调节问卷 (ERQ)
    _questionnaire(
        "ERQ",
        "情绪管理方式问卷",
        "emotion_regulation",
        "这份问卷想了解同学们在面对不同情绪时通常会怎么做。每道题描述的是一种做法，请根据自己的真实情况作答。",
        "6-12",
        "standard_like",
        _dimensions(("cognitive_reappraisal", "认知重评"), ("expressive_suppression", "表达抑制")),
        [
            _question("erq_1", "当我遇到不开心的事时，我会换一个角度去看待它", "cognitive_reappraisal", options=ERQ_7),
            _question("erq_2", "当我感到紧张时，我会控制自己不表现出来", "expressive_suppression", options=ERQ_7),
            _question("erq_3", "当我遇到困难时，我会想这也许是件好事", "cognitive_reappraisal", options=ERQ_7),
            _question("erq_4", "当我感到不开心时，我不会让别人看出来", "expressive_suppression", options=ERQ_7),
            _question("erq_5", "当不好的事情发生时，我会告诉自己这只是暂时的", "cognitive_reappraisal", options=ERQ_7),
            _question("erq_6", "当我有负面情绪时，我会控制自己的表情和行为", "expressive_suppression", options=ERQ_7),
            _question("erq_7", "当遇到不顺心的事时，我会试着从中找到积极的一面", "cognitive_reappraisal", options=ERQ_7),
            _question("erq_8", "当我情绪不好时，我倾向于把感受藏在心里", "expressive_suppression", options=ERQ_7),
            _question("erq_9", "当我遇到挫折时，我会告诉自己这能让我学到东西", "cognitive_reappraisal", options=ERQ_7),
            _question("erq_10", "当我有强烈的情绪时，我会忍住不表达出来", "expressive_suppression", options=ERQ_7),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 10, "max": 30, "level": "low"},
                {"min": 31, "max": 50, "level": "medium"},
                {"min": 51, "max": 70, "level": "high"},
            ],
            "dimension_rules": [
                {"dimension": "expressive_suppression", "max_score": 35, "min_pct": 70, "level": "medium"},
            ],
            "messages": {
                "low": "情绪管理方式评估正常，情绪调节能力良好。",
                "medium": "情绪管理方面存在一定特点，建议关注学生的情绪表达方式。",
                "high": "情绪管理方面有值得关注的倾向，建议引导学生学习更灵活的情绪调节方式。",
            },
        },
    ),

    # ===== 新增标准化问卷 (批次3: 29-32) =====

    # 29. 生活满意度量表 (SWLS)
    _questionnaire(
        "SWLS",
        "生活满意度问卷",
        "life_satisfaction",
        "这份问卷想了解同学们对自己生活状况的整体感受。请根据自己的真实想法选择最符合的选项。",
        "6-12",
        "standard_like",
        _dimensions(("life_satisfaction", "生活满意度")),
        [
            _question("swls_1", "我的生活状况和我期望的比较接近", "life_satisfaction", options=SWLS_7),
            _question("swls_2", "我对自己的生活感到满意", "life_satisfaction", options=SWLS_7),
            _question("swls_3", "到现在为止，我已经得到了生活中想要的重要东西", "life_satisfaction", options=SWLS_7),
            _question("swls_4", "如果可以重新来过，我几乎不会改变什么", "life_satisfaction", options=SWLS_7),
            _question("swls_5", "总的来说，我觉得自己的生活是丰富多彩的", "life_satisfaction", options=SWLS_7),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 5, "max": 9, "level": "high"},
                {"min": 10, "max": 19, "level": "medium"},
                {"min": 20, "max": 35, "level": "low"},
            ],
            "messages": {
                "low": "生活满意度评估良好，对生活状况感到满意。",
                "medium": "生活满意度方面存在一定波动，建议关注学生的生活感受。",
                "high": "生活满意度方面信号较低，建议了解学生的生活状况并给予关心。",
            },
        },
    ),

    # 30. 一般自我效能感量表 (GSES)
    _questionnaire(
        "GSES",
        "自我能力感知问卷",
        "self_efficacy",
        "这份问卷想了解同学们对自己能力的看法。请根据自己的真实感受选择最符合的选项。",
        "6-12",
        "standard_like",
        _dimensions(("self_efficacy", "自我效能感")),
        [
            _question("gses_1", "如果我尽力去做的话，我总能解决问题", "self_efficacy", options=GSES_4),
            _question("gses_2", "即使别人反对我，我仍有办法取得我想要的", "self_efficacy", options=GSES_4),
            _question("gses_3", "对我来说，坚持理想和达成目标是轻而易举的", "self_efficacy", options=GSES_4),
            _question("gses_4", "我自信能有效地应付意外情况", "self_efficacy", options=GSES_4),
            _question("gses_5", "以我的才智，我定能应付意料之外的情况", "self_efficacy", options=GSES_4),
            _question("gses_6", "如果我付出必要的努力，我一定能解决大多数难题", "self_efficacy", options=GSES_4),
            _question("gses_7", "我能冷静地面对困难，因为我相信自己的处理能力", "self_efficacy", options=GSES_4),
            _question("gses_8", "面对一个难题时，我通常能找到几个解决方法", "self_efficacy", options=GSES_4),
            _question("gses_9", "有麻烦的时候，我通常能想到一些应付的方法", "self_efficacy", options=GSES_4),
            _question("gses_10", "无论什么事发生在我身上，我都能应付自如", "self_efficacy", options=GSES_4),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 10, "max": 20, "level": "high"},
                {"min": 21, "max": 30, "level": "medium"},
                {"min": 31, "max": 40, "level": "low"},
            ],
            "messages": {
                "low": "自我效能感评估良好，对自己应对挑战的能力有信心。",
                "medium": "自我效能感方面存在一定波动，建议多给予鼓励和成功体验。",
                "high": "自我效能感方面信号较低，建议通过小目标积累成功经验来增强信心。",
            },
        },
    ),

    # 31. 青少年学习倦怠量表 (ASBI)
    _questionnaire(
        "ASBI",
        "学习状态与感受问卷",
        "academic_burnout",
        "这份问卷想了解同学们在学习方面的感受和状态。请根据最近一段时间的真实情况作答。",
        "6-12",
        "standard_like",
        _dimensions(("emotional_exhaustion", "情绪耗竭"), ("learning_disengagement", "学习疏离"), ("low_achievement", "低成就感")),
        [
            _question("asbi_1", "一想到要学习，我就觉得很累", "emotional_exhaustion", options=ASBI_5),
            _question("asbi_2", "我觉得学习让我精疲力竭", "emotional_exhaustion", options=ASBI_5),
            _question("asbi_3", "我一整天学习下来觉得特别疲惫", "emotional_exhaustion", options=ASBI_5),
            _question("asbi_4", "我对学习越来越没有热情了", "learning_disengagement", options=ASBI_5),
            _question("asbi_5", "我觉得学习对我来说没什么意义", "learning_disengagement", options=ASBI_5),
            _question("asbi_6", "我对学习越来越不感兴趣了", "learning_disengagement", options=ASBI_5),
            _question("asbi_7", "我觉得自己在学习上做不出什么成绩", "low_achievement", options=ASBI_5),
            _question("asbi_8", "我觉得自己的学习能力不如别人", "low_achievement", options=ASBI_5),
            _question("asbi_9", "我觉得自己在学习方面没有成就感", "low_achievement", options=ASBI_5),
            _question("asbi_10", "我很难从学习中获得快乐", "learning_disengagement", options=ASBI_5),
            _question("asbi_11", "我觉得学习是一种负担", "emotional_exhaustion", options=ASBI_5),
            _question("asbi_12", "我常常想逃避学习任务", "learning_disengagement", options=ASBI_5),
            _question("asbi_13", "我觉得不管怎么努力，学习成绩都不会提高", "low_achievement", options=ASBI_5),
            _question("asbi_14", "我觉得自己在学习方面很失败", "low_achievement", options=ASBI_5),
            _question("asbi_15", "我在学习时很难集中注意力", "emotional_exhaustion", options=ASBI_5),
            _question("asbi_16", "我越来越不想去学校了", "learning_disengagement", options=ASBI_5),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 16, "max": 35, "level": "low"},
                {"min": 36, "max": 47, "level": "medium"},
                {"min": 48, "max": 80, "level": "high"},
            ],
            "dimension_rules": [
                {"dimension": "emotional_exhaustion", "max_score": 25, "min_pct": 60, "level": "medium"},
                {"dimension": "learning_disengagement", "max_score": 25, "min_pct": 60, "level": "medium"},
            ],
            "messages": {
                "low": "学习状态评估良好，学习积极性和投入度正常。",
                "medium": "学习方面存在一定倦怠感受，建议关注学生的学习动力。",
                "high": "学习倦怠信号较为明显，建议了解原因并调整学习节奏和支持方式。",
            },
        },
    ),

    # 32. 考试焦虑量表 (TAS)
    _questionnaire(
        "TAS",
        "考试感受问卷",
        "test_anxiety",
        "这份问卷想了解同学们在考试前后的一些感受和想法。请根据自己的真实情况作答，每道题没有对错之分。",
        "6-12",
        "standard_like",
        _dimensions(("worry", "担忧"), ("emotionality", "情绪反应"), ("bodily_symptoms", "身体反应"), ("cognitive_interference", "思维干扰")),
        [
            _question("tas_1", "考试前我会感到紧张不安", "emotionality", options=TAS_4),
            _question("tas_2", "考试时我会担心自己考不好", "worry", options=TAS_4),
            _question("tas_3", "考试前我会觉得心跳加快", "bodily_symptoms", options=TAS_4),
            _question("tas_4", "考试时我会担心成绩不理想会怎样", "worry", options=TAS_4),
            _question("tas_5", "考试前我会觉得肚子不舒服", "bodily_symptoms", options=TAS_4),
            _question("tas_6", "考试时我会担心比别人考得差", "worry", options=TAS_4),
            _question("tas_7", "考试时我的手会出汗或发抖", "bodily_symptoms", options=TAS_4),
            _question("tas_8", "考试时我会想一些和考试无关的事", "cognitive_interference", options=TAS_4),
            _question("tas_9", "考试前我会睡不好觉", "bodily_symptoms", options=TAS_4),
            _question("tas_10", "考试时我觉得脑子一片空白", "cognitive_interference", options=TAS_4),
            _question("tas_11", "考试前我会觉得压力很大", "emotionality", options=TAS_4),
            _question("tas_12", "考试时我会担心让父母失望", "worry", options=TAS_4),
            _question("tas_13", "考试前我会觉得头痛或头晕", "bodily_symptoms", options=TAS_4),
            _question("tas_14", "考试时我会想不起来本来记住的内容", "cognitive_interference", options=TAS_4),
            _question("tas_15", "考试前我会觉得心情烦躁", "emotionality", options=TAS_4),
            _question("tas_16", "考试时我会担心时间不够用", "worry", options=TAS_4),
            _question("tas_17", "考试前我会觉得吃不下东西", "bodily_symptoms", options=TAS_4),
            _question("tas_18", "考试时我很难集中注意力", "cognitive_interference", options=TAS_4),
            _question("tas_19", "考试前我会觉得浑身不自在", "bodily_symptoms", options=TAS_4),
            _question("tas_20", "考试时我会担心自己做的题是错的", "worry", options=TAS_4),
            _question("tas_21", "考试前我会觉得呼吸不顺畅", "bodily_symptoms", options=TAS_4),
            _question("tas_22", "考试时我觉得自己的思路很混乱", "cognitive_interference", options=TAS_4),
            _question("tas_23", "考试前我会觉得很害怕", "emotionality", options=TAS_4),
            _question("tas_24", "考试时我会担心被老师批评", "worry", options=TAS_4),
            _question("tas_25", "考试前我会觉得肌肉紧张", "bodily_symptoms", options=TAS_4),
            _question("tas_26", "考试时我会反复想不好的结果", "cognitive_interference", options=TAS_4),
            _question("tas_27", "考试前我会觉得心里发慌", "emotionality", options=TAS_4),
            _question("tas_28", "考试时我会担心别人比我答得好", "worry", options=TAS_4),
            _question("tas_29", "考试前我会觉得坐立不安", "emotionality", options=TAS_4),
            _question("tas_30", "考试时我会觉得很难发挥出正常水平", "cognitive_interference", options=TAS_4),
            _question("tas_31", "考试前我会觉得总想上厕所", "bodily_symptoms", options=TAS_4),
            _question("tas_32", "考试时我会担心考砸了怎么办", "worry", options=TAS_4),
            _question("tas_33", "考试前我会觉得心情沉重", "emotionality", options=TAS_4),
            _question("tas_34", "考试时我会觉得很难做出选择", "cognitive_interference", options=TAS_4),
            _question("tas_35", "考试前我会觉得身体发软", "bodily_symptoms", options=TAS_4),
            _question("tas_36", "考试时我会想赶紧做完离开", "cognitive_interference", options=TAS_4),
            _question("tas_37", "考试前我会觉得特别焦虑", "emotionality", options=TAS_4),
        ],
        {"method": "sum", "score_types": ["scale"], "exclude_attention_check": True, "exclude_types": ["fill_blank", "short_answer"]},
        {
            "basis": "total_score",
            "total_ranges": [
                {"min": 37, "max": 74, "level": "low"},
                {"min": 75, "max": 97, "level": "medium"},
                {"min": 98, "max": 148, "level": "high"},
            ],
            "dimension_rules": [
                {"dimension": "worry", "max_score": 40, "min_pct": 60, "level": "medium"},
                {"dimension": "emotionality", "max_score": 40, "min_pct": 60, "level": "medium"},
                {"dimension": "bodily_symptoms", "max_score": 40, "min_pct": 60, "level": "medium"},
            ],
            "messages": {
                "low": "考试焦虑评估正常，考试应对能力良好。",
                "medium": "考试方面存在一定焦虑感受，建议引导学生建立积极的考试心态。",
                "high": "考试焦虑信号较为明显，建议了解具体焦虑来源并提供应对策略支持。",
            },
        },
    ),

    # =========================================================================
    # 金盾护苗专用问卷 (6 套)
    # =========================================================================

    # 33. 青少年自我认知与心理特质调研
    _questionnaire(
        "builtin-jindun-selfcognition-v1",
        "青少年自我认知与心理特质调研",
        "custom",
        "通过隐性测试捕捉青少年性格裂痕，评估同理心缺失、自我中心、操控倾向和反社会冲动等人格特质风险。",
        JINDUN_GRADES,
        "reference_screening",
        _dimensions(
            ("empathy", "同理心与道德感知"),
            ("egocentrism", "自我中心与优越感"),
            ("manipulation", "控制欲与操控倾向"),
            ("antisocial", "反社会与冲动倾向"),
        ),
        _jindun_selfcognition_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 26, "max": 50, "level": "low"},
                {"min": 51, "max": 75, "level": "medium"},
                {"min": 76, "max": 104, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "人格特质风险信号"},
            },
            "messages": {
                "low": "性格内核健康，具备良好的自我调节能力。建议保持常规关注。",
                "medium": "存在明显的性格缺陷信号，如自私、冷漠、冲动等，需重点关注其压力来源。",
                "urgent": "具备典型的高风险人格倾向（如缺乏罪恶感、操控欲强、无视社会契约），建议学校按学生关怀流程及时跟进。",
            },
        },
    ),

    # 34. 青少年社会规则与生存技能认知问卷
    _questionnaire(
        "builtin-jindun-socialrule-v1",
        "青少年社会规则与生存技能认知问卷",
        "safety_awareness",
        "评估青少年在社会规则遵守、违法接触和暴力行为等方面的风险程度，识别潜在违法行为倾向。",
        JINDUN_GRADES,
        "reference_screening",
        _dimensions(
            ("violent_behavior", "暴力与违法行为"),
            ("marginal_contact", "社会边缘接触"),
            ("rule_disregard", "规则漠视与侥幸心理"),
        ),
        _jindun_socialrule_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 25, "max": 40, "level": "low"},
                {"min": 41, "max": 70, "level": "medium"},
                {"min": 71, "max": 100, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "违法行为风险信号"},
                "safety_awareness": {"level": "high", "type_label": "规则意识薄弱信号"},
            },
            "messages": {
                "low": "无明显违规倾向，社会规则意识良好。建议保持常规教育。",
                "medium": "社交圈存在严重违规隐患，需进行个别排查和引导。",
                "urgent": "极大概率有相关行为史，建议学校按学生安全流程尽快跟进，必要时联系公安机关进行风险评估。",
            },
        },
    ),

    # 35. 家庭成长环境与亲子互动观察调研
    _questionnaire(
        "builtin-jindun-familyenv-v1",
        "家庭成长环境与亲子互动观察调研",
        "family_relationship",
        "评估家庭沟通方式、教育风格、情感支持和自主权等维度，识别家庭教育缺失或高压控制风险。",
        JINDUN_GRADES,
        "reference_screening",
        _dimensions(
            ("communication", "沟通与倾听方式"),
            ("parenting_style", "教育与管教方式"),
            ("emotional_support", "情感支持与关怀"),
            ("autonomy", "自主权与个人空间"),
        ),
        _jindun_familyenv_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 23, "max": 40, "level": "low"},
                {"min": 41, "max": 65, "level": "medium"},
                {"min": 66, "max": 92, "level": "high"},
            ],
            "risk_tag_rules": {
                "family_relationship": {"level": "high", "type_label": "亲子关系关注信号"},
                "family_support": {"level": "high", "type_label": "家庭支持缺失信号"},
            },
            "messages": {
                "low": "亲子关系健康，教育方式科学。建议保持良好沟通。",
                "medium": "存在教育方式不当的信号，建议调整沟通频率或方式，关注学生情绪变化。",
                "high": "存在明显的教育缺失或高压控制，极易导致孩子出现行为偏差，建议学校进行家庭走访并提供指导支持。",
            },
        },
    ),

    # 36. 成长阶段生活习惯与环境适应性调研
    _questionnaire(
        "builtin-jindun-lifestyle-v1",
        "成长阶段生活习惯与环境适应性调研",
        "custom",
        "从生活作息、数字环境接触和社交圈层三个维度评估青少年的行为偏差与环境适应风险。",
        JINDUN_GRADES,
        "reference_screening",
        _dimensions(
            ("daily_habits", "生活作息与自我管理"),
            ("digital_env", "数字环境与内容接触"),
            ("social_law", "社交圈层与法治意识"),
        ),
        _jindun_lifestyle_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 50, "max": 80, "level": "low"},
                {"min": 81, "max": 130, "level": "medium"},
                {"min": 131, "max": 200, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "social_law", "min_pct": 80, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "高风险行为信号"},
                "internet_use": {"level": "high", "type_label": "网络内容风险信号"},
                "safety_awareness": {"level": "high", "type_label": "安全意识薄弱信号"},
            },
            "messages": {
                "low": "生活习惯良好，具备较强的自我管理能力与避险意识。建议保持常规关注。",
                "medium": "存在生活习惯紊乱或同伴压力影响的信号，需要关注其社交圈和日常行为。",
                "urgent": "存在严重的行为偏差与高风险活动倾向，建议重点排查并及时跟进支持。",
            },
        },
    ),

    # 37. 青少年社会价值观与校内外认知调研
    _questionnaire(
        "builtin-jindun-socialvalue-v1",
        "青少年社会价值观与校内外认知调研",
        "custom",
        "从秩序认知、破坏性倾向和深度投射三个层面探测青少年的反社会价值观和破坏行为动机。",
        JINDUN_GRADES,
        "reference_screening",
        _dimensions(
            ("rule_cognition", "秩序与规则认知"),
            ("destructive", "破坏性倾向探测"),
            ("projection", "深度投射与极端测试"),
        ),
        _jindun_socialvalue_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 30, "max": 50, "level": "low"},
                {"min": 51, "max": 85, "level": "medium"},
                {"min": 86, "max": 120, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "destructive", "min_pct": 80, "level": "urgent"},
                {"dimension": "projection", "min_pct": 80, "level": "urgent"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "urgent", "type_label": "破坏性倾向信号"},
                "safety_awareness": {"level": "high", "type_label": "规则认知偏差信号"},
            },
            "messages": {
                "low": "具备基本的社会契约精神和规则意识。建议保持常规教育引导。",
                "medium": "存在明显的抵触情绪或愤世嫉俗的认知信号，建议结合日常观察进行针对性引导。",
                "urgent": "具备强烈的反体制、反社会人格特征，潜藏潜在的破坏行为动机，建议学校按学生安全流程尽快跟进。",
            },
        },
    ),

    # 38. 校园生活与个人成长支持度问卷
    _questionnaire(
        "builtin-jindun-schoolsupport-v1",
        "校园生活与个人成长支持度问卷",
        "interpersonal",
        "从家庭监护、学习状态和社会支持三个维度评估青少年的困境程度和支持需求，识别监护缺失和社交孤立。",
        JINDUN_GRADES,
        "reference_screening",
        _dimensions(
            ("family_guardian", "家庭环境与监护"),
            ("learning_future", "学习状态与未来预期"),
            ("social_support", "社会支持与困境感知"),
        ),
        _jindun_schoolsupport_questions(),
        deepcopy(SCORING_RULE_DEFAULT),
        {
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 30, "max": 50, "level": "low"},
                {"min": 51, "max": 80, "level": "medium"},
                {"min": 81, "max": 120, "level": "high"},
            ],
            "risk_tag_rules": {
                "family_support": {"level": "high", "type_label": "监护缺失信号"},
                "academic_pressure": {"level": "medium", "type_label": "学业困境信号"},
                "interpersonal": {"level": "high", "type_label": "社交孤立信号"},
            },
            "messages": {
                "low": "有良好的监护与支持系统，生活状态稳定。建议保持常规关怀。",
                "medium": "存在明显的监护薄弱环节或社交孤立感，建议班主任加强日常关注和沟通。",
                "high": "极度缺乏社会支撑，急需介入进行家庭走访与心理关怀，建议学校启动帮扶流程。",
            },
        },
    ),
]


def _refresh_questionnaire(existing: Questionnaire, data: dict) -> None:
    existing.title = data["title"]
    existing.description = data["description"]
    existing.category = data["category"]
    existing.applicable_grades = data["applicable_grades"]
    existing.is_builtin = True
    existing.source_type = data["source_type"]
    existing.disclaimer = data["disclaimer"]
    existing.dimensions = data["dimensions"]
    existing.scoring_rule = data["scoring_rule"]
    existing.risk_rules = data["risk_rules"]
    existing.quality_rules = data["quality_rules"]
    existing.builtin_content_hash = _compute_builtin_content_hash(data)
    existing.version = data["version"]
    existing.locked_after_publish = True
    existing.rule_version = f"builtin-{data['version']}"
    existing.status = "active"


def ensure_builtin_questionnaires(db: Session) -> list[Questionnaire]:
    from ..models.task import AnswerRecord

    db.query(Questionnaire).filter(
        Questionnaire.is_builtin == True,
        Questionnaire.code.is_(None),
        Questionnaire.status == "active",
    ).update({"status": "inactive"}, synchronize_session=False)
    db.flush()

    created_or_existing: list[Questionnaire] = []
    for data in BUILTIN_QUESTIONNAIRES:
        content_hash = _compute_builtin_content_hash(data)
        existing = db.query(Questionnaire).filter(Questionnaire.code == data["code"]).first()
        if existing is None:
            existing = Questionnaire(code=data["code"], title=data["title"])
            db.add(existing)
            db.flush()

        needs_rebuild = (
            existing.version != data["version"]
            or len(existing.questions) != len(data["questions"])
            or (existing.builtin_content_hash or "") != content_hash
        )
        _refresh_questionnaire(existing, data)

        if needs_rebuild:
            # Check if any questions have answer records
            question_ids = [q.id for q in existing.questions]
            has_answers = False
            if question_ids:
                has_answers = db.query(AnswerRecord).filter(AnswerRecord.question_id.in_(question_ids)).first() is not None

            if has_answers:
                # Can't delete questions with answer records, just update metadata
                # Update existing questions' properties where possible
                existing_questions_by_code = {q.code: q for q in existing.questions}
                for idx, question_data in enumerate(data["questions"], start=1):
                    eq = existing_questions_by_code.get(question_data["code"])
                    if eq:
                        eq.title = question_data["title"]
                        eq.dimension = question_data.get("dimension", "")
                        eq.risk_tag = question_data.get("risk_tag", "")
                        eq.is_reverse = question_data.get("is_reverse", False)
                        eq.sort_order = idx
                db.flush()
            else:
                # Safe to delete and rebuild
                db.query(Option).filter(Option.question_id.in_(db.query(Question.id).filter(Question.questionnaire_id == existing.id))).delete(synchronize_session=False)
                db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == existing.id).delete(synchronize_session=False)
                db.query(Question).filter(Question.questionnaire_id == existing.id).delete(synchronize_session=False)
                db.flush()

                question_map: dict[str, Question] = {}
                for idx, question_data in enumerate(data["questions"], start=1):
                    question = Question(
                        questionnaire_id=existing.id,
                        code=question_data["code"],
                        title=question_data["title"],
                        description=question_data.get("description", ""),
                        type=question_data.get("type", "scale"),
                        required=question_data.get("required", True),
                        sort_order=idx,
                        dimension=question_data.get("dimension", ""),
                        risk_tag=question_data.get("risk_tag", ""),
                        is_reverse=question_data.get("is_reverse", False),
                        is_attention_check=question_data.get("is_attention_check", False),
                        attention_correct_answer=question_data.get("attention_correct_answer", ""),
                    )
                    db.add(question)
                    db.flush()
                    question_map[question_data["code"]] = question

                    for option_idx, option_data in enumerate(question_data.get("options", []), start=1):
                        db.add(
                            Option(
                                question_id=question.id,
                                content=option_data["content"],
                                score=option_data.get("score", 0),
                                sort_order=option_data.get("sort_order", option_idx),
                                is_risk_option=option_data.get("is_risk_option", False),
                            )
                        )

                for cg in data.get("contradiction_groups", []):
                    question_a = question_map.get(cg["question_a_code"])
                    question_b = question_map.get(cg["question_b_code"])
                    if question_a and question_b:
                        db.add(
                            ContradictionGroup(
                                questionnaire_id=existing.id,
                                question_a_id=question_a.id,
                                question_b_id=question_b.id,
                                relation_type=cg.get("relation_type", "opposite"),
                                max_score_diff=cg.get("max_score_diff", 3),
                                description=cg.get("description", ""),
                            )
                        )

        created_or_existing.append(existing)

    db.commit()
    for questionnaire in created_or_existing:
        db.refresh(questionnaire)
    return created_or_existing
