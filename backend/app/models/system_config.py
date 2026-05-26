from sqlalchemy import Column, String, Integer, Text
from .base import Base, TimestampMixin


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_configs"
    school_id = Column(Integer, nullable=True)
    config_key = Column(String(100), nullable=False)
    config_value = Column(Text, default="")
    description = Column(String(500), default="")
