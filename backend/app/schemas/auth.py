from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    school_id: int | None
    username: str
    real_name: str
    role: str
    teacher_type: str | None
    gender: str
    phone: str
    student_no: str
    grade_id: int | None
    class_id: int | None
    must_change_password: bool

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    new_password: str
