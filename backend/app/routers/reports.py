from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.risk import RiskAlert, Intervention, QualityAssessment, ScoringResult
from ..models.questionnaire import Questionnaire
from ..dependencies import require_role
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


@router.get("/school-overview")
def school_overview(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    grades = db.query(Grade).filter(Grade.school_id == school_id, Grade.status == True).order_by(Grade.sort_order).all()
    grade_data = []
    total_students = 0
    total_completed = 0

    for g in grades:
        classes = db.query(Class).filter(Class.grade_id == g.id).all()
        class_data = []
        grade_students = 0
        grade_completed = 0

        for c in classes:
            student_ids_query = db.query(User.id).filter(User.class_id == c.id, User.role == "student")
            student_count = db.query(func.count(User.id)).filter(User.class_id == c.id, User.role == "student").scalar()
            # 统计去重学生数，避免同一学生多份答卷导致完成率超100%
            completed_count = db.query(func.count(func.distinct(AnswerSheet.student_id))).filter(
                AnswerSheet.student_id.in_(student_ids_query),
                AnswerSheet.status == "submitted"
            ).scalar()
            class_data.append({
                "class_name": c.name,
                "student_count": student_count,
                "completed_count": completed_count,
                "completion_rate": round(completed_count / max(student_count, 1) * 100, 1),
            })
            grade_students += student_count
            grade_completed += completed_count

        grade_data.append({
            "grade_name": g.name,
            "student_count": grade_students,
            "completed_count": grade_completed,
            "completion_rate": round(grade_completed / max(grade_students, 1) * 100, 1),
            "classes": class_data,
        })
        total_students += grade_students
        total_completed += grade_completed

    return APIResponse.success({
        "grades": grade_data,
        "total_students": total_students,
        "total_completed": total_completed,
        "overall_completion_rate": round(total_completed / max(total_students, 1) * 100, 1),
    })


@router.get("/risk-summary")
def risk_summary(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    total = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar()

    by_level = db.query(RiskAlert.risk_level, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id
    ).group_by(RiskAlert.risk_level).all()

    by_status = db.query(RiskAlert.status, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id
    ).group_by(RiskAlert.status).all()

    level_labels = {"low": "关注", "medium": "预警", "high": "警告", "urgent": "危急"}
    status_labels = {"pending": "待处理", "processing": "处理中", "resolved": "已解决", "closed": "已关闭"}

    level_data = [{
        "level": l,
        "label": level_labels.get(l, l),
        "count": c,
        "percentage": round(c / max(total, 1) * 100, 1),
    } for l, c in by_level]

    status_data = [{
        "status": s,
        "label": status_labels.get(s, s),
        "count": c,
        "percentage": round(c / max(total, 1) * 100, 1),
    } for s, c in by_status]

    return APIResponse.success({
        "total": total,
        "by_level": level_data,
        "by_status": status_data,
    })


@router.get("/student-longitudinal/{student_id}")
def student_longitudinal(student_id: int, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student or student.school_id != school_id:
        raise HTTPException(status_code=404, detail="学生不存在")
    if user.role in ("teacher", "counselor"):
        if not can_access_student(db, user, student):
            raise HTTPException(status_code=403, detail="无权限查看该学生")

    sheets = db.query(AnswerSheet).filter(
        AnswerSheet.student_id == student_id, AnswerSheet.status == "submitted"
    ).order_by(AnswerSheet.submitted_at).all()

    results = []
    for sheet in sheets:
        sr = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).first()
        q = db.query(Questionnaire).filter(Questionnaire.id == sheet.questionnaire_id).first()
        results.append({
            "answer_sheet_id": sheet.id,
            "task_id": sheet.task_id,
            "questionnaire_title": q.title if q else "",
            "submitted_at": sheet.submitted_at.isoformat() if sheet.submitted_at else None,
            "total_score": sr.total_score if sr else None,
            "dimension_scores": sr.dimension_scores if sr else {},
            "risk_level": sr.risk_level if sr else None,
        })

    return APIResponse.success({
        "student_id": student.id,
        "student_name": student.real_name,
        "records": results,
    })


@router.get("/group-summary")
def group_summary(
    scope: str = Query("grade", description="class | grade | school"),
    scope_id: int = Query(None, description="班级或年级ID"),
    user: User = Depends(require_role("school_admin", "platform_admin")),
    db: Session = Depends(get_db),
):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)

    if scope == "school":
        student_q = db.query(User.id).filter(User.school_id == school_id, User.role == "student", User.status == True)
        group_name = "全校"
    elif scope == "grade" and scope_id:
        classes = db.query(Class).filter(Class.grade_id == scope_id).all()
        class_ids = [c.id for c in classes]
        student_q = db.query(User.id).filter(User.class_id.in_(class_ids), User.role == "student", User.status == True)
        grade = db.query(Grade).filter(Grade.id == scope_id).first()
        group_name = grade.name if grade else "年级"
    elif scope == "class" and scope_id:
        student_q = db.query(User.id).filter(User.class_id == scope_id, User.role == "student", User.status == True)
        cls = db.query(Class).filter(Class.id == scope_id).first()
        group_name = cls.name if cls else "班级"
    else:
        raise HTTPException(status_code=400, detail="请指定 scope 和 scope_id")

    student_ids = [s[0] for s in student_q.all()]
    if not student_ids:
        return APIResponse.success({"group_name": group_name, "student_count": 0, "avg_total_score": 0, "dimension_avg": {}, "risk_distribution": {}, "completion_rate": 0})

    student_count = len(student_ids)
    sheets = db.query(AnswerSheet).filter(
        AnswerSheet.student_id.in_(student_ids), AnswerSheet.status == "submitted"
    ).all()
    sheet_ids = [s.id for s in sheets]
    completed_students = len(set(s.student_id for s in sheets))

    scoring_results = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).all() if sheet_ids else []

    avg_total = 0
    dim_accum: dict = {}
    risk_dist: dict = {"low": 0, "medium": 0, "high": 0, "urgent": 0}

    for sr in scoring_results:
        avg_total += sr.total_score or 0
        if sr.risk_level in risk_dist:
            risk_dist[sr.risk_level] += 1
        if sr.dimension_scores and isinstance(sr.dimension_scores, dict):
            for dim_key, dim_val in sr.dimension_scores.items():
                if isinstance(dim_val, (int, float)):
                    dim_accum[dim_key] = dim_accum.get(dim_key, 0) + dim_val

    n = len(scoring_results) or 1
    avg_total = round(avg_total / n, 1)
    dim_avg = {k: round(v / n, 1) for k, v in dim_accum.items()}

    return APIResponse.success({
        "group_name": group_name,
        "student_count": student_count,
        "completed_count": completed_students,
        "avg_total_score": avg_total,
        "dimension_avg": dim_avg,
        "risk_distribution": risk_dist,
        "completion_rate": round(completed_students / max(student_count, 1) * 100, 1),
    })


