import json
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.questionnaire import Question, Option, ContradictionGroup, Questionnaire
from ..models.risk import ScoringResult, QualityAssessment, RiskAlert
from ..models.user import User
from ..utils.access_control import task_is_answerable, task_matches_student

tz = timezone(timedelta(hours=8))


def start_answer(db: Session, task_id: int, student_id: int) -> AnswerSheet:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    _ensure_task_fillable(task)
    student = db.query(User).filter(User.id == student_id).first()
    if not student or not task_matches_student(student, task):
        raise ValueError("任务不存在")

    existing = db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id, AnswerSheet.student_id == student_id).first()
    if existing:
        if existing.status == "submitted" and not task.allow_edit:
            raise ValueError("本次问卷已提交，不能重复提交")
        if existing.status == "submitted" and task.allow_edit:
            existing.status = "in_progress"
            existing.started_at = datetime.now(tz)
            existing.submitted_at = None
            db.commit()
            db.refresh(existing)
        return existing

    questions = db.query(Question).filter(Question.questionnaire_id == task.questionnaire_id).order_by(Question.sort_order).all()
    question_order = [q.id for q in questions]
    if task.shuffle_questions:
        random.shuffle(question_order)

    option_orders = {}
    if task.shuffle_options:
        for q in questions:
            if q.type in ("single_choice", "multi_choice"):
                opts = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
                opt_order = [o.id for o in opts]
                random.shuffle(opt_order)
                option_orders[str(q.id)] = opt_order

    sheet = AnswerSheet(
        school_id=student.school_id, class_id=student.class_id,
        task_id=task_id, student_id=student_id, questionnaire_id=task.questionnaire_id,
        question_order=question_order, option_orders=option_orders,
        status="in_progress", started_at=datetime.now(tz),
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return sheet


def _ensure_task_fillable(task: Task) -> None:
    if task.status in ("closed", "archived"):
        raise ValueError("任务已关闭")
    if task.status in ("draft", "pending"):
        raise ValueError("任务尚未开始")
    if task.status in ("ended", "expired"):
        raise ValueError("任务已截止")
    if not task_is_answerable(task):
        now = datetime.now()
        if task.start_time and task.start_time > now:
            raise ValueError("任务尚未开始")
        if task.end_time and task.end_time < now:
            raise ValueError("任务已截止")
        raise ValueError("任务尚未开始")


def _compute_display_index(sheet: AnswerSheet, question_id: int, answer_content: dict | None) -> int:
    """后端根据 option_orders 计算选项显示位置，不信任前端传入值。"""
    if not answer_content or not isinstance(answer_content, dict):
        return 0
    selected_id = answer_content.get("selected_option_id")
    if not selected_id:
        selected_ids = answer_content.get("selected_option_ids") or []
        selected_id = selected_ids[0] if selected_ids else None
    if not selected_id:
        return 0
    option_orders = sheet.option_orders or {}
    order_list = option_orders.get(str(question_id)) or []
    if not order_list:
        return 0
    try:
        return order_list.index(int(selected_id))
    except (ValueError, TypeError):
        return 0


def save_progress(db: Session, sheet_id: int, answers: list[dict]):
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet or sheet.status != "in_progress":
        raise ValueError("答卷状态不允许保存")
    task = db.query(Task).filter(Task.id == sheet.task_id).first()
    if task:
        _ensure_task_fillable(task)

    for ans in answers:
        question_id = ans.get("question_id")
        content = ans.get("answer_content")
        duration = ans.get("duration_seconds", 0)
        displayed_order = ans.get("displayed_order", 0)
        # 后端计算可信显示位置
        display_idx = _compute_display_index(sheet, question_id, content)
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            continue

        existing = db.query(AnswerRecord).filter(
            AnswerRecord.answer_sheet_id == sheet_id,
            AnswerRecord.question_id == question_id,
        ).first()

        if existing:
            existing.answer_content = content
            existing.duration_seconds = duration
            existing.selected_display_index = display_idx
        else:
            db.add(AnswerRecord(
                answer_sheet_id=sheet_id, question_id=question_id,
                question_type=question.type, answer_content=content,
                duration_seconds=duration, displayed_order=displayed_order,
                selected_display_index=display_idx,
            ))
    db.commit()


def submit_answer(db: Session, sheet_id: int) -> dict:
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet:
        raise ValueError("答卷不存在")
    if sheet.status != "in_progress":
        raise ValueError("答卷状态不允许提交")
    task = db.query(Task).filter(Task.id == sheet.task_id).first()
    if task:
        _ensure_task_fillable(task)
    _validate_required_answers(db, sheet)

    sheet.status = "submitted"
    now = datetime.now(tz)
    sheet.submitted_at = now
    if sheet.started_at:
        started = sheet.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=tz)
        sheet.total_duration_seconds = int((now - started).total_seconds())
    db.commit()

    scoring = calculate_scores(db, sheet_id)
    quality = calculate_quality(db, sheet_id)
    risk = check_risk_alerts(db, sheet_id)

    db.commit()
    return {"scoring": scoring, "quality": quality, "risk": risk}


