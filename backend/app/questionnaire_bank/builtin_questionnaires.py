from copy import deepcopy

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
        "情绪状态参考性筛查问卷（9题）",
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
                {"min": 0, "max": 4, "level": "low"},
                {"min": 5, "max": 9, "level": "medium"},
                {"min": 10, "max": 14, "level": "medium"},
                {"min": 15, "max": 19, "level": "high"},
                {"min": 20, "max": 27, "level": "urgent"},
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
        "焦虑压力参考性筛查问卷（7题）",
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
                {"min": 0, "max": 4, "level": "low"},
                {"min": 5, "max": 9, "level": "medium"},
                {"min": 10, "max": 14, "level": "high"},
                {"min": 15, "max": 21, "level": "urgent"},
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
        "睡眠状态参考性筛查问卷",
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
    existing.version = data["version"]
    existing.locked_after_publish = True
    existing.rule_version = f"builtin-{data['version']}"
    existing.status = "active"


def ensure_builtin_questionnaires(db: Session) -> list[Questionnaire]:
    db.query(Questionnaire).filter(
        Questionnaire.is_builtin == True,
        Questionnaire.code.is_(None),
        Questionnaire.status == "active",
    ).update({"status": "inactive"}, synchronize_session=False)
    db.flush()

    created_or_existing: list[Questionnaire] = []
    for data in BUILTIN_QUESTIONNAIRES:
        existing = db.query(Questionnaire).filter(Questionnaire.code == data["code"]).first()
        if existing is None:
            existing = Questionnaire(code=data["code"], title=data["title"])
            db.add(existing)
            db.flush()

        needs_rebuild = existing.version != data["version"] or len(existing.questions) != len(data["questions"])
        _refresh_questionnaire(existing, data)

        if needs_rebuild:
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
