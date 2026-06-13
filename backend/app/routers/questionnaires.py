from fastapi import APIRouter, Depends, Query, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.questionnaire import Questionnaire, Question, ContradictionGroup
from ..schemas.questionnaire import QuestionnaireCreate, QuestionnaireUpdate, QuestionCreate, QuestionUpdate, ContradictionGroupCreate
from ..dependencies import get_current_user, require_role
from ..services import questionnaire_service as qs
from ..services.questionnaire_import_service import generate_import_template, import_questionnaire, export_questionnaire_to_excel
from ..services.audit_service import log_operation
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/questionnaires", tags=["问卷管理"])


def _get_accessible_questionnaire(db: Session, qid: int, user: User, writable: bool = False) -> Questionnaire:
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q or (q.school_id not in (None, (getattr(user, '_effective_school_id', None) or user.school_id)) and not q.is_builtin):
        raise HTTPException(status_code=404, detail="问卷不存在")
    if writable and (q.is_builtin or q.school_id != (getattr(user, '_effective_school_id', None) or user.school_id)):
        raise HTTPException(status_code=403, detail="内置问卷或其他学校问卷不可直接修改，请先复制")
    return q


@router.get("")
def list_questionnaires(
    page: int = Query(1), page_size: int = Query(20), category: str = Query(""),
    status: str = Query(""), keyword: str = Query(""),
    user: User = Depends(require_role("school_admin", "teacher")),
    db: Session = Depends(get_db),
):
    result = qs.list_questionnaires(db, (getattr(user, '_effective_school_id', None) or user.school_id), page, page_size, category, status, keyword)
    return APIResponse.success(result)


@router.post("")
def create_questionnaire(data: QuestionnaireCreate, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    q = qs.create_questionnaire(db, data, user.id, (getattr(user, '_effective_school_id', None) or user.school_id))
    log_operation(db, user, request, module="questionnaire", action="create", object_type="questionnaire", object_id=q.id, object_name=q.title)
    return APIResponse.success({"id": q.id}, message="问卷创建成功")


# ---------------------------------------------------------------------------
# 问卷导入导出 (school_admin) — 必须在 {qid} 路由之前定义
# ---------------------------------------------------------------------------

@router.get("/import-template")
def download_import_template(user: User = Depends(require_role("school_admin"))):
    """下载问卷导入 Excel 模板"""
    data = generate_import_template()
    import io
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=questionnaire_template.xlsx"},
    )


@router.post("/import")
def import_questionnaire_from_excel(
    file: UploadFile = File(...),
    user: User = Depends(require_role("school_admin")),
    db: Session = Depends(get_db),
):
    """从 Excel 文件导入问卷"""
    if not file.filename or not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的 Excel 文件")

    file_bytes = file.file.read()
    school_id = getattr(user, '_effective_school_id', None) or user.school_id
    result = import_questionnaire(db, file_bytes, school_id=school_id, created_by=user.id)

    if not result.get("success"):
        return JSONResponse(status_code=400, content={
            "code": 400,
            "message": f"导入失败，共发现 {result.get('total_errors', 0)} 个错误",
            "data": {"errors": result.get("errors", []), "total_errors": result.get("total_errors", 0)},
        })

    log_operation(db, user, None, module="questionnaire", action="import",
                  object_type="questionnaire", object_id=str(result["questionnaire_id"]),
                  detail=f"导入问卷: {result['title']}")
    return APIResponse.success(data=result, message=result.get("message", "导入成功"))


