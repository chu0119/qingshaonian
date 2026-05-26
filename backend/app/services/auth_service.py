from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from ..models.user import User, UserRole
from ..utils.password import verify_password, hash_password
from ..utils.jwt import create_access_token
from ..schemas.auth import LoginRequest, LoginResponse, UserInfo

tz = timezone(timedelta(hours=8))


def authenticate(db: Session, request: LoginRequest) -> LoginResponse:
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if not user.status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    user.last_login_at = datetime.now(tz)
    db.commit()

    access_token = create_access_token(data={"user_id": user.id, "role": user.role})

    user_info = UserInfo.model_validate(user)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info,
    )


def get_user_info(user: User) -> UserInfo:
    return UserInfo.model_validate(user)


def change_password(db: Session, user: User, old_password: str, new_password: str):
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()


def reset_user_password(db: Session, user_id: int, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    db.commit()
