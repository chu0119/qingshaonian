from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, JSON, DateTime, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ScoringResult(Base, TimestampMixin):
    __tablename__ = "scoring_results"
    answer_sheet_id = Column(Integer, ForeignKey("answer_sheets.id"), nullable=False, unique=True)
    total_score = Column(Float, default=0)
    dimension_scores = Column(JSON, default=dict)
    risk_level = Column(String(20), default="low")
    risk_type = Column(String(100), default="")
    risk_description = Column(Text, default="")
    triggered_rules = Column(JSON, default=list)


class QualityAssessment(Base, TimestampMixin):
    __tablename__ = "quality_assessments"
    answer_sheet_id = Column(Integer, ForeignKey("answer_sheets.id"), nullable=False, unique=True)
    quality_level = Column(String(20), default="normal")
    validity = Column(String(20), default="valid")
    quality_score = Column(Float, default=100)
    total_duration_seconds = Column(Integer, default=0)
    fast_question_count = Column(Integer, default=0)
    contradiction_count = Column(Integer, default=0)
    contradiction_details = Column(JSON, default=list)
    reverse_consistency_score = Column(Float, default=100)
    attention_passed = Column(Boolean, default=True)
    attention_details = Column(JSON, default=list)
    max_consecutive_same = Column(Integer, default=0)
    same_option_ratio = Column(Float, default=0)
    pattern_detected = Column(Boolean, default=False)
    suggest_retest = Column(Boolean, default=False)
    details = Column(JSON, default=dict)


class RiskAlert(Base, TimestampMixin):
    __tablename__ = "risk_alerts"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer_sheet_id = Column(Integer, ForeignKey("answer_sheets.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    risk_level = Column(String(20), default="low")
    risk_type = Column(String(100), default="")
    trigger_method = Column(String(50), default="total_score")
    trigger_detail = Column(JSON, default=dict)
    assigned_teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")
    due_at = Column(DateTime, nullable=True)
    latest_handled_at = Column(DateTime, nullable=True)
    closed_reason = Column(Text, default="")
    source_rule_version = Column(String(50), default="v1")


class Intervention(Base, TimestampMixin):
    __tablename__ = "interventions"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    risk_alert_id = Column(Integer, ForeignKey("risk_alerts.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    intervention_time = Column(DateTime, nullable=True)
    method = Column(String(50), default="other")
    content = Column(Text, default="")
    result = Column(Text, default="")
    follow_up_suggestion = Column(Text, default="")
    need_follow_up = Column(Boolean, default=False)
    next_follow_up_time = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    follow_up_status = Column(String(20), default="none")
    closed_at = Column(DateTime, nullable=True)
    attachments = Column(JSON, default=list)
    visibility_scope = Column(String(30), default="school")