@router.get("/{qid}/export")
def export_questionnaire(
    qid: int,
    user: User = Depends(require_role("school_admin", "teacher")),
    db: Session = Depends(get_db),
):
    """导出单个问卷为 Excel"""
    qn = _get_accessible_questionnaire(db, qid, user, writable=False)
    try:
        data = export_questionnaire_to_excel(db, qn.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    import io, re, urllib.parse
    safe_name = re.sub(r'[\\/*?:"<>|]', "", qn.title or "questionnaire").replace(" ", "_")[:80]
    encoded_name = urllib.parse.quote(f"{safe_name}.xlsx")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


# ---------------------------------------------------------------------------
# 问卷 CRUD
# ---------------------------------------------------------------------------


@router.get("/{qid}")
def get_questionnaire(qid: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        _get_accessible_questionnaire(db, qid, user)
        result = qs.get_questionnaire_detail(db, qid)
        return APIResponse.success(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{qid}")
def update_questionnaire(qid: int, data: QuestionnaireUpdate, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        current = _get_accessible_questionnaire(db, qid, user, writable=True)
        qs.update_questionnaire(db, qid, data)
        log_operation(db, user, request, module="questionnaire", action="update", object_type="questionnaire", object_id=qid, object_name=current.title)
        return APIResponse.success(message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{qid}")
def delete_questionnaire(qid: int, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        current = _get_accessible_questionnaire(db, qid, user, writable=True)
        qs.delete_questionnaire(db, qid)
        log_operation(db, user, request, module="questionnaire", action="delete", object_type="questionnaire", object_id=qid, object_name=current.title)
        return APIResponse.success(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{qid}/copy")
def copy_questionnaire(qid: int, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        _get_accessible_questionnaire(db, qid, user)
        q = qs.copy_questionnaire(db, qid, user.id, (getattr(user, '_effective_school_id', None) or user.school_id))
        log_operation(db, user, request, module="questionnaire", action="copy", object_type="questionnaire", object_id=q.id, object_name=q.title, detail=f"source={qid}")
        return APIResponse.success({"id": q.id}, message="复制成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{qid}/preview")
def preview_questionnaire(qid: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        _get_accessible_questionnaire(db, qid, user)
        result = qs.get_questionnaire_detail(db, qid)
        return APIResponse.success(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 题目管理
@router.get("/{qid}/questions")
def list_questions(qid: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user)
    result = qs.get_questionnaire_detail(db, qid)
    return APIResponse.success(result.get("questions", []))


@router.post("/{qid}/questions")
def add_question(qid: int, data: QuestionCreate, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user, writable=True)
    q = qs.add_question(db, qid, data)
    return APIResponse.success({"id": q.id}, message="题目添加成功")


@router.put("/{qid}/questions/{question_id}")
def update_question(qid: int, question_id: int, data: QuestionUpdate, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        _get_accessible_questionnaire(db, qid, user, writable=True)
        question = db.query(Question).filter(Question.id == question_id, Question.questionnaire_id == qid).first()
        if not question:
            raise HTTPException(status_code=404, detail="题目不存在")
        qs.update_question(db, question_id, data)
        return APIResponse.success(message="题目更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{qid}/questions/{question_id}")
def delete_question(qid: int, question_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user, writable=True)
    question = db.query(Question).filter(Question.id == question_id, Question.questionnaire_id == qid).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    qs.delete_question(db, question_id)
    return APIResponse.success(message="题目删除成功")


@router.put("/{qid}/questions/sort")
def sort_questions(qid: int, question_ids: list[int] | None = None, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    if not question_ids:
        question_ids = []
    _get_accessible_questionnaire(db, qid, user, writable=True)
    count = db.query(Question).filter(Question.questionnaire_id == qid, Question.id.in_(question_ids)).count() if question_ids else 0
    if count != len(set(question_ids)):
        raise HTTPException(status_code=403, detail="包含不属于当前问卷的题目")
    qs.update_question_sort(db, question_ids)
    return APIResponse.success(message="排序更新成功")


# 选项管理

@router.post("/{qid}/questions/{question_id}/options")
def add_option(qid: int, question_id: int, data: dict, request: Request,
               user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    """添加选项"""
    _get_accessible_questionnaire(db, qid, user, writable=True)
    question = db.query(Question).filter(Question.id == question_id, Question.questionnaire_id == qid).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    from ..models.questionnaire import Option
    max_order = db.query(func.max(Option.sort_order)).filter(Option.question_id == question_id).scalar() or 0
    option = Option(
        question_id=question_id, content=data.get("content", ""),
        score=data.get("score", 0), sort_order=data.get("sort_order", max_order + 1),
        is_risk_option=data.get("is_risk_option", False),
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    log_operation(db, user, request, module="questionnaire", action="add_option", object_type="question", object_id=question_id)
    return APIResponse.success({"id": option.id}, message="选项添加成功")


@router.put("/{qid}/questions/{question_id}/options/{option_id}")
def update_option(qid: int, question_id: int, option_id: int, data: dict, request: Request,
                  user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    """更新选项"""
    _get_accessible_questionnaire(db, qid, user, writable=True)
    from ..models.questionnaire import Option
    option = db.query(Option).filter(Option.id == option_id, Option.question_id == question_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="选项不存在")
    allowed_fields = {"content", "score", "sort_order", "is_risk_option"}
    for k, v in data.items():
        if k in allowed_fields and hasattr(option, k):
            setattr(option, k, v)
    db.commit()
    return APIResponse.success(message="选项更新成功")


@router.delete("/{qid}/questions/{question_id}/options/{option_id}")
def delete_option(qid: int, question_id: int, option_id: int, request: Request,
                  user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    """删除选项"""
    _get_accessible_questionnaire(db, qid, user, writable=True)
    from ..models.questionnaire import Option
    option = db.query(Option).filter(Option.id == option_id, Option.question_id == question_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="选项不存在")
    count = db.query(func.count(Option.id)).filter(Option.question_id == question_id).scalar()
    if count <= 2:
        raise HTTPException(status_code=400, detail="每道题至少需要2个选项")
    db.delete(option)
    db.commit()
    return APIResponse.success(message="选项删除成功")


# 矛盾题组管理
@router.get("/{qid}/contradictions")
def list_contradictions(qid: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user)
    result = qs.get_questionnaire_detail(db, qid)
    return APIResponse.success(result.get("contradiction_groups", []))


@router.post("/{qid}/contradictions")
def add_contradiction(qid: int, data: ContradictionGroupCreate, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user, writable=True)
    cg = qs.add_contradiction_group(db, qid, data)
    return APIResponse.success({"id": cg.id}, message="矛盾题组设置成功")


@router.delete("/{qid}/contradictions/{cg_id}")
def delete_contradiction(qid: int, cg_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user, writable=True)
    cg = db.query(ContradictionGroup).filter(ContradictionGroup.id == cg_id, ContradictionGroup.questionnaire_id == qid).first()
    if not cg:
        raise HTTPException(status_code=404, detail="矛盾题组不存在")
    qs.delete_contradiction_group(db, cg_id)
    return APIResponse.success(message="矛盾题组删除成功")


# ======================== 问卷版本管理 ========================

@router.get("/{qid}/versions")
def list_versions(qid: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    """查看问卷版本历史"""
    _get_accessible_questionnaire(db, qid, user)
    current = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    versions = [{"id": current.id, "version": current.version or 1, "title": current.title, "status": current.status, "created_at": current.created_at.isoformat() if current.created_at else None}]
    copies = db.query(Questionnaire).filter(Questionnaire.source_questionnaire_id == qid).order_by(Questionnaire.version.desc()).all()
    for c in copies:
        versions.append({"id": c.id, "version": c.version or 1, "title": c.title, "status": c.status, "created_at": c.created_at.isoformat() if c.created_at else None})
    return APIResponse.success(versions)


@router.post("/{qid}/new-version")
def create_new_version(qid: int, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    """从当前问卷创建新版本"""
    source = _get_accessible_questionnaire(db, qid, user)
    existing_copies = db.query(func.count(Questionnaire.id)).filter(Questionnaire.source_questionnaire_id == qid).scalar() or 0
    new_version = (source.version or 1) + 1 + existing_copies

    new_q = Questionnaire(
        school_id=source.school_id, title=f"{source.title} v{new_version}",
        description=source.description, category=source.category,
        applicable_grades=source.applicable_grades, is_builtin=False,
        source_type="school_custom", disclaimer=source.disclaimer,
        dimensions=source.dimensions, scoring_rule=source.scoring_rule,
        risk_rules=source.risk_rules, quality_rules=source.quality_rules,
        status="draft", created_by=user.id, version=new_version,
        locked_after_publish=False, source_questionnaire_id=qid,
    )
    db.add(new_q)
    db.flush()

    questions = db.query(Question).filter(Question.questionnaire_id == qid).order_by(Question.sort_order).all()
    from ..models.questionnaire import Option
    q_id_map = {}
    for old_q in questions:
        new_question = Question(
            questionnaire_id=new_q.id, title=old_q.title, description=old_q.description,
            type=old_q.type, sort_order=old_q.sort_order, required=old_q.required,
            dimension=old_q.dimension, is_attention_check=old_q.is_attention_check,
        )
        db.add(new_question)
        db.flush()
        q_id_map[old_q.id] = new_question.id
        old_options = db.query(Option).filter(Option.question_id == old_q.id).order_by(Option.sort_order).all()
        for old_opt in old_options:
            db.add(Option(
                question_id=new_question.id, content=old_opt.content, score=old_opt.score,
                sort_order=old_opt.sort_order, is_risk_option=old_opt.is_risk_option,
            ))

    db.commit()
    log_operation(db, user, request, module="questionnaire", action="create_version",
                  object_type="questionnaire", object_id=new_q.id, object_name=new_q.title,
                  detail=f"source={qid};version={new_version}")
    return APIResponse.success({"id": new_q.id, "version": new_version}, message=f"新版本 v{new_version} 创建成功")

