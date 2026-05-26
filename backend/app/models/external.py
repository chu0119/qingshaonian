from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime

from .base import Base, TimestampMixin


class SMSLog(Base, TimestampMixin):
    __tablename__ = "sms_logs"

    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_name = Column(String(100), default="")
    phone = Column(String(30), default="")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    sms_type = Column(String(50), default="")
    template_code = Column(String(100), default="")
    content = Column(Text, default="")
    status = Column(String(30), default="pending")
    failure_reason = Column(Text, default="")
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime, nullable=True)


class AIAnalysisLog(Base, TimestampMixin):
    __tablename__ = "ai_analysis_logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_role = Column(String(30), default="")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    object_type = Column(String(50), default="")
    object_id = Column(String(100), default="")
    analysis_type = Column(String(50), default="")
    status = Column(String(30), default="pending")
    error_message = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    model_name = Column(String(100), default="")