def _validate_required_answers(db: Session, sheet: AnswerSheet) -> None:
    questions = db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id, Question.required == True).all()
    records = {
        r.question_id: r.answer_content
        for r in db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet.id).all()
    }
    missing = []
    for question in questions:
        answer = records.get(question.id)
        if answer in (None, "", [], {}):
            missing.append(question.title[:30])
        elif isinstance(answer, dict):
            values = [v for v in answer.values() if v not in (None, "", [], {})]
            if not values:
                missing.append(question.title[:30])
    if missing:
        raise ValueError(f"请完成必填题：{', '.join(missing[:3])}")


def calculate_scores(db: Session, sheet_id: int) -> dict:
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet:
        return {}

    questionnaire = db.query(Questionnaire).filter(Questionnaire.id == sheet.questionnaire_id).first()
    records = db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet_id).all()
    questions = {q.id: q for q in db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id).all()}
    options_by_question = {
        question_id: db.query(Option).filter(Option.question_id == question_id).order_by(Option.sort_order).all()
        for question_id in questions.keys()
    }
    scoring_rule = questionnaire.scoring_rule or {} if questionnaire else {}
    risk_rules = questionnaire.risk_rules or {} if questionnaire else {}

    total_score = 0.0
    total_max_score = 0.0
    dimension_scores: dict[str, float] = {}
    dimension_max_scores: dict[str, float] = {}
    triggered_rules = []
    risk_types: dict[str, int] = {}  # tag -> count of risk options selected
    risk_type_labels: dict[str, str] = {}

    for record in records:
        question = questions.get(record.question_id)
        if not question:
            continue

        options = options_by_question.get(question.id, [])
        score, question_max_score, selected_risk_tags, question_rules = _score_record(question, record.answer_content, options)
        record.score = score
        triggered_rules.extend(question_rules)

        if question.risk_threshold is not None and score >= question.risk_threshold and question.risk_tag:
            selected_risk_tags.add(question.risk_tag)
            triggered_rules.append({
                "type": "question_threshold",
                "question_id": question.id,
                "risk_tag": question.risk_tag,
                "score": score,
                "threshold": question.risk_threshold,
            })

        for risk_tag in selected_risk_tags:
            risk_types[risk_tag] = risk_types.get(risk_tag, 0) + 1

        if not _should_include_in_score(question, scoring_rule):
            continue

        total_score += score
        total_max_score += question_max_score

        dim = question.dimension or "general"
        dimension_scores[dim] = dimension_scores.get(dim, 0.0) + score
        dimension_max_scores[dim] = dimension_max_scores.get(dim, 0.0) + question_max_score

    total_score_pct = round((total_score / total_max_score) * 100, 2) if total_max_score else 0.0
    dimension_breakdown = _build_dimension_breakdown(questionnaire, dimension_scores, dimension_max_scores)

    risk_level, risk_type_labels, risk_rule_triggers = _resolve_risk_level(
        db=db,
        questionnaire=questionnaire,
        total_score=total_score,
        total_max_score=total_max_score,
        total_score_pct=total_score_pct,
        dimension_breakdown=dimension_breakdown,
        risk_types=risk_types,
    )
    triggered_rules.extend(risk_rule_triggers)

    # 保存评分结果
    existing = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet_id).first()
    if existing:
        db.delete(existing)
        db.flush()
    dimension_analysis = _generate_dimension_analysis(dimension_breakdown)
    risk_type = _risk_types_chinese(risk_types, risk_type_labels)
    db.add(ScoringResult(
        answer_sheet_id=sheet_id, total_score=total_score, dimension_scores=dimension_scores,
        risk_level=risk_level, risk_type=risk_type,
        risk_description=_generate_risk_description(questionnaire, risk_level, risk_types),
        triggered_rules=_dedupe_rules(triggered_rules + dimension_analysis),
    ))
    db.flush()

    return {
        "total_score": total_score,
        "total_max_score": total_max_score,
        "total_score_pct": total_score_pct,
        "dimension_scores": dimension_scores,
        "dimension_breakdown": dimension_breakdown,
        "risk_level": risk_level,
        "risk_type": risk_type,
    }

