from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum


class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    TRUE_FALSE = "true_false"
    SCALE = "scale"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class QuestionnaireCategory(str, enum.Enum):
    MENTAL_HEALTH = "mental_health"
    BULLYING = "bullying"
    INTERNET_ADDICTION = "internet_addiction"
    FAMILY_RELATIONSHIP = "family_relationship"
    SAFETY_AWARENESS = "safety_awareness"
    INTERPERSONAL = "interpersonal"
    ACADEMIC_PRESSURE = "academic_pressure"
    CUSTOM = "custom"


class Questionnaire(Base, TimestampMixin):
    __tablename__ = "questionnaires"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category = Column(String(50), default="custom")
    applicable_grades = Column(String(200), default="")
    is_builtin = Column(Boolean, default=False)
    status = Column(String(20), default="draft")  # draft / active / inactive
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    locked_after_publish = Column(Boolean, default=False)
    source_questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=True)
    rule_version = Column(String(50), default="v1")

    questions = relationship("Question", back_populates="questionnaire", order_by="Question.sort_order")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(String(500), default="")
    type = Column(String(20), nullable=False, default=QuestionType.SINGLE_CHOICE)
    required = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    dimension = Column(String(50), default="")
    risk_tag = Column(String(50), default="")
    is_reverse = Column(Boolean, default=False)
    is_attention_check = Column(Boolean, default=False)
    attention_correct_answer = Column(String(500), default="")
    risk_threshold = Column(Integer, nullable=True)

    questionnaire = relationship("Questionnaire", back_populates="questions")
    options = relationship("Option", back_populates="question", order_by="Option.sort_order")


class Option(Base, TimestampMixin):
    __tablename__ = "options"
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    content = Column(String(500), nullable=False)
    score = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    is_risk_option = Column(Boolean, default=False)

    question = relationship("Question", back_populates="options")


class ContradictionGroup(Base, TimestampMixin):
    __tablename__ = "contradiction_groups"
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    question_a_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_b_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    relation_type = Column(String(20), default="opposite")  # opposite / positive_correlated / mutually_exclusive
    max_score_diff = Column(Integer, default=3)
    description = Column(String(500), default="")

    questionnaire = relationship("Questionnaire")
    question_a = relationship("Question", foreign_keys=[question_a_id])
    question_b = relationship("Question", foreign_keys=[question_b_id])
