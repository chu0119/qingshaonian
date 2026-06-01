from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.audit import OperationLog
from ..models.external import AIAnalysisLog, SMSLog
from ..models.risk import QualityAssessment, RiskAlert
from ..models.task import AnswerSheet, Task
from ..models.user import Class, School, User

OPEN_RISK_STATUSES = ("pending", "viewed", "processing", "follow_up")
DONE_RISK_STATUSES = ("completed", "closed", "resolved")
ACTIVE_TASK_STATUSES = ("not_started", "in_progress")


def target_snapshot_student_ids(task: Task) -> list[int]:
    snapshot = task.target_snapshot or {}
    ids = snapshot.get("student_ids")
    if task.status != "draft" and isinstance(ids, list):
        return [int(sid) for sid in ids if str(sid).isdigit()]
    return []


def school_metrics(db: Session, school_id: int) -> dict:
    students = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role == "student").scalar() or 0
    teachers = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role.in_(["teacher", "counselor"])).scalar() or 0
    classes = db.query(func.count(Class.id)).filter(Class.school_id == school_id).scalar() or 0
    tasks = db.query(func.count(Task.id)).filter(Task.school_id == school_id).scalar() or 0
    sheets = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.school_id == school_id, AnswerSheet.status == "submitted").scalar() or 0
    if sheets == 0:
        sheets = db.query(func.count(AnswerSheet.id)).join(Task, Task.id == AnswerSheet.task_id).filter(Task.school_id == school_id, AnswerSheet.status == "submitted").scalar() or 0

    risks = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar() or 0
    pending_risks = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id, RiskAlert.status.in_(OPEN_RISK_STATUSES)).scalar() or 0
    handled_risks = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id, RiskAlert.status.in_(DONE_RISK_STATUSES)).scalar() or 0
    ai_calls = db.query(func.count(AIAnalysisLog.id)).filter(AIAnalysisLog.school_id == school_id).scalar() or 0
    sms_sends = db.query(func.count(SMSLog.id)).filter(SMSLog.school_id == school_id).scalar() or 0

    # 完成率：按每个任务的学生完成率取平均
    active_tasks = db.query(Task).filter(Task.school_id == school_id, Task.status.notin_(["draft", "archived"])).all()
    task_rates = []
    expected = 0
    completed = 0
    for task in active_tasks:
        target_ids = target_student_ids(db, task)
        task_expected = len(target_ids)
        task_completed = db.query(func.count(AnswerSheet.id)).filter(
            AnswerSheet.task_id == task.id, AnswerSheet.status == "submitted"
        ).scalar() or 0
        expected += task_expected
        completed += task_completed
        if task_expected > 0:
            task_rates.append(task_completed / task_expected * 100)
    completion_rate = round(sum(task_rates) / max(len(task_rates), 1), 1) if task_rates else 0

    valid = (
        db.query(func.count(QualityAssessment.id))
        .join(AnswerSheet, AnswerSheet.id == QualityAssessment.answer_sheet_id)
        .filter(AnswerSheet.school_id == school_id, QualityAssessment.validity.in_(["valid", "basically_valid"]))
        .scalar()
        or 0
    )
    quality_total = (
        db.query(func.count(QualityAssessment.id))
        .join(AnswerSheet, AnswerSheet.id == QualityAssessment.answer_sheet_id)
        .filter(AnswerSheet.school_id == school_id)
        .scalar()
        or 0
    )

    return {
        "student_count": students,
        "teacher_count": teachers,
        "class_count": classes,
        "task_count": tasks,
        "answer_sheet_count": sheets,
        "risk_count": risks,
        "pending_risk_count": pending_risks,
        "handled_risk_count": handled_risks,
        "ai_call_count": ai_calls,
        "sms_send_count": sms_sends,
        "expected_count": expected,
        "completed_count": completed,
        "uncompleted_count": max(expected - completed, 0),
        "completion_rate": completion_rate,
        "risk_rate": round(risks / max(students, 1) * 100, 1) if students else 0,
        "valid_answer_rate": round(valid / max(quality_total, 1) * 100, 1) if quality_total else 0,
        "intervention_completion_rate": round(handled_risks / max(risks, 1) * 100, 1) if risks else 0,
    }