def _should_include_in_score(question: Question, scoring_rule: dict) -> bool:
    score_types = set(scoring_rule.get("score_types") or ["single_choice", "multi_choice", "scale", "true_false"])
    exclude_types = set(scoring_rule.get("exclude_types") or ["fill_blank", "short_answer"])
    if question.type in exclude_types:
        return False
    if scoring_rule.get("exclude_attention_check", True) and question.is_attention_check:
        return False
    return question.type in score_types


def _score_record(question: Question, answer, options: list[Option]) -> tuple[float, float, set[str], list[dict]]:
    option_map = {opt.id: opt for opt in options}
    option_scores = [opt.score for opt in options] or [0]
    min_score = min(option_scores)
    max_score = max(option_scores)
    score = 0.0
    triggered_rules: list[dict] = []
    risk_tags: set[str] = set()

    if question.type in ("single_choice", "scale", "true_false"):
        selected_option_id = answer.get("selected_option_id") if isinstance(answer, dict) else None
        selected_option = option_map.get(selected_option_id)
        if selected_option is not None:
            score = selected_option.score
            if selected_option.is_risk_option and question.risk_tag:
                risk_tags.add(question.risk_tag)
                triggered_rules.append({"type": "sensitive_option", "question_id": question.id, "option_id": selected_option.id, "risk_tag": question.risk_tag})
        elif question.type == "true_false" and isinstance(answer, dict):
            truthy = str(answer.get("value", "")).lower() in {"true", "1", "yes"}
            score = max_score if truthy else min_score
    elif question.type == "multi_choice":
        selected_ids = answer.get("selected_option_ids", []) if isinstance(answer, dict) else []
        selected_options = [option_map[option_id] for option_id in selected_ids if option_id in option_map]
        score = float(sum(option.score for option in selected_options))
        for option in selected_options:
            if option.is_risk_option and question.risk_tag:
                risk_tags.add(question.risk_tag)
                triggered_rules.append({"type": "sensitive_option", "question_id": question.id, "option_id": option.id, "risk_tag": question.risk_tag})
        max_score = float(sum(max(option.score, 0) for option in options))
    else:
        max_score = 0.0

    if question.is_reverse and options:
        score = max_score + min_score - score

    if question.type != "multi_choice":
        max_score = float(max(option_scores) if option_scores else 0)

    return float(score), float(max_score), risk_tags, triggered_rules


def _build_dimension_breakdown(questionnaire: Questionnaire | None, dimension_scores: dict[str, float], dimension_max_scores: dict[str, float]) -> dict[str, dict]:
    dimension_labels = {
        item.get("code"): item.get("title")
        for item in ((questionnaire.dimensions or []) if questionnaire else [])
        if isinstance(item, dict) and item.get("code")
    }
    breakdown: dict[str, dict] = {}
    for dimension, score in dimension_scores.items():
        max_score = dimension_max_scores.get(dimension, 0.0)
        breakdown[dimension] = {
            "label": dimension_labels.get(dimension, dimension),
            "score": score,
            "max_score": max_score,
            "pct": round((score / max_score) * 100, 2) if max_score else 0.0,
        }
    return breakdown


