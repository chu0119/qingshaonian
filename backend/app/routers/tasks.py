from fastapi import APIRouter, Depends, Query, HTTPException, Request
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.questionnaire import Questionnaire
from ..dependencies import get_current_user, require_role
from ..services.audit_service import log_operation
from ..services.stats_service import target_student_ids
from ..utils.access_control import can_access_task, teacher_class_ids
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/tasks", tags=["任务管理"])

OPEN_TASK_STATUSES = {"not_started", "in_progress", "active"}


def _effective_status(task: Task) -> str:
    now = datetime.now()
    if task.status in ("draft", "closed", "archived"):
        return task.status
    if task.end_time and task.end_time < now:
        return "ended"
    if task.start_time and task.start_time > now:
        return "not_started"
    return "in_progress"


@router.get("")
def list_tasks(
    page: int = Query(1), page_size: int = Query(20), status: str = Query(""),
    user: User = Depends(require_role("school_admin", "teacher")),
    db: Session = Depends(get_db),
):
    q = db.query(Task).filter(Task.school_id == user.school_id)
    if status:
        q = q.filter(Task.status == status)
    if user.role in ("teacher", "counselor"):
        all_tasks = [t for t in q.order_by(Task.id.desc()).all() if can_access_task(db, user, t)]
        total = len(all_tasks)
        tasks = all_tasks[(page - 1) * page_size: page * page_size]
    else:
        total = q.count()
        tasks = q.order_by(Task.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for t in tasks:
        qnr = db.query(Questionnaire).filter(Questionnaire.id == t.questionnaire_id).first()
        status_value = _effective_status(t)
        completed_q = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.task_id == t.id, AnswerSheet.status == "submitted")
        if user.role in ("teacher", "counselor"):
            completed_q = completed_q.join(User, User.id == AnswerSheet.student_id).filter(User.class_id.in_(teacher_class_ids(db, user)))
        completed = completed_q.scalar()
        expected = len(target_student_ids(db, t))
        items.append({
            "id": t.id, "name": t.name, "questionnaire_id": t.questionnaire_id,
            "questionnaire_title": qnr.title if qnr else "", "target_type": t.target_type,
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "end_time": t.end_time.isoformat() if t.end_time else None,
            "published_at": t.published_at.isoformat() if t.published_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "extended_at": t.extended_at.isoformat() if t.extended_at else None,
            "description": t.description,
            "allow_edit": t.allow_edit,
            "status": status_value, "shuffle_questions": t.shuffle_questions,
            "enable_quality_check": t.enable_quality_check,
            "completed_count": completed,
            "expected_count": expected,
            "uncompleted_count": max(expected - completed, 0),
            "completion_rate": round(completed / max(expected, 1) * 100, 1) if expected else 0,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return APIResponse.success({"items": items, "total": total, "page": page, "page_size": page_size,
                                "total_pages": max((total + page_size - 1) // page_size, 1)})


@router.post("")
def create_task(data: dict, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    questionnaire_id = data.get("questionnaire_id")
    if not questionnaire_id:
        raise HTTPException(status_code=400, detail="问卷ID不能为空")
    qnr = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
    if qnr and not (qnr.school_id == user.school_id or qnr.is_builtin):
        qnr = None
    if not qnr:
        raise HTTPException(status_code=404, detail="问卷不存在或无权限访问")

    target_type = data.get("target_type", "class")
    target_ids = [int(x) for x in (data.get("target_ids") or []) if str(x).isdigit()]
    if user.role in ("teacher", "counselor"):
        allowed_classes = teacher_class_ids(db, user)
        if target_type != "class" or not set(target_ids).issubset(allowed_classes):
            raise HTTPException(status_code=403, detail="只能向自己负责的班级发布任务")
    elif target_type == "class":
        count = db.query(Class).filter(Class.id.in_(target_ids), Class.school_id == user.school_id).count() if target_ids else 0
        if count != len(set(target_ids)):
            raise HTTPException(status_code=403, detail="包含不属于本校的班级")

    def parse_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

    status_value = data.get("status") or ("draft" if data.get("draft") else "in_progress")
    if status_value == "active":
        status_value = "in_progress"
    if status_value not in ("draft", "not_started", "in_progress"):
        status_value = "in_progress"
    published_at = datetime.now() if status_value != "draft" else None
    task = Task(
        school_id=user.school_id, questionnaire_id=questionnaire_id,
        name=data.get("name", ""), target_type=target_type,
        target_ids=target_ids, start_time=parse_dt(data.get("start_time")),
        end_time=parse_dt(data.get("end_time")), shuffle_questions=data.get("shuffle_questions", False),
        shuffle_options=data.get("shuffle_options", False),
        allow_edit=data.get("allow_edit", False),
        description=data.get("description", ""),
        reminder_strategy=data.get("reminder_strategy") or {},
        enable_quality_check=data.get("enable_quality_check", True),
        status=status_value, published_at=published_at, created_by=user.id,
    )
    task.target_snapshot = {"student_ids": target_student_ids(db, task), "target_type": target_type, "target_ids": target_ids}
    db.add(task)
    db.commit()
    db.refresh(task)
    log_operation(db, user, request, module="questionnaire_task", action="publish", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success({"id": task.id}, message="任务发布成功")


@router.get("/{task_id}")
def get_task(task_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    qnr = db.query(Questionnaire).filter(Questionnaire.id == task.questionnaire_id).first()
    completed = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.task_id == task_id, AnswerSheet.status == "submitted").scalar()
    total_students = len(target_student_ids(db, task))
    return APIResponse.success({
        "id": task.id, "name": task.name, "questionnaire_title": qnr.title if qnr else "",
        "description": task.description,
        "target_type": task.target_type, "target_ids": task.target_ids or [],
        "start_time": task.start_time.isoformat() if task.start_time else None,
        "end_time": task.end_time.isoformat() if task.end_time else None,
        "published_at": task.published_at.isoformat() if task.published_at else None,
        "closed_at": task.closed_at.isoformat() if task.closed_at else None,
        "extended_at": task.extended_at.isoformat() if task.extended_at else None,
        "status": _effective_status(task), "completed_count": completed, "total_students": total_students,
        "completion_rate": round(completed / max(total_students, 1) * 100, 1) if total_students else 0,
    })


@router.get("/{task_id}/completion")
def task_completion(task_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    sheets_q = db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id)
    if user.role in ("teacher", "counselor"):
        sheets_q = sheets_q.join(User, User.id == AnswerSheet.student_id).filter(User.class_id.in_(teacher_class_ids(db, user)))
    sheets = sheets_q.all()
    submitted_student_ids = {s.student_id for s in sheets if s.status == "submitted"}
    target_students_q = db.query(User).filter(User.id.in_(target_student_ids(db, task)), User.role == "student")
    if user.role in ("teacher", "counselor"):
        target_students_q = target_students_q.filter(User.class_id.in_(teacher_class_ids(db, user)))
    target_students = target_students_q.all()
    items = []
    sheet_by_student = {s.student_id: s for s in sheets}
    for student in target_students:
        s = sheet_by_student.get(student.id)
        items.append({
            "student_id": student.id, "student_name": student.real_name,
            "class_name": student.class_.name if student.class_ else "",
            "status": s.status if s else "not_started",
            "submitted_at": s.submitted_at.isoformat() if s and s.submitted_at else None,
        })
    return APIResponse.success(items)


@router.post("/{task_id}/publish")
def publish_task(task_id: int, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "archived":
        raise HTTPException(status_code=400, detail="已归档任务不能发布")
    task.status = "not_started" if task.start_time and task.start_time > datetime.now() else "in_progress"
    task.published_at = task.published_at or datetime.now()
    task.target_snapshot = {"student_ids": target_student_ids(db, task), "target_type": task.target_type, "target_ids": task.target_ids or []}
    db.commit()
    log_operation(db, user, request, module="questionnaire_task", action="publish", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已发布")


@router.post("/{task_id}/close")
def close_task(task_id: int, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "closed"
    task.closed_at = datetime.now()
    db.commit()
    log_operation(db, user, request, module="questionnaire_task", action="close", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已关闭")


@router.post("/{task_id}/extend")
def extend_task(task_id: int, data: dict, request: Request, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    end_time = data.get("end_time")
    if not end_time:
        raise HTTPException(status_code=400, detail="请设置新的截止时间")
    task.end_time = datetime.fromisoformat(str(end_time).replace("Z", "+00:00")).replace(tzinfo=None)
    task.extended_at = datetime.now()
    if task.status == "ended":
        task.status = "in_progress"
    db.commit()
    log_operation(db, user, request, module="questionnaire_task", action="extend", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已延期")


@router.post("/{task_id}/archive")
def archive_task(task_id: int, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.school_id == user.school_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "archived"
    db.commit()
    log_operation(db, user, request, module="questionnaire_task", action="archive", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已归档")


@router.get("/{task_id}/uncompleted")
def task_uncompleted(task_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    completion = task_completion(task_id, user, db).data
    return APIResponse.success([row for row in completion if row["status"] != "submitted"])


@router.get("/{task_id}/statistics")
def task_statistics(task_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")
    total = len(target_student_ids(db, task))
    submitted = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.task_id == task_id, AnswerSheet.status == "submitted").scalar() or 0
    return APIResponse.success({
        "expected_count": total,
        "completed_count": submitted,
        "uncompleted_count": max(total - submitted, 0),
        "completion_rate": round(submitted / max(total, 1) * 100, 1) if total else 0,
    })
