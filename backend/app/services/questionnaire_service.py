from sqlalchemy.orm import Session, joinedload
from ..models.questionnaire import Questionnaire, Question, Option, ContradictionGroup, QuestionType
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.risk import ScoringResult, QualityAssessment, RiskAlert
from ..models.user import User
from ..schemas.questionnaire import QuestionnaireCreate, QuestionnaireUpdate, QuestionCreate, QuestionUpdate, OptionCreate, ContradictionGroupCreate


def list_questionnaires(db: Session, school_id: int | None, page: int = 1, page_size: int = 20,
                         category: str = "", status: str = "", keyword: str = "", include_builtin: bool = True):
    q = db.query(Questionnaire)
    if school_id:
        q = q.filter((Questionnaire.school_id == school_id) | (Questionnaire.is_builtin == True))
    elif not include_builtin:
        q = q.filter(Questionnaire.school_id.isnot(None))
    if category:
        q = q.filter(Questionnaire.category == category)
    if status:
        q = q.filter(Questionnaire.status == status)
    if keyword:
        q = q.filter(Questionnaire.title.contains(keyword))

    total = q.count()
    items = q.order_by(Questionnaire.is_builtin.desc(), Questionnaire.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [format_questionnaire(item, db) for item in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max((total + page_size - 1) // page_size, 1),
    }


def format_questionnaire(q: Questionnaire, db: Session) -> dict:
    question_count = db.query(Question).filter(Question.questionnaire_id == q.id).count()
    return {
        "id": q.id, "school_id": q.school_id, "title": q.title, "description": q.description,
        "category": q.category, "applicable_grades": q.applicable_grades,
        "is_builtin": q.is_builtin, "status": q.status, "created_by": q.created_by,
        "code": q.code,
        "source_type": q.source_type or ("reference_screening" if q.is_builtin else "school_custom"),
        "disclaimer": q.disclaimer or "",
        "dimensions": q.dimensions or [],
        "scoring_rule": q.scoring_rule or {},
        "risk_rules": q.risk_rules or {},
        "quality_rules": q.quality_rules or {},
        "version": q.version,
        "rule_version": q.rule_version,
        "locked_after_publish": q.locked_after_publish,
        "source_questionnaire_id": q.source_questionnaire_id,
        "editable": not q.is_builtin,
        "question_count": question_count,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }


def create_questionnaire(db: Session, data: QuestionnaireCreate, user_id: int, school_id: int) -> Questionnaire:
    q = Questionnaire(
        school_id=school_id,
        title=data.title,
        description=data.description,
        category=data.category,
        applicable_grades=data.applicable_grades or "",
        source_type=data.source_type or "school_custom",
        disclaimer=data.disclaimer or "",
        dimensions=data.dimensions or [],
        scoring_rule=data.scoring_rule or {},
        risk_rules=data.risk_rules or {},
        quality_rules=data.quality_rules or {},
        created_by=user_id,
        status="draft",
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


_ALLOWED_UPDATE_FIELDS = {
    "title", "description", "category", "applicable_grades", "status",
    "disclaimer", "dimensions", "scoring_rule", "risk_rules", "quality_rules", "source_type",
}


def update_questionnaire(db: Session, qid: int, data: QuestionnaireUpdate) -> Questionnaire:
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise ValueError("问卷不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k in _ALLOWED_UPDATE_FIELDS:
            setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return q


def delete_questionnaire(db: Session, qid: int):
    q = db.query(Questionnaire).filter(Questionnaire.id == qid, Questionnaire.status == "draft").first()
    if not q:
        raise ValueError("只能删除草稿状态的问卷")
    # 级联删除关联的任务和答卷数据
    task_ids = [t.id for t in db.query(Task.id).filter(Task.questionnaire_id == qid).all()]
    if task_ids:
        sheet_ids = [s.id for s in db.query(AnswerSheet.id).filter(AnswerSheet.task_id.in_(task_ids)).all()]
        if sheet_ids:
            db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
            db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
            db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
            alert_ids = [a.id for a in db.query(RiskAlert.id).filter(RiskAlert.answer_sheet_id.in_(sheet_ids)).all()]
            if alert_ids:
                db.query(Intervention).filter(Intervention.risk_alert_id.in_(alert_ids)).delete(synchronize_session=False)
            db.query(RiskAlert).filter(RiskAlert.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
            db.query(AnswerSheet).filter(AnswerSheet.id.in_(sheet_ids)).delete(synchronize_session=False)
        db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
    # 删除问卷本身
    db.query(Option).filter(Option.question_id.in_(db.query(Question.id).filter(Question.questionnaire_id == qid))).delete(synchronize_session=False)
    db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == qid).delete()
    db.query(Question).filter(Question.questionnaire_id == qid).delete()
    db.delete(q)
    db.commit()


def copy_questionnaire(db: Session, qid: int, user_id: int, school_id: int) -> Questionnaire:
    original = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not original:
        raise ValueError("问卷不存在")
    new_q = Questionnaire(school_id=school_id, title=original.title + " (副本)", description=original.description,
                           category=original.category, applicable_grades=original.applicable_grades,
                           is_builtin=False, status="draft", created_by=user_id,
                           code=None, source_type=original.source_type or "school_custom",
                           disclaimer=original.disclaimer or "",
                           dimensions=original.dimensions or [],
                           scoring_rule=original.scoring_rule or {},
                           risk_rules=original.risk_rules or {},
                           quality_rules=original.quality_rules or {},
                           version=original.version or 1,
                           source_questionnaire_id=original.id,
                           rule_version=original.rule_version or f"copy-of-{original.id}")
    db.add(new_q)
    db.flush()
    question_id_map: dict[int, int] = {}
    for question in db.query(Question).filter(Question.questionnaire_id == qid).order_by(Question.sort_order).all():
        new_question = Question(questionnaire_id=new_q.id, title=question.title, description=question.description,
                                type=question.type, required=question.required, sort_order=question.sort_order,
                                dimension=question.dimension, risk_tag=question.risk_tag,
                                is_reverse=question.is_reverse, is_attention_check=question.is_attention_check,
                                attention_correct_answer=question.attention_correct_answer,
                                risk_threshold=question.risk_threshold, code=question.code)
        db.add(new_question)
        db.flush()
        question_id_map[question.id] = new_question.id
        for option in db.query(Option).filter(Option.question_id == question.id).order_by(Option.sort_order).all():
            db.add(Option(question_id=new_question.id, content=option.content, score=option.score,
                          sort_order=option.sort_order, is_risk_option=option.is_risk_option))

    for cg in db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == qid).all():
        new_question_a_id = question_id_map.get(cg.question_a_id)
        new_question_b_id = question_id_map.get(cg.question_b_id)
        if not new_question_a_id or not new_question_b_id:
            continue
        db.add(ContradictionGroup(questionnaire_id=new_q.id, question_a_id=new_question_a_id,
                                   question_b_id=new_question_b_id, relation_type=cg.relation_type,
                                   max_score_diff=cg.max_score_diff, description=cg.description))
    db.commit()
    db.refresh(new_q)
    return new_q


def get_questionnaire_detail(db: Session, qid: int) -> dict:
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise ValueError("问卷不存在")
    result = format_questionnaire(q, db)
    questions = db.query(Question).filter(Question.questionnaire_id == qid).order_by(Question.sort_order).all()
    result["questions"] = []
    for qu in questions:
        q_data = {
            "id": qu.id, "code": qu.code, "title": qu.title, "description": qu.description, "type": qu.type,
            "required": qu.required, "sort_order": qu.sort_order, "dimension": qu.dimension,
            "risk_tag": qu.risk_tag, "is_reverse": qu.is_reverse,
            "is_attention_check": qu.is_attention_check, "attention_correct_answer": qu.attention_correct_answer,
            "risk_threshold": qu.risk_threshold,
            "options": [],
        }
        for opt in db.query(Option).filter(Option.question_id == qu.id).order_by(Option.sort_order).all():
            q_data["options"].append({
                "id": opt.id, "content": opt.content, "score": opt.score,
                "sort_order": opt.sort_order, "is_risk_option": opt.is_risk_option,
            })
        result["questions"].append(q_data)

    result["contradiction_groups"] = []
    for cg in db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == qid).all():
        result["contradiction_groups"].append({
            "id": cg.id, "question_a_id": cg.question_a_id, "question_b_id": cg.question_b_id,
            "relation_type": cg.relation_type, "max_score_diff": cg.max_score_diff, "description": cg.description,
        })
    return result


# Question CRUD
def add_question(db: Session, qid: int, data: QuestionCreate) -> Question:
    q = Question(questionnaire_id=qid, title=data.title, description=data.description or "",
                 type=data.type, required=data.required, sort_order=data.sort_order or 0,
                 dimension=data.dimension or "", risk_tag=data.risk_tag or "",
                 is_reverse=data.is_reverse or False, is_attention_check=data.is_attention_check or False,
                 attention_correct_answer=data.attention_correct_answer or "",
                 risk_threshold=data.risk_threshold)
    db.add(q)
    db.flush()
    for i, opt in enumerate(data.options):
        db.add(Option(question_id=q.id, content=opt.content, score=opt.score, sort_order=opt.sort_order or i, is_risk_option=opt.is_risk_option or False))
    db.commit()
    db.refresh(q)
    return q


def update_question(db: Session, question_id: int, data: QuestionUpdate) -> Question:
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise ValueError("题目不存在")
    for k, v in data.model_dump(exclude_unset=True, exclude={"options"}).items():
        setattr(q, k, v)
    if data.options is not None:
        db.query(Option).filter(Option.question_id == question_id).delete()
        for i, opt in enumerate(data.options):
            db.add(Option(question_id=q.id, content=opt.content, score=opt.score, sort_order=opt.sort_order or i, is_risk_option=opt.is_risk_option or False))
    db.commit()
    db.refresh(q)
    return q


def delete_question(db: Session, question_id: int):
    db.query(Option).filter(Option.question_id == question_id).delete()
    db.query(AnswerRecord).filter(AnswerRecord.question_id == question_id).delete()
    db.query(ContradictionGroup).filter(
        (ContradictionGroup.question_a_id == question_id) | (ContradictionGroup.question_b_id == question_id)
    ).delete()
    db.query(Question).filter(Question.id == question_id).delete()
    db.commit()


def update_question_sort(db: Session, question_ids: list[int]):
    for i, qid in enumerate(question_ids):
        db.query(Question).filter(Question.id == qid).update({Question.sort_order: i})
    db.commit()


# Contradiction Group CRUD
def add_contradiction_group(db: Session, qid: int, data: ContradictionGroupCreate) -> ContradictionGroup:
    cg = ContradictionGroup(questionnaire_id=qid, question_a_id=data.question_a_id, question_b_id=data.question_b_id,
                             relation_type=data.relation_type, max_score_diff=data.max_score_diff or 3,
                             description=data.description or "")
    db.add(cg)
    db.commit()
    db.refresh(cg)
    return cg


def delete_contradiction_group(db: Session, cg_id: int):
    db.query(ContradictionGroup).filter(ContradictionGroup.id == cg_id).delete()
    db.commit()


DIMENSION_LABELS = {
    "emotion": "情绪状态", "sleep": "睡眠状态", "academic_pressure": "学习压力",
    "interpersonal": "人际关系", "family_support": "家庭支持", "campus_safety": "校园安全",
    "internet_use": "网络使用", "self_safety": "自我安全", "general": "综合",
    "somatization": "躯体化", "obsessive": "强迫症状", "interpersonal_sensitivity": "人际敏感",
    "depression": "抑郁", "anxiety": "焦虑", "hostility": "敌对", "phobic": "恐怖",
    "paranoid": "偏执", "psychoticism": "精神病性",
    "force": "强迫", "adaptation": "适应不良", "emotional_instability": "情绪不稳定",
    "psychological_imbalance": "心理失衡", "stress": "压力",
    "compulsive_use": "强迫性使用", "withdrawal": "戒断反应", "tolerance": "耐受性",
    "interpersonal_health": "人际与健康", "time_management": "时间管理",
    "sleep_quality": "睡眠质量", "sleep_latency": "入睡时间", "sleep_duration": "睡眠时长",
    "sleep_efficiency": "睡眠效率", "sleep_disturbance": "睡眠障碍",
    "daytime_dysfunction": "日间功能障碍",
    "victimization": "受欺凌", "aggression": "攻击行为", "bystander": "旁观行为",
    "help_seeking": "求助行为", "safety": "安全感", "cyberbullying": "网络欺凌",
    "rejection": "拒绝", "emotional_warmth": "情感温暖", "overprotection": "过度保护",
    "hopelessness": "绝望感", "optimism": "乐观", "concealment": "掩饰",
    "learning_pressure": "学习压力",
}


def get_answer_detail(db: Session, answer_sheet_id: int) -> dict:
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == answer_sheet_id).first()
    if not sheet:
        raise ValueError("答卷不存在")

    student = db.query(User).filter(User.id == sheet.student_id).first()
    questionnaire = db.query(Questionnaire).filter(Questionnaire.id == sheet.questionnaire_id).first()
    from ..models.task import Task
    task = db.query(Task).filter(Task.id == sheet.task_id).first()

    scoring = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).first()
    quality = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == sheet.id).first()

    dim_label_map = {}
    if questionnaire and questionnaire.dimensions:
        for d in questionnaire.dimensions:
            if isinstance(d, dict):
                dim_label_map[d.get("code", "")] = d.get("title", d.get("code", ""))

    questions = db.query(Question).filter(
        Question.questionnaire_id == sheet.questionnaire_id
    ).order_by(Question.sort_order).all()

    options_by_qid = {}
    for q in questions:
        opts = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
        options_by_qid[q.id] = opts

    records = db.query(AnswerRecord).filter(
        AnswerRecord.answer_sheet_id == sheet.id
    ).all()
    record_map = {r.question_id: r for r in records}

    duration = sheet.total_duration_seconds or 0
    if not duration and sheet.started_at and sheet.submitted_at:
        from datetime import timezone as _tz
        try:
            s = sheet.started_at.replace(tzinfo=_tz.utc) if sheet.started_at.tzinfo is None else sheet.started_at
            e = sheet.submitted_at.replace(tzinfo=_tz.utc) if sheet.submitted_at.tzinfo is None else sheet.submitted_at
            duration = int((e - s).total_seconds())
        except Exception:
            pass

    answers = []
    for q in questions:
        rec = record_map.get(q.id)
        all_opts = options_by_qid.get(q.id, [])
        opt_list = [{"option_id": o.id, "content": o.content, "score": o.score, "is_risk_option": o.is_risk_option} for o in all_opts]

        selected_ids = []
        selected_opts = []
        if rec and isinstance(rec.answer_content, dict):
            sel_id = rec.answer_content.get("selected_option_id")
            sel_ids = rec.answer_content.get("selected_option_ids")
            if sel_id:
                selected_ids = [sel_id]
            elif sel_ids:
                selected_ids = sel_ids
            for o in all_opts:
                if o.id in selected_ids:
                    selected_opts.append({"option_id": o.id, "content": o.content, "score": o.score})

        dim = q.dimension or "general"
        answers.append({
            "question_id": q.id,
            "question_code": q.code or "",
            "question_title": q.title,
            "question_type": q.type,
            "dimension": dim,
            "dimension_label": dim_label_map.get(dim, DIMENSION_LABELS.get(dim, dim)),
            "sort_order": q.sort_order,
            "is_reverse": q.is_reverse or False,
            "is_attention_check": q.is_attention_check or False,
            "options": opt_list,
            "answer_content": rec.answer_content if rec else None,
            "selected_option_ids": selected_ids,
            "selected_options": selected_opts,
            "score": rec.score if rec else 0,
            "duration_seconds": rec.duration_seconds if rec else 0,
            "risk_tag": q.risk_tag or "",
        })

    return {
        "answer_sheet_id": sheet.id,
        "student_id": sheet.student_id,
        "student_name": student.real_name if student else "",
        "student_no": student.student_no if student else "",
        "school_name": "",
        "questionnaire_id": sheet.questionnaire_id,
        "questionnaire_title": questionnaire.title if questionnaire else "",
        "task_id": sheet.task_id,
        "task_name": task.name if task else "",
        "status": sheet.status,
        "started_at": sheet.started_at.isoformat() if sheet.started_at else None,
        "submitted_at": sheet.submitted_at.isoformat() if sheet.submitted_at else None,
        "total_duration_seconds": duration,
        "scoring": {
            "total_score": scoring.total_score if scoring else 0,
            "dimension_scores": scoring.dimension_scores if scoring else {},
            "risk_level": scoring.risk_level if scoring else "low",
            "risk_type": scoring.risk_type if scoring else "",
            "risk_description": scoring.risk_description if scoring else "",
            "triggered_rules": scoring.triggered_rules if scoring else [],
        } if scoring else None,
        "quality": {
            "quality_score": quality.quality_score if quality else 100,
            "quality_level": quality.quality_level if quality else "normal",
            "validity": quality.validity if quality else "valid",
            "suggest_retest": quality.suggest_retest if quality else False,
        } if quality else None,
        "answers": answers,
    }


def list_student_answer_sheets(db: Session, student_id: int) -> list[dict]:
    sheets = db.query(AnswerSheet).filter(
        AnswerSheet.student_id == student_id, AnswerSheet.status == "submitted"
    ).order_by(AnswerSheet.submitted_at.desc()).all()

    results = []
    for sheet in sheets:
        questionnaire = db.query(Questionnaire).filter(Questionnaire.id == sheet.questionnaire_id).first()
        scoring = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).first()
        results.append({
            "answer_sheet_id": sheet.id,
            "questionnaire_id": sheet.questionnaire_id,
            "questionnaire_title": questionnaire.title if questionnaire else "",
            "submitted_at": sheet.submitted_at.isoformat() if sheet.submitted_at else None,
            "total_score": scoring.total_score if scoring else 0,
            "risk_level": scoring.risk_level if scoring else "low",
        })
    return results
