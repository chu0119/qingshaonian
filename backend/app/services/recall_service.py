"""答卷打回（recall）共享逻辑"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta

from ..models.task import AnswerSheet, AnswerRecord, Task
from ..models.user import User
from ..models.risk import RiskAlert, ScoringResult, QualityAssessment, Intervention


def recall_answer_sheet(db: Session, task_id: int, student_id: int) -> AnswerSheet:
    """
    打回已提交的答卷，清除关联数据，重置答卷状态。

    Raises:
        HTTPException 404: 任务或答卷不存在
        HTTPException 400: 答卷未提交或参数缺失
    Returns:
        重置后的 AnswerSheet
    """
    if not student_id:
        raise HTTPException(status_code=400, detail="请指定学生ID")

    sheet = db.query(AnswerSheet).filter(
        AnswerSheet.task_id == task_id, AnswerSheet.student_id == student_id
    ).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="该学生无此任务的答卷")
    if sheet.status != "submitted":
        raise HTTPException(status_code=400, detail="只能打回已提交的答卷")

    # 清除答题记录、评分、质检、风险预警及干预
    db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet.id).delete()
    db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).delete()
    db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == sheet.id).delete()
    alert_ids = [a.id for a in db.query(RiskAlert.id).filter(RiskAlert.answer_sheet_id == sheet.id).all()]
    if alert_ids:
        db.query(Intervention).filter(Intervention.risk_alert_id.in_(alert_ids)).delete(synchronize_session=False)
    db.query(RiskAlert).filter(RiskAlert.answer_sheet_id == sheet.id).delete()

    # 重置答卷状态
    sheet.status = "in_progress"
    sheet.submitted_at = None
    sheet.total_duration_seconds = None
    sheet.started_at = datetime.now(timezone(timedelta(hours=8)))
    db.commit()
    return sheet
