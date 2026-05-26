import json
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.questionnaire import Question, Option, ContradictionGroup, Questionnaire
from ..models.risk import ScoringResult, QualityAssessment, RiskAlert
from ..models.user import User
from ..utils.access_control import task_matches_student

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
    now = datetime.now()
    if task.status in ("closed", "archived"):
        raise ValueError("任务已关闭")
    if task.status in ("draft", "not_started", "pending"):
        raise ValueError("任务尚未开始")
    if task.status in ("ended", "expired"):
        raise ValueError("任务已截止")
    if task.start_time and task.start_time > now:
        raise ValueError("任务尚未开始")
    if task.end_time and task.end_time < now:
        raise ValueError("任务已截止")


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
        else:
            db.add(AnswerRecord(
                answer_sheet_id=sheet_id, question_id=question_id,
                question_type=question.type, answer_content=content,
                duration_seconds=duration, displayed_order=displayed_order,
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
    sheet.submitted_at = datetime.now(tz)
    if sheet.started_at:
        sheet.total_duration_seconds = int((sheet.submitted_at - sheet.started_at).total_seconds())
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

    records = db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet_id).all()
    questions = {q.id: q for q in db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id).all()}

    total_score = 0.0
    dimension_scores = {}
    triggered_rules = []
    risk_types = set()
    max_risk_level = "low"

    for record in records:
        question = questions.get(record.question_id)
        if not question:
            continue

        answer = record.answer_content
        score = 0

        if question.type in ("single_choice", "scale"):
            if isinstance(answer, dict):
                option_id = answer.get("selected_option_id")
                option = db.query(Option).filter(Option.id == option_id).first()
                if option:
                    score = option.score
                    if option.is_risk_option:
                        risk_types.add(question.risk_tag or "general")
                        triggered_rules.append({"type": "sensitive_option", "question_id": question.id, "option_id": option_id})
                        max_risk_level = _max_risk(max_risk_level, "high")

        elif question.type == "multi_choice":
            if isinstance(answer, dict):
                selected_ids = answer.get("selected_option_ids", [])
                for oid in selected_ids:
                    option = db.query(Option).filter(Option.id == oid).first()
                    if option:
                        score += option.score
                        if option.is_risk_option:
                            risk_types.add(question.risk_tag or "general")
                            triggered_rules.append({"type": "sensitive_option", "question_id": question.id, "option_id": oid})
                            max_risk_level = _max_risk(max_risk_level, "high")

        elif question.type == "true_false":
            if isinstance(answer, dict):
                score = 5 if answer.get("value") == "true" else 0

        # 反向计分
        if question.is_reverse:
            max_opt_score = max((o.score for o in db.query(Option).filter(Option.question_id == question.id).all()), default=5)
            score = max_opt_score - score

        record.score = score
        total_score += score

        dim = question.dimension or "general"
        dimension_scores[dim] = dimension_scores.get(dim, 0) + score

    # 计算每题理论最高分（根据选项配置），用于归一化到百分制
    max_score_per_q = 4  # 默认最高分
    if questions:
        sample_q = next(iter(questions.values()))
        sample_opts = db.query(Option).filter(Option.question_id == sample_q.id).all()
        if sample_opts:
            opt_scores = [o.score for o in sample_opts]
            max_score_per_q = max(opt_scores) if opt_scores else 4

    # 判定风险等级
    risk_level = "low"
    q_count = len(records)

    # 读取系统配置中的阈值，将平均分转换为百分制
    from ..models.system_config import SystemConfig
    config = db.query(SystemConfig).filter(SystemConfig.config_key == "risk_levels", SystemConfig.school_id.is_(None)).first()
    if config:
        levels = json.loads(config.config_value)
        avg_score_pct = (total_score / max(q_count * max_score_per_q, 1)) * 100
        for level_name, level_cfg in levels.items():
            min_score = level_cfg.get("min_score", level_cfg.get("min", 0))
            max_score = level_cfg.get("max_score", level_cfg.get("max", 100))
            if min_score <= avg_score_pct <= max_score:
                risk_level = level_name
                break
    risk_level = _max_risk(risk_level, max_risk_level)

    for dim, dim_score in dimension_scores.items():
        dim_questions = [q for q in questions.values() if (q.dimension or "general") == dim]
        dim_max = sum(max((o.score for o in db.query(Option).filter(Option.question_id == q.id).all()), default=max_score_per_q) for q in dim_questions)
        if dim_max and (dim_score / dim_max) * 100 >= 75:
            risk_level = _max_risk(risk_level, "high")
            triggered_rules.append({"type": "dimension_threshold", "dimension": dim, "score": dim_score, "rule_version": "v1"})

    # 生成维度分析
    dim_analysis = _generate_dimension_analysis(dimension_scores, total_score, q_count, max_score_per_q)

    # 保存评分结果
    existing = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet_id).first()
    if existing:
        db.delete(existing)
    db.add(ScoringResult(
        answer_sheet_id=sheet_id, total_score=total_score, dimension_scores=dimension_scores,
        risk_level=risk_level, risk_type=_risk_types_chinese(risk_types),
        risk_description=_generate_risk_description(risk_level, risk_types),
        triggered_rules=_dedupe_rules(triggered_rules + dim_analysis),
    ))

    return {"total_score": total_score, "dimension_scores": dimension_scores, "risk_level": risk_level}