def _resolve_risk_level(
    db: Session,
    questionnaire: Questionnaire | None,
    total_score: float,
    total_max_score: float,
    total_score_pct: float,
    dimension_breakdown: dict[str, dict],
    risk_types: dict[str, int],
) -> tuple[str, dict[str, str], list[dict]]:
    risk_rules = questionnaire.risk_rules or {} if questionnaire else {}
    triggered_rules: list[dict] = []
    risk_level = "low"
    risk_type_labels: dict[str, str] = {}

    total_ranges = risk_rules.get("total_score_ranges") or []
    total_pct_ranges = risk_rules.get("total_pct_ranges") or []
    dimension_pct_rules = risk_rules.get("dimension_pct_rules") or []
    risk_tag_rules = risk_rules.get("risk_tag_rules") or {}

    if total_ranges:
        risk_level = _match_range_level(total_score, total_ranges, "low")
    elif total_pct_ranges:
        risk_level = _match_range_level(total_score_pct, total_pct_ranges, "low")
    else:
        risk_level = _resolve_default_risk_level(db, total_score_pct)

    for rule in dimension_pct_rules:
        dimension = rule.get("dimension")
        min_pct = float(rule.get("min_pct", 0))
        current = dimension_breakdown.get(dimension)
        if current and current.get("pct", 0) >= min_pct:
            rule_level = rule.get("level", "medium")
            risk_level = _max_risk(risk_level, rule_level)
            triggered_rules.append({
                "type": "dimension_threshold",
                "dimension": dimension,
                "min_pct": min_pct,
                "actual_pct": current.get("pct", 0),
                "level": rule_level,
                "rule_version": questionnaire.rule_version if questionnaire else "default",
            })

    for risk_tag, tag_count in sorted(risk_types.items()):
        tag_rule = risk_tag_rules.get(risk_tag) or {}
        if tag_rule:
            min_count = tag_rule.get("min_count", 1)
            if tag_count < min_count:
                continue  # Not enough risk selections to trigger
            rule_level = tag_rule.get("level", "high")
            risk_level = _max_risk(risk_level, rule_level)
            if tag_rule.get("type_label"):
                risk_type_labels[risk_tag] = tag_rule["type_label"]
            triggered_rules.append({
                "type": "risk_tag_rule",
                "risk_tag": risk_tag,
                "level": rule_level,
                "count": tag_count,
                "min_count": min_count,
                "label": tag_rule.get("type_label", ""),
                "rule_version": questionnaire.rule_version if questionnaire else "default",
            })

    return risk_level, risk_type_labels, triggered_rules


def _resolve_default_risk_level(db: Session, total_score_pct: float) -> str:
    from ..models.system_config import SystemConfig

    config = db.query(SystemConfig).filter(SystemConfig.config_key == "risk_levels", SystemConfig.school_id.is_(None)).first()
    if not config or not config.config_value:
        return "low"
    levels = json.loads(config.config_value)
    for level_name, level_cfg in levels.items():
        min_score = float(level_cfg.get("min_score", level_cfg.get("min", 0)))
        max_score = float(level_cfg.get("max_score", level_cfg.get("max", 100)))
        if min_score <= total_score_pct <= max_score:
            return level_name
    return "low"


def _match_range_level(value: float, ranges: list[dict], default_level: str = "low") -> str:
    for item in ranges:
        min_value = float(item.get("min", 0))
        max_value = float(item.get("max", value))
        if min_value <= value <= max_value:
            return item.get("level", default_level)
    return default_level


def _risk_types_chinese(risk_types: dict | set, risk_type_labels: dict[str, str] | None = None) -> str:
    tag_map = {
        "mental_pressure": "心理压力关注信号", "bullying": "校园欺凌关注信号",
        "internet_addiction": "网络使用关注信号", "family_relationship": "家庭关系关注信号",
        "interpersonal": "人际关系关注信号", "academic_pressure": "学业压力关注信号",
        "safety_awareness": "安全意识关注信号", "self_safety": "自我安全关注信号",
        "emotion": "情绪关注信号", "sleep": "睡眠关注信号", "general": "综合关注信号",
        "internet_use": "网络使用关注信号", "family_support": "家庭支持关注信号",
        "campus_safety": "校园安全关注信号",
    }
    labels = []
    for risk_tag in sorted(risk_types):
        if risk_type_labels and risk_type_labels.get(risk_tag):
            labels.append(risk_type_labels[risk_tag])
        else:
            labels.append(tag_map.get(risk_tag, risk_tag))
    return ",".join(dict.fromkeys(labels)) if labels else ""


