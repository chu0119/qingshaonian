from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.risk import QualityAssessment
from ..models.user import User
from ..dependencies import require_role
from ..utils.access_control import can_access_student, can_access_task
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/quality", tags=["答题质量"])


@router.get("/{answer_sheet_id}")
def get_quality(answer_sheet_id: int, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    from ..models.task import AnswerSheet
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == answer_sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="未找到质量评估")
    student = db.query(User).filter(User.id == sheet.student_id).first()
    if not can_access_student(db, user, student):
        raise HTTPException(status_code=404, detail="未找到质量评估")

    q = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == answer_sheet_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="未找到质量评估")

    quality_labels = {"normal": "正常", "mild_anomaly": "轻度异常", "moderate_anomaly": "中度异常", "severe_anomaly": "高度异常"}
    validity_labels = {"valid": "有效", "basically_valid": "基本有效", "questionable": "存疑", "not_recommended": "不建议纳入核心统计"}
    details = q.details or {}

    return APIResponse.success({
        "quality_level": q.quality_level,
        "quality_level_label": quality_labels.get(q.quality_level, q.quality_level),
        "quality_score": q.quality_score,
        "validity": q.validity,
        "validity_label": validity_labels.get(q.validity, q.validity),
        "total_duration_seconds": q.total_duration_seconds,
        "total_duration_formatted": f"{q.total_duration_seconds // 60}分{q.total_duration_seconds % 60}秒" if q.total_duration_seconds else "未知",
        "fast_question_count": q.fast_question_count,
        "contradiction_count": q.contradiction_count,
        "contradiction_details": q.contradiction_details or [],
        "attention_passed": q.attention_passed,
        "attention_details": q.attention_details or [],
        "max_consecutive_same": q.max_consecutive_same,
        "same_option_ratio": round(q.same_option_ratio * 100, 1) if q.same_option_ratio else 0,
        "pattern_detected": q.pattern_detected,
        "suggest_retest": q.suggest_retest,
        "deductions": details.get("deductions", []),
        "fast_ratio": details.get("fast_ratio", 0),
        "pattern_detail": details.get("pattern_detail", ""),
        "min_expected_time": details.get("min_expected_time", 0),
    })


@router.get("/statistics/task/{task_id}")
def task_quality_stats(task_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    from ..models.task import Task, AnswerSheet
    task = db.query(Task).filter(Task.id == task_id).first()
    if not can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="任务不存在")

    sheets = db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id, AnswerSheet.status == "submitted").all()
    sheet_ids = [s.id for s in sheets]
    if not sheet_ids:
        return APIResponse.success({"total": 0, "by_level": [], "by_validity": []})

    qs = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).all()

    by_level = {}
    by_validity = {}
    retest_count = 0
    for q in qs:
        by_level[q.quality_level] = by_level.get(q.quality_level, 0) + 1
        by_validity[q.validity] = by_validity.get(q.validity, 0) + 1
        if q.suggest_retest:
            retest_count += 1

    return APIResponse.success({
        "total": len(sheets),
        "assessed": len(qs),
        "by_level": [{"level": k, "count": v} for k, v in by_level.items()],
        "by_validity": [{"validity": k, "count": v} for k, v in by_validity.items()],
        "suggest_retest_count": retest_count,
        "effective_rate": round(by_validity.get("valid", 0) / max(len(qs), 1) * 100, 1) if qs else 0,
    })


@router.get("/statistics/school")
def school_quality_stats(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.task import Task, AnswerSheet
    task_ids = [t.id for t in db.query(Task).filter(Task.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).all()]
    if not task_ids:
        return APIResponse.success({"total": 0})

    sheet_ids = [s.id for s in db.query(AnswerSheet).filter(AnswerSheet.task_id.in_(task_ids), AnswerSheet.status == "submitted").all()]
    if not sheet_ids:
        return APIResponse.success({"total": 0})

    qs = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).all()

    by_level = {}
    retest = 0
    for q in qs:
        by_level[q.quality_level] = by_level.get(q.quality_level, 0) + 1
        if q.suggest_retest: retest += 1

    normal = by_level.get("normal", 0)
    return APIResponse.success({
        "total": len(sheet_ids),
        "by_level": [{"level": k, "count": v} for k, v in by_level.items()],
        "suggest_retest_count": retest,
        "effective_rate": round(normal / max(len(qs), 1) * 100, 1) if qs else 0,
    })
