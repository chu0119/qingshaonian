from sqlalchemy.orm import Session, joinedload
from ..models.questionnaire import Questionnaire, Question, Option, ContradictionGroup, QuestionType
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
    q = Questionnaire(school_id=school_id, title=data.title, description=data.description,
                       category=data.category, applicable_grades=data.applicable_grades or "",
                       source_type="school_custom", disclaimer="",
                       dimensions=data.dimensions or [],
                       scoring_rule=data.scoring_rule or {},
                       risk_rules=data.risk_rules or {},
                       quality_rules=data.quality_rules or {},
                       created_by=user_id, status="draft")
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


_ALLOWED_UPDATE_FIELDS = {
    "title", "description", "category", "applicable_grades", "status",
    "dimensions", "scoring_rule", "risk_rules", "quality_rules",
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