def _generate_risk_description(questionnaire: Questionnaire | None, risk_level: str, risk_types: dict | set) -> str:
    risk_rules = questionnaire.risk_rules or {} if questionnaire else {}
    messages = risk_rules.get("messages") or {}
    if risk_level in messages:
        return messages[risk_level]
    descriptions = {
        "low": "测评结果显示该学生可能需要额外的关爱和支持，建议班主任或心理老师在日常教育中给予更多关注和帮助。",
        "medium": "测评结果显示该学生存在一定的风险信号，建议班主任适时了解学生近期学习、生活和情绪状态，并结合日常观察进行核实。",
        "high": "测评结果显示该学生存在较为明显的风险信号，建议心理老师或班主任在近期进行一对一沟通，结合日常观察、班级情况和家庭沟通综合研判，并形成持续跟进记录。",
        "urgent": "测评结果显示该学生存在需要及时关注的严重信号，建议学校按既有学生关怀和安全支持流程尽快跟进，必要时联系监护人并寻求专业支持。",
    }
    return descriptions.get(risk_level, "")


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def _max_risk(left: str, right: str) -> str:
    return left if RISK_ORDER.get(left, 0) >= RISK_ORDER.get(right, 0) else right


def _dedupe_rules(rules: list) -> list:
    seen = set()
    deduped = []
    for rule in rules:
        key = json.dumps(rule, ensure_ascii=False, sort_keys=True) if isinstance(rule, dict) else str(rule)
        if key not in seen:
            seen.add(key)
            deduped.append(rule)
    return deduped


def _generate_dimension_analysis(dimension_breakdown: dict[str, dict]) -> list:
    analyses = []
    for dimension, item in dimension_breakdown.items():
        ratio = item.get("pct", 0)
        label = item.get("label", dimension)
        if ratio >= 75:
            analyses.append({"dimension": dimension, "label": label, "level": "偏高", "ratio": round(ratio), "suggestion": f"「{label}」维度关注信号相对更集中，建议结合班级观察和学生访谈进一步复核。"})
        elif ratio >= 45:
            analyses.append({"dimension": dimension, "label": label, "level": "中等", "ratio": round(ratio), "suggestion": f"「{label}」维度出现一定关注信号，建议保持关注并结合日常表现综合判断。"})
    return sorted(analyses, key=lambda x: x["ratio"], reverse=True)


