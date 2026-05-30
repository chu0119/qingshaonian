from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional, Any


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
    title: str = Field(..., min_length=1, max_length=200, description="问卷标题")
    description: Optional[str] = ""
    category: Optional[str] = "custom"
    applicable_grades: Optional[str] = ""
    disclaimer: Optional[str] = ""
    dimensions: list[dict[str, Any]] = []
    scoring_rule: dict[str, Any] = {}
    risk_rules: dict[str, Any] = {}
    quality_rules: dict[str, Any] = {}
    source_type: Optional[str] = "school_custom"

    @validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('问卷标题不能为空')
        return v.strip()


class QuestionnaireUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    applicable_grades: Optional[str] = None
    status: Optional[str] = None
    disclaimer: Optional[str] = None
    dimensions: Optional[list[dict[str, Any]]] = None
    scoring_rule: Optional[dict[str, Any]] = None
    risk_rules: Optional[dict[str, Any]] = None
    quality_rules: Optional[dict[str, Any]] = None
    source_type: Optional[str] = None