@router.get("/audit-logs")
def school_audit_logs(
    page: int = Query(1), page_size: int = Query(20),
    action: str = Query(""), start_date: str = Query(""), end_date: str = Query(""),
    user: User = Depends(require_role("school_admin", "platform_admin")), db: Session = Depends(get_db),
):
    """学校管理员查看本校操作日志"""
    from ..models.audit import OperationLog
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    q = db.query(OperationLog).filter(OperationLog.school_id == school_id)
    if action:
        q = q.filter(OperationLog.action == action)
    if start_date:
        q = q.filter(OperationLog.operation_time >= start_date)
    if end_date:
        from datetime import datetime
        end_dt = datetime.fromisoformat(end_date) + __import__('datetime').timedelta(days=1)
        q = q.filter(OperationLog.operation_time < end_dt.isoformat())
    total = q.count()
    logs = q.order_by(OperationLog.operation_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({
        "total": total,
        "items": [{
            "id": l.id,
            "operator_name": l.operator_name,
            "operator_role": l.operator_role,
            "module": l.module,
            "action": l.action,
            "object_type": l.object_type,
            "object_name": l.object_name,
            "operation_time": l.operation_time.isoformat() if l.operation_time else None,
            "request_ip": l.request_ip,
            "result": l.result,
            "detail": l.detail,
        } for l in logs],
    })