def calculate_quality(db: Session, sheet_id: int) -> dict:
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet:
        return {}

    records = db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet_id).all()
    questions = {q.id: q for q in db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id).all()}

    total_q = len(records)
    total_time = sheet.total_duration_seconds or 0

    # 按题型的最低时间阈值（秒）— 放宽阈值
    type_thresholds = {"true_false": 1, "single_choice": 1, "scale": 1, "multi_choice": 2, "fill_blank": 5, "short_answer": 5}
    # 每道题的合理最低时间
    min_time_per_q = 0
    for r in records:
        q = questions.get(r.question_id)
        min_time_per_q += type_thresholds.get(q.type, 2) if q else 2

    # 1. 快速作答检测 - 按题型分别判断
    fast_count = 0
    for r in records:
        q = questions.get(r.question_id)
        threshold = type_thresholds.get(q.type, 2) if q else 2
        if r.duration_seconds < threshold:
            fast_count += 1

    max_consecutive_fast = 0
    current_fast = 0
    for r in sorted(records, key=lambda x: x.displayed_order):
        q = questions.get(r.question_id)
        threshold = type_thresholds.get(q.type, 1) if q else 1
        if r.duration_seconds < threshold:
            current_fast += 1
            max_consecutive_fast = max(max_consecutive_fast, current_fast)
        else:
            current_fast = 0

    # 2. 连续同选项检测（按选项ID而非分值）
    answers_list: list[str | None] = []
    selected_option_keys: list[str] = []
    display_positions: list[int] = []
    for r in sorted(records, key=lambda x: x.displayed_order):
        ans = r.answer_content
        if isinstance(ans, dict):
            if "selected_option_id" in ans and ans["selected_option_id"] is not None:
                key = str(ans["selected_option_id"])
                answers_list.append(key)
                selected_option_keys.append(key)
            elif "selected_option_ids" in ans and ans["selected_option_ids"] is not None:
                key = str(sorted(ans["selected_option_ids"]))
                answers_list.append(key)
                selected_option_keys.append(key)
            elif "value" in ans and ans["value"] is not None:
                answers_list.append(str(ans["value"]))
            else:
                answers_list.append(None)
        else:
            answers_list.append(str(ans) if ans is not None else None)

        if getattr(r, "selected_display_index", 0):
            display_positions.append(r.selected_display_index)

    max_consecutive_same = 0
    if answers_list:
        current_same = 1
        for i in range(1, len(answers_list)):
            if answers_list[i] is not None and answers_list[i] == answers_list[i - 1]:
                current_same += 1
            else:
                max_consecutive_same = max(max_consecutive_same, current_same)
                current_same = 1
        max_consecutive_same = max(max_consecutive_same, current_same)

    # 3. 集中度统计
    score_counts: dict[float, int] = {}
    scores_list = [r.score for r in sorted(records, key=lambda x: x.displayed_order)]
    for s in scores_list:
        score_counts[s] = score_counts.get(s, 0) + 1
    same_score_ratio = max(score_counts.values()) / max(total_q, 1) if score_counts else 0

    option_counts: dict[str, int] = {}
    for key in selected_option_keys:
        option_counts[key] = option_counts.get(key, 0) + 1
    same_option_ratio = max(option_counts.values()) / max(total_q, 1) if option_counts else 0

    display_index_counts: dict[int, int] = {}
    for idx in display_positions:
        display_index_counts[idx] = display_index_counts.get(idx, 0) + 1
    same_display_position_ratio = max(display_index_counts.values()) / max(total_q, 1) if display_index_counts else 0

    # 4. 注意力检测
    attention_passed = True
    attention_details = []
    for record in records:
        q = questions.get(record.question_id)
        if q and q.is_attention_check:
            correct = q.attention_correct_answer
            answer = record.answer_content
            if isinstance(answer, dict):
                opt_id = answer.get("selected_option_id")
                if opt_id:
                    opt = db.query(Option).filter(Option.id == opt_id).first()
                    passed = (opt.content == correct) if opt else False
                    attention_passed = attention_passed and passed
                    attention_details.append({"question_id": q.id, "passed": passed, "answer": opt.content if opt else "", "expected": correct})

    # 5. 矛盾题检测
    contradiction_count = 0
    contradiction_details = []
    cgs = db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == sheet.questionnaire_id).all()
    for cg in cgs:
        ra = next((r for r in records if r.question_id == cg.question_a_id), None)
        rb = next((r for r in records if r.question_id == cg.question_b_id), None)
        if ra and rb:
            score_diff = abs(ra.score - rb.score)
            if cg.relation_type == "opposite" and score_diff < cg.max_score_diff:
                contradiction_count += 1
                contradiction_details.append({"group_id": cg.id, "score_a": ra.score, "score_b": rb.score, "diff": score_diff})

    # 6. 规律作答检测（ABAB / ABCDABCD / AABB等模式）— 需要更长序列
    pattern_detected = False
    pattern_detail = ""
    if len(scores_list) >= 6:
        # 检测ABAB模式（需要至少6题连续）
        consecutive_pattern = 0
        for i in range(len(scores_list) - 3):
            if scores_list[i] == scores_list[i + 2] and scores_list[i + 1] == scores_list[i + 3] and scores_list[i] != scores_list[i + 1]:
                consecutive_pattern += 1
            else:
                consecutive_pattern = 0
            if consecutive_pattern >= 3:  # 连续3组ABAB才算
                pattern_detected = True; pattern_detail = "ABAB重复模式"
                break
        # 检测ABCDABCD模式（长度为4的重复，需要至少2轮）
        if not pattern_detected and len(scores_list) >= 12:
            for i in range(len(scores_list) - 11):
                seg1 = scores_list[i:i+4]
                seg2 = scores_list[i+4:i+8]
                seg3 = scores_list[i+8:i+12]
                if seg1 == seg2 == seg3 and len(set(seg1)) > 2:
                    pattern_detected = True; pattern_detail = "四题段重复模式"
                    break

    # 7. 综合质量评分（加权计算，满分100）
    quality_score = 100.0
    deductions = []

    if total_q > 0:
        # 总时长过短（权重25%）
        if total_time < min_time_per_q * 0.3:
            quality_score -= 25; deductions.append("总答题时间严重不足")
        elif total_time < min_time_per_q * 0.6:
            quality_score -= 10; deductions.append("总答题时间偏短")

        # 快速作答题目过多（权重15%）
        fast_ratio = fast_count / total_q
        if fast_ratio > 0.7:
            quality_score -= 15; deductions.append(f"快速作答题目过多（{fast_count}/{total_q}）")
        elif fast_ratio > 0.5:
            quality_score -= 8; deductions.append(f"部分题目作答过快（{fast_count}/{total_q}）")

        # 连续同选项（权重15%）
        if max_consecutive_same >= 12:
            quality_score -= 15; deductions.append(f"连续{max_consecutive_same}题选同一选项")
        elif max_consecutive_same >= 8:
            quality_score -= 8; deductions.append(f"连续{max_consecutive_same}题选同一选项")

        # 选项分布异常（权重10%）
        if same_option_ratio > 0.9:
            quality_score -= 10; deductions.append("某一选项占比过高")
        elif same_display_position_ratio > 0.9:
            quality_score -= 10; deductions.append("某一显示位置点击占比过高")
        elif same_score_ratio > 0.9:
            quality_score -= 10; deductions.append("某一得分占比过高")

        # 注意力检测失败（权重15%）
        if not attention_passed:
            quality_score -= 15; deductions.append("注意力检测未通过")

        # 矛盾题（权重10%）
        if contradiction_count >= 4:
            quality_score -= 15; deductions.append(f"存在{contradiction_count}组矛盾答案")
        elif contradiction_count >= 2:
            quality_score -= 8; deductions.append(f"存在{contradiction_count}组矛盾答案")
        elif contradiction_count >= 1:
            quality_score -= 4; deductions.append(f"存在{contradiction_count}组矛盾答案")

        # 规律作答（权重10%）— 需要更长序列才触发
        if pattern_detected:
            quality_score -= 10; deductions.append(f"检测到规律作答（{pattern_detail}）")

    quality_score = max(quality_score, 0)

    if quality_score >= 70:
        quality_level = "normal"
        validity = "valid"
    elif quality_score >= 50:
        quality_level = "mild_anomaly"
        validity = "basically_valid"
    elif quality_score >= 30:
        quality_level = "moderate_anomaly"
        validity = "questionable"
    else:
        quality_level = "severe_anomaly"
        validity = "not_recommended"

    suggest_retest = quality_level == "severe_anomaly"

    existing = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == sheet_id).first()
    if existing:
        db.delete(existing)
    db.add(QualityAssessment(
        answer_sheet_id=sheet_id, quality_level=quality_level, validity=validity,
        quality_score=quality_score, total_duration_seconds=total_time,
        fast_question_count=fast_count, contradiction_count=contradiction_count,
        contradiction_details=contradiction_details, reverse_consistency_score=100,
        attention_passed=attention_passed, attention_details=attention_details,
        max_consecutive_same=max_consecutive_same, same_option_ratio=same_option_ratio,
        pattern_detected=pattern_detected, suggest_retest=suggest_retest,
        details={"deductions": deductions, "fast_ratio": fast_count/max(total_q,1),
                 "max_consecutive_fast": max_consecutive_fast, "pattern_detail": pattern_detail,
                 "min_expected_time": min_time_per_q, "same_score_ratio": same_score_ratio,
                 "same_option_ratio": same_option_ratio, "same_display_position_ratio": same_display_position_ratio},
    ))

    return {
        "quality_level": quality_level,
        "quality_score": quality_score,
        "validity": validity,
        "suggest_retest": suggest_retest,
        "deductions": deductions,
        "same_score_ratio": same_score_ratio,
        "same_option_ratio": same_option_ratio,
        "same_display_position_ratio": same_display_position_ratio,
    }


