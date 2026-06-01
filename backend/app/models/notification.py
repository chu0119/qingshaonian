from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, func
from .base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="接收用户")
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="发送用户（系统消息为空）")
    type = Column(String(50), nullable=False, default="system", comment="消息类型: task/risk/intervention/system")
    title = Column(String(200), nullable=False, comment="消息标题")
    content = Column(Text, nullable=True, comment="消息内容")
    related_type = Column(String(50), nullable=True, comment="关联对象类型: task/risk/intervention/answer_sheet")
    related_id = Column(Integer, nullable=True, comment="关联对象ID")
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
