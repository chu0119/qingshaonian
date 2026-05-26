from pydantic import BaseModel
from typing import Optional
from datetime import date


class ClassCreate(BaseModel):
    grade_id: int
    name: str
    head_teacher_id: Optional[int] = None
    counselor_id: Optional[int] = None
    status: bool = True


class ClassUpdate(BaseModel):
    grade_id: Optional[int] = None
    name: Optional[str] = None
    head_teacher_id: Optional[int] = None
    counselor_id: Optional[int] = None
    status: Optional[bool] = None


class ClassInfo(BaseModel):
    id: int
    school_id: int
    grade_id: int
    name: str
    head_teacher_id: Optional[int] = None
    counselor_id: Optional[int] = None
    status: bool
    grade_name: Optional[str] = ""
    head_teacher_name: Optional[str] = ""
    counselor_name: Optional[str] = ""
    student_count: int = 0

    class Config:
        from_attributes = True
