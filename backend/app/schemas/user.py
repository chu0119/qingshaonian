from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class UserCreate(BaseModel):
    school_id: Optional[int] = 0
    username: str
    password: Optional[str] = None
    real_name: str
    role: Optional[str] = None
    teacher_type: Optional[str] = None
    gender: Optional[str] = ""
    phone: Optional[str] = ""
    student_no: Optional[str] = ""
    birth_date: Optional[date] = None
    grade_id: Optional[int] = None
    class_id: Optional[int] = None
    status: bool = True


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    teacher_type: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    student_no: Optional[str] = None
    birth_date: Optional[date] = None
    grade_id: Optional[int] = None
    class_id: Optional[int] = None
    status: Optional[bool] = None


class UserInfo(BaseModel):
    id: int
    school_id: Optional[int] = None
    username: str
    real_name: str
    role: str
    teacher_type: Optional[str] = None
    gender: str
    phone: str
    student_no: str
    birth_date: Optional[date] = None
    grade_id: Optional[int] = None
    class_id: Optional[int] = None
    status: bool
    grade_name: Optional[str] = ""
    class_name: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudentImportRow(BaseModel):
    student_no: str
    name: str
    gender: str = ""
    grade_name: str = ""
    class_name: str = ""
    birth_date: Optional[str] = None
    phone: Optional[str] = ""


class ImportResult(BaseModel):
    success_count: int = 0
    fail_count: int = 0
    errors: list[str] = []
