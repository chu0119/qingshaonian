from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.questionnaire import Question, Option, Questionnaire
from ..dependencies import get_current_user, require_role
from ..services import scoring_service
from ..utils.access_control import task_matches_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/student", tags=["学生端"])


@router.get("/tasks/pending")
def pending_tasks(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.status.in_(["not_started", "in_progress", "active"]), Task.school_id == user.school_id).all()
    items = []
    for t in tasks:
        if not task_matches_student(user, t):
            continue
        sheet = db.query(AnswerSheet).filter(AnswerSheet.task_id == t.id, AnswerSheet.student_id == user.id).first()
        qnr = db.query(Questionnaire).filter(Questionnaire.id == t.questionnaire_id).first()
        items.append({
            "task_id": t.id, "task_name": t.name, "questionnaire_title": qnr.title if qnr else "",
            "description": t.description,
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "end_time": t.end_time.isoformat() if t.end_time else None,
            "can_answer": _student_can_answer(t),
            "status": sheet.status if sheet else "not_started",
            "answer_sheet_id": sheet.id if sheet else None,
        })
    return APIResponse.success(items)


@router.get("/tasks/completed")
def completed_tasks(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    sheets = db.query(AnswerSheet).filter(AnswerSheet.student_id == user.id, AnswerSheet.status == "submitted").all()
    items = []
    for s in sheets:
        task = db.query(Task).filter(Task.id == s.task_id).first()
        qnr = db.query(Questionnaire).filter(Questionnaire.id == s.questionnaire_id).first()
        items.append({
            "answer_sheet_id": s.id, "task_name": task.name if task else "",
            "questionnaire_title": qnr.title if qnr else "",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        })
    return APIResponse.success(items)


@router.post("/tasks/{task_id}/start")
def start_answer(task_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or not task_matches_student(user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        sheet = scoring_service.start_answer(db, task_id, user.id)
        return _format_sheet_for_student(db, sheet)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/answer-sheets/{sheet_id}")
def get_answer_sheet(sheet_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id, AnswerSheet.student_id == user.id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="答卷不存在")
    return _format_sheet_for_student(db, sheet)


def _student_can_answer(task: Task) -> bool:
    now = datetime.now()
    if task.status not in ("in_progress", "active"):
        return False
    if task.start_time and task.start_time > now:
        return False
    if task.end_time and task.end_time < now:
        return False
    return True


def _format_sheet_for_student(db: Session, sheet: AnswerSheet):
    task = db.query(Task).filter(Task.id == sheet.task_id).first()
    questionnaire = db.query(Questionnaire).filter(Questionnaire.id == sheet.questionnaire_id).first()
    questions = db.query(Question).filter(Question.questionnaire_id == sheet.questionnaire_id).order_by(Question.sort_order).all()
    records = {r.question_id: r for r in db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet.id).all()}
    question_data = []
    ordered_ids = sheet.question_order or [q.id for q in questions]
    for qid in ordered_ids:
        q = next((x for x in questions if x.id == qid), None)
        if not q:
            continue
        options = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
        opt_order = sheet.option_orders.get(str(q.id), [o.id for o in options]) if sheet.option_orders else [o.id for o in options]
        opt_data = []
        for oid in opt_order:
            o = next((x for x in options if x.id == oid), None)
            if o:
                opt_data.append({"id": o.id, "content": o.content, "sort_order": o.sort_order})
        record = records.get(q.id)
        question_data.append({
            "id": q.id, "title": q.title, "description": q.description, "type": q.type,
            "required": q.required, "options": opt_data,
            "previous_answer": record.answer_content if record else None,
            "previous_duration": record.duration_seconds if record else 0,
        })
    return APIResponse.success({
        "answer_sheet_id": sheet.id, "task_id": sheet.task_id,
        "questionnaire_id": sheet.questionnaire_id,
        "questionnaire_title": questionnaire.title if questionnaire else "",
        "task_name": task.name if task else "",
        "description": task.description if task else "",
        "start_time": task.start_time.isoformat() if task and task.start_time else None,
        "end_time": task.end_time.isoformat() if task and task.end_time else None,
        "can_answer": _student_can_answer(task) if task else False,
        "allow_edit": task.allow_edit if task else False,
        "status": sheet.status,
        "submitted_message": "感谢你完成本次问卷，学校和老师会根据整体情况开展后续支持工作。" if sheet.status == "submitted" else "",
        "questions": question_data,
    })


@router.put("/answer-sheets/{sheet_id}/save")
def save_progress(sheet_id: int, data: dict, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id, AnswerSheet.student_id == user.id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="答卷不存在")
    scoring_service.save_progress(db, sheet_id, data.get("answers", []))
    return APIResponse.success({"saved_at": datetime.now().isoformat()}, message="保存成功")


@router.post("/answer-sheets/{sheet_id}/submit")
def submit_answer(sheet_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id, AnswerSheet.student_id == user.id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="答卷不存在")
    try:
        scoring_service.submit_answer(db, sheet_id)
        return APIResponse.success({"message": "感谢你完成本次问卷，学校和老师会根据整体情况开展后续支持工作。"})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