def target_student_ids(db: Session, task: Task) -> list[int]:
    snapshot_ids = target_snapshot_student_ids(task)
    if snapshot_ids:
        return snapshot_ids
    q = db.query(User.id).filter(User.school_id == task.school_id, User.role == "student", User.status == True)
    target_ids = task.target_ids or []
    if task.target_type == "grade":
        q = q.filter(User.grade_id.in_(target_ids))
    elif task.target_type == "class":
        q = q.filter(User.class_id.in_(target_ids))
    elif task.target_type == "student":
        q = q.filter(User.id.in_(target_ids))
    return [row[0] for row in q.all()]


def recent_school_activity(db: Session, school_id: int) -> datetime | None:
    latest_login = db.query(func.max(User.last_login_at)).filter(User.school_id == school_id).scalar()
    latest_task = db.query(func.max(Task.updated_at)).filter(Task.school_id == school_id).scalar()
    latest_answer = (
        db.query(func.max(AnswerSheet.submitted_at))
        .join(Task, Task.id == AnswerSheet.task_id)
        .filter(Task.school_id == school_id)
        .scalar()
    )
    latest_risk = db.query(func.max(RiskAlert.updated_at)).filter(RiskAlert.school_id == school_id).scalar()
    return max([dt for dt in [latest_login, latest_task, latest_answer, latest_risk] if dt], default=None)


def platform_summary(db: Session) -> dict:
    schools = db.query(School).all()
    rows = []
    for school in schools:
        metrics = school_metrics(db, school.id)
        active_at = recent_school_activity(db, school.id)
        rows.append({"id": school.id, "name": school.name, "code": school.code, "status": school.status, "last_active_at": active_at, **metrics})

    # 风险等级分布（全局）
    risk_level_dist = {}
    for level in ["low", "medium", "high", "urgent"]:
        risk_level_dist[level] = db.query(func.count(RiskAlert.id)).filter(RiskAlert.risk_level == level).scalar() or 0

    # 全局完成率：按学生维度计算（已完成独立答卷的学生 / 有任务的学生总数）
    all_tasks = db.query(Task).filter(Task.status.notin_(["draft", "archived"])).all()
    total_expected = 0
    total_completed = 0
    for task in all_tasks:
        target_ids = target_student_ids(db, task)
        total_expected += len(target_ids)
        total_completed += db.query(func.count(AnswerSheet.id)).filter(
            AnswerSheet.task_id == task.id, AnswerSheet.status == "submitted"
        ).scalar() or 0
    global_completion_rate = round(total_completed / max(total_expected, 1) * 100, 1) if total_expected else 0

    return {
        "school_total": len(schools),
        "enabled_school_total": len([s for s in schools if s.status]),
        "disabled_school_total": len([s for s in schools if not s.status]),
        "student_total": sum(r["student_count"] for r in rows),
        "teacher_total": sum(r["teacher_count"] for r in rows),
        "task_total": sum(r["task_count"] for r in rows),
        "answer_sheet_total": sum(r["answer_sheet_count"] for r in rows),
        "risk_alert_total": sum(r["risk_count"] for r in rows),
        "pending_risk_total": sum(r["pending_risk_count"] for r in rows),
        "completion_rate": global_completion_rate,
        "ai_call_total": db.query(func.count(AIAnalysisLog.id)).scalar() or 0,
        "sms_send_total": db.query(func.count(SMSLog.id)).scalar() or 0,
        "risk_level_distribution": risk_level_dist,
        "completion_rankings": sorted(rows, key=lambda r: r["completion_rate"], reverse=True)[:10],
        "risk_rankings": sorted(rows, key=lambda r: r["risk_count"], reverse=True)[:10],
        "risk_handling_rankings": sorted(rows, key=lambda r: r["intervention_completion_rate"], reverse=True)[:10],
        "recent_active_schools": sorted(rows, key=lambda r: r["last_active_at"] or datetime.min, reverse=True)[:10],
    }