def check_risk_alerts(db: Session, sheet_id: int) -> dict:
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    scoring = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet_id).first()
    if not sheet or not scoring:
        return {}

    if scoring.risk_level in ("medium", "high", "urgent"):
        existing = db.query(RiskAlert).filter(RiskAlert.answer_sheet_id == sheet_id).first()
        if not existing:
            student = db.query(User).filter(User.id == sheet.student_id).first()
            task = db.query(Task).filter(Task.id == sheet.task_id).first()
            db.add(RiskAlert(
                school_id=task.school_id if task else student.school_id if student else 1,
                student_id=sheet.student_id, answer_sheet_id=sheet_id, task_id=sheet.task_id,
                risk_level=scoring.risk_level, risk_type=scoring.risk_type,
                trigger_method="total_score", trigger_detail=scoring.triggered_rules,
                status="pending", source_rule_version="v1",
            ))
        elif RISK_ORDER.get(scoring.risk_level, 0) > RISK_ORDER.get(existing.risk_level, 0):
            existing.risk_level = scoring.risk_level
            existing.risk_type = scoring.risk_type
            existing.trigger_detail = scoring.triggered_rules
            existing.source_rule_version = "v1"
        return {"alert_created": True, "risk_level": scoring.risk_level}

    return {"alert_created": False}
