from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.questionnaire import Questionnaire, Question, ContradictionGroup
from ..schemas.questionnaire import QuestionnaireCreate, QuestionnaireUpdate, QuestionCreate, QuestionUpdate, ContradictionGroupCreate
from ..dependencies import get_current_user, require_role
from ..services import questionnaire_service as qs
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
def sort_questions(qid: int, question_ids: list[int] = [], user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    _get_accessible_questionnaire(db, qid, user, writable=True)
    count = db.query(Question).filter(Question.questionnaire_id == qid, Question.id.in_(question_ids)).count() if question_ids else 0
    if count != len(set(question_ids)):
        raise HTTPException(status_code=403, detail="包含不属于当前问卷的题目")
    qs.update_question_sort(db, question_ids)
    return APIResponse.success(message="排序更新成功")


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
