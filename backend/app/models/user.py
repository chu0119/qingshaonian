from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Date, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum


class UserRole(str, enum.Enum):
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    COUNSELOR = "counselor"
    STUDENT = "student"
    PLATFORM_ADMIN = "platform_admin"


class TeacherType(str, enum.Enum):
    HEAD_TEACHER = "head_teacher"
    COUNSELOR = "counselor"
    GRADE_DIRECTOR = "grade_director"
    MORAL_EDU = "moral_edu"
    NORMAL = "normal"


class School(Base, TimestampMixin):
    __tablename__ = "schools"
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    address = Column(String(255), default="")
    phone = Column(String(20), default="")
    status = Column(Boolean, default=True)

    users = relationship("User", back_populates="school")
    grades = relationship("Grade", back_populates="school")
    classes = relationship("Class", back_populates="school")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.STUDENT)
    teacher_type = Column(String(20), nullable=True)
    gender = Column(String(4), default="")
    phone = Column(String(20), default="")
    student_no = Column(String(50), default="")
    birth_date = Column(Date, nullable=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    status = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)

    school = relationship("School", back_populates="users")
    grade = relationship("Grade", foreign_keys=[grade_id])
    class_ = relationship("Class", foreign_keys=[class_id], back_populates="students")


class Grade(Base, TimestampMixin):
    __tablename__ = "grades"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, default=0)
    status = Column(Boolean, default=True)

    school = relationship("School", back_populates="grades")
    classes = relationship("Class", back_populates="grade")


class Class(Base, TimestampMixin):
    __tablename__ = "classes"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    name = Column(String(100), nullable=False)
    head_teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    counselor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Boolean, default=True)

    school = relationship("School", back_populates="classes")
    grade = relationship("Grade", back_populates="classes")
    head_teacher = relationship("User", foreign_keys=[head_teacher_id])
    counselor = relationship("User", foreign_keys=[counselor_id])
    students = relationship("User", foreign_keys="User.class_id", back_populates="class_")


class TeacherClass(Base, TimestampMixin):
    __tablename__ = "teacher_classes"
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