def _risk_types_chinese(risk_types: set) -> str:
    tag_map = {
        "mental_pressure": "心理压力关注信号", "bullying": "校园欺凌关注信号",
        "internet_addiction": "网络使用关注信号", "family_relationship": "家庭关系关注信号",
        "interpersonal": "人际关系关注信号", "academic_pressure": "学业压力关注信号",
        "safety_awareness": "安全意识关注信号", "self_safety": "自我安全关注信号",
        "emotion": "情绪关注信号", "sleep": "睡眠关注信号", "general": "综合关注信号",
    }
    return ",".join(tag_map.get(t, t) for t in risk_types) if risk_types else ""


def _generate_risk_description(risk_level: str, risk_types: set) -> str:
    descriptions = {
        "low": "测评结果暂未发现明显关注信号，建议保持日常关怀和常规教育支持。",
        "medium": "测评结果出现一定关注信号，建议班主任或心理老师适时了解学生近期学习、生活和情绪状态，并结合日常观察进行复核。",
        "high": "测评结果出现较明显关注信号，建议心理老师或班主任在近期进行一对一沟通，结合日常观察、班级情况和家庭沟通综合研判，并形成持续跟进记录。",
        "urgent": "测评结果出现需要及时关注的信号，建议学校按既有学生关怀和安全支持流程尽快跟进，必要时联系监护人并寻求专业支持。",
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


def _generate_dimension_analysis(dimension_scores: dict, total_score: float, question_count: int, max_score_per_q: int = 4) -> list:
    """根据各维度得分生成详细分析"""
    dim_labels = {
        "emotion": "情绪状态", "sleep": "睡眠质量", "academic_pressure": "学习压力",
        "interpersonal": "人际关系", "family_support": "家庭支持",
        "campus_safety": "校园安全", "internet_use": "网络使用", "self_safety": "自我安全"
    }
    analyses = []
    for dim, score in dimension_scores.items():
        label = dim_labels.get(dim, dim)
        max_score = question_count * max_score_per_q
        ratio = score / max(max_score, 1)
        if ratio > 0.6:
            analyses.append({"dimension": dim, "label": label, "level": "偏高", "ratio": round(ratio * 100),
                             "suggestion": f"「{label}」维度得分偏高，建议教师重点关注该学生在此方面的状况，必要时进行个别访谈。"})
        elif ratio > 0.4:
            analyses.append({"dimension": dim, "label": label, "level": "中等", "ratio": round(ratio * 100),
                             "suggestion": f"「{label}」维度处于中等水平，建议保持关注。"})
    return sorted(analyses, key=lambda x: x["ratio"], reverse=True)


def calculate_quality(db: Session, sheet_id: int) -> dict:
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet:
        return {}

    records = db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet_id).all()
    questions = {q.id: q for q in db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id).all()}

    total_q = len(records)
    total_time = sheet.total_duration_seconds or 0

    # 按题型的最低时间阈值（秒）
    type_thresholds = {"true_false": 1, "single_choice": 2, "scale": 2, "multi_choice": 4, "fill_blank": 8, "short_answer": 8}
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

    # 2. 连续同选项检测（按答案内容而非分值）
    answers_list = []
    for r in sorted(records, key=lambda x: x.displayed_order):
        ans = r.answer_content
        if isinstance(ans, dict):
            # 获取选项ID：单选题用selected_option_id，多选题用selected_option_ids
            val = ans.get("selected_option_id") or ans.get("selected_option_ids") or ans.get("value")
            answers_list.append(str(val) if val is not None else None)
        else:
            answers_list.append(str(ans) if ans is not None else None)

    max_consecutive_same = 0
    current_same = 1
    for i in range(1, len(answers_list)):
        if answers_list[i] == answers_list[i - 1]:
            current_same += 1
        else:
            max_consecutive_same = max(max_consecutive_same, current_same)
            current_same = 1
    max_consecutive_same = max(max_consecutive_same, current_same)

    # 3. 选项分布
    score_counts = {}
    scores_list = [r.score for r in sorted(records, key=lambda x: x.displayed_order)]
    for s in scores_list:
        score_counts[s] = score_counts.get(s, 0) + 1
    same_option_ratio = max(score_counts.values()) / max(total_q, 1) if score_counts else 0

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

    # 6. 规律作答检测（ABAB / ABCDABCD / AABB等模式）
    pattern_detected = False
    pattern_detail = ""
    if len(scores_list) >= 4:
        # 检测ABAB模式
        for i in range(len(scores_list) - 3):
            if scores_list[i] == scores_list[i + 2] and scores_list[i + 1] == scores_list[i + 3] and scores_list[i] != scores_list[i + 1]:
                pattern_detected = True; pattern_detail = "ABAB重复模式"
                break
        # 检测ABCDABCD模式（长度为4的重复）
        if not pattern_detected and len(scores_list) >= 8:
            for i in range(len(scores_list) - 7):
                seg1 = scores_list[i:i+4]
                seg2 = scores_list[i+4:i+8]
                if seg1 == seg2 and len(set(seg1)) > 2:
                    pattern_detected = True; pattern_detail = "四题段重复模式"
                    break

    # 7. 综合质量评分（加权计算，满分100）
    quality_score = 100.0
    deductions = []

    if total_q > 0:
        # 总时长过短（权重30%）
        if total_time < min_time_per_q * 0.5:
            quality_score -= 30; deductions.append("总答题时间严重不足")
        elif total_time < min_time_per_q * 0.8:
            quality_score -= 15; deductions.append("总答题时间偏短")

        # 快速作答题目过多（权重20%）
        fast_ratio = fast_count / total_q
        if fast_ratio > 0.5:
            quality_score -= 20; deductions.append(f"快速作答题目过多（{fast_count}/{total_q}）")
        elif fast_ratio > 0.3:
            quality_score -= 10; deductions.append(f"部分题目作答过快（{fast_count}/{total_q}）")

        # 连续同选项（权重15%）
        if max_consecutive_same >= 10:
            quality_score -= 15; deductions.append(f"连续{max_consecutive_same}题选同一选项")
        elif max_consecutive_same >= 7:
            quality_score -= 8; deductions.append(f"连续{max_consecutive_same}题选同一选项")

        # 选项分布异常（权重10%）
        if same_option_ratio > 0.8:
            quality_score -= 10; deductions.append("某一选项占比过高")

        # 注意力检测失败（权重20%）
        if not attention_passed:
            quality_score -= 20; deductions.append("注意力检测未通过")

        # 矛盾题（权重15%）
        if contradiction_count >= 4:
            quality_score -= 20; deductions.append(f"存在{contradiction_count}组矛盾答案")
        elif contradiction_count >= 2:
            quality_score -= 12; deductions.append(f"存在{contradiction_count}组矛盾答案")
        elif contradiction_count >= 1:
            quality_score -= 6; deductions.append(f"存在{contradiction_count}组矛盾答案")

        # 规律作答（权重10%）
        if pattern_detected:
            quality_score -= 15; deductions.append(f"检测到规律作答（{pattern_detail}）")

    quality_score = max(quality_score, 0)

    if quality_score >= 80:
        quality_level = "normal"
        validity = "valid"
    elif quality_score >= 60:
        quality_level = "mild_anomaly"
        validity = "basically_valid"
    elif quality_score >= 40:
        quality_level = "moderate_anomaly"
        validity = "questionable"
    else:
        quality_level = "severe_anomaly"
        validity = "not_recommended"

    suggest_retest = quality_level in ("moderate_anomaly", "severe_anomaly")

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
                 "min_expected_time": min_time_per_q},
    ))

    return {"quality_level": quality_level, "quality_score": quality_score, "validity": validity, "suggest_retest": suggest_retest, "deductions": deductions}


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
