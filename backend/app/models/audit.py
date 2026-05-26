from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.sql import func

from .base import Base


class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), default="", index=True)
    user_role = Column(String(20), default="")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    login_time = Column(DateTime, server_default=func.now(), nullable=False)
    login_ip = Column(String(50), default="")
    result = Column(String(20), nullable=False)
    failure_reason = Column(String(500), default="")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operator_name = Column(String(50), default="")
    operator_role = Column(String(20), default="")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    module = Column(String(80), nullable=False)
    action = Column(String(50), nullable=False)
    object_type = Column(String(80), default="")
    object_id = Column(String(80), default="")
    object_name = Column(String(200), default="")
    operation_time = Column(DateTime, server_default=func.now(), nullable=False)
    request_ip = Column(String(50), default="")
    result = Column(String(20), nullable=False)
    detail = Column(Text, default="")
