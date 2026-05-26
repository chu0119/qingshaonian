from pydantic import BaseModel, Field
from typing import Optional


class OptionCreate(BaseModel):
    content: str
    score: int = 0
    sort_order: int = 0
    is_risk_option: bool = False


class OptionUpdate(BaseModel):
    content: str
    score: int = 0
    sort_order: int = 0
    is_risk_option: bool = False


class QuestionCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    type: str = "single_choice"
    required: bool = True
    sort_order: int = 0
    dimension: Optional[str] = ""
    risk_tag: Optional[str] = ""
    is_reverse: bool = False
    is_attention_check: bool = False
    attention_correct_answer: Optional[str] = ""
    risk_threshold: Optional[int] = None
    options: list[OptionCreate] = []


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    required: Optional[bool] = None
    sort_order: Optional[int] = None
    dimension: Optional[str] = None
    risk_tag: Optional[str] = None
    is_reverse: Optional[bool] = None
    is_attention_check: Optional[bool] = None
    attention_correct_answer: Optional[str] = None
    risk_threshold: Optional[int] = None
    options: Optional[list[OptionCreate]] = None


class ContradictionGroupCreate(BaseModel):
    question_a_id: int
    question_b_id: int
    relation_type: str = "opposite"
    max_score_diff: int = 3
    description: Optional[str] = ""


class QuestionnaireCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "custom"
    applicable_grades: Optional[str] = ""


class QuestionnaireUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    applicable_grades: Optional[str] = None
    status: Optional[str] = None
