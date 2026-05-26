from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    name = Column(String(200), nullable=False)
    target_type = Column(String(20), default="class")  # all / grade / class / student
    target_ids = Column(JSON, default=list)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    extended_at = Column(DateTime, nullable=True)
    reminder_strategy = Column(JSON, default=dict)
    target_snapshot = Column(JSON, default=dict)
    description = Column(Text, default="")
    is_anonymous = Column(Boolean, default=False)
    allow_edit = Column(Boolean, default=False)
    shuffle_questions = Column(Boolean, default=False)
    shuffle_options = Column(Boolean, default=False)
    enable_quality_check = Column(Boolean, default=True)
    enable_reminder = Column(Boolean, default=False)
    status = Column(String(20), default="draft")  # draft / pending / active / ended / closed
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    questionnaire = relationship("Questionnaire", foreign_keys=[questionnaire_id], lazy="joined")


class AnswerSheet(Base, TimestampMixin):
    __tablename__ = "answer_sheets"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    question_order = Column(JSON, default=list)
    option_orders = Column(JSON, default=dict)
    status = Column(String(20), default="in_progress")  # in_progress / submitted
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    total_duration_seconds = Column(Integer, default=0)
    ip_address = Column(String(50), default="")
    user_agent = Column(String(500), default="")


class AnswerRecord(Base, TimestampMixin):
    __tablename__ = "answer_records"
    answer_sheet_id = Column(Integer, ForeignKey("answer_sheets.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_type = Column(String(20), nullable=False)
    answer_content = Column(JSON, default=None)
    score = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    displayed_order = Column(Integer, default=0)
    selected_display_index = Column(Integer, default=0)
