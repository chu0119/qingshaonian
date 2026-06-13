from sqlalchemy.orm import Session
from datetime import datetime

from ..models.task import Task
from ..models.user import Class, TeacherClass, User


TEACHER_ROLES = {"teacher", "counselor"}
TASK_FILLABLE_STATUSES = {"in_progress", "active", "not_started"}


def effective_school_id(user: User) -> int | None:
    return getattr(user, "_effective_school_id", None) or user.school_id


def is_school_scoped_admin(user: User) -> bool:
    return user.role == "school_admin" or (user.role == "platform_admin" and effective_school_id(user) is not None)


def effective_task_status(task: Task, now: datetime | None = None) -> str:
    now = now or datetime.now()
    if task.status in ("draft", "closed", "archived"):
        return task.status
    if task.end_time and task.end_time < now:
        return "ended"
    if task.start_time and task.start_time > now:
        return "not_started"
    return "in_progress"


def task_is_answerable(task: Task) -> bool:
    return effective_task_status(task) == "in_progress"


def teacher_class_ids(db: Session, user: User) -> set[int]:
    if user.role not in TEACHER_ROLES:
        return set()

    school_id = effective_school_id(user)
    assigned = {
        cid
        for (cid,) in db.query(TeacherClass.class_id)
        .filter(TeacherClass.teacher_id == user.id)
        .all()
    }
    direct = {
        cid
        for (cid,) in db.query(Class.id)
        .filter(
            Class.school_id == school_id,
            ((Class.head_teacher_id == user.id) | (Class.counselor_id == user.id)),
        )
        .all()
    }
    return assigned | direct


def can_access_class(db: Session, user: User, class_id: int | None) -> bool:
    if not class_id:
        return False
    # platform_admin 未进入学校视图时，可跨校访问
    if user.role == "platform_admin" and effective_school_id(user) is None:
        return True
    school_id = effective_school_id(user)
    klass = db.query(Class).filter(Class.id == class_id).first()
    if not klass or klass.school_id != school_id:
        return False
    if is_school_scoped_admin(user):
        return True
    return klass.id in teacher_class_ids(db, user)


def can_access_student(db: Session, user: User, student: User | None) -> bool:
    if not student or student.role != "student":
        return False
    # platform_admin 未进入学校视图时，可跨校访问
    if user.role == "platform_admin" and effective_school_id(user) is None:
        return True
    school_id = effective_school_id(user)
    if student.school_id != school_id:
        return False
    if is_school_scoped_admin(user):
        return True
    if user.role in TEACHER_ROLES:
        return bool(student.class_id and student.class_id in teacher_class_ids(db, user))
    return user.role == "student" and student.id == user.id


def task_matches_student(student: User, task: Task) -> bool:
    target_ids = set(task.target_ids or [])
    if task.school_id != student.school_id or not task_is_answerable(task):
        return False
    if task.target_type == "all":
        return True
    if task.target_type == "grade":
        return bool(student.grade_id and student.grade_id in target_ids)
    if task.target_type == "class":
        return bool(student.class_id and student.class_id in target_ids)
    if task.target_type == "student":
        return student.id in target_ids
    return False


def can_access_task(db: Session, user: User, task: Task | None) -> bool:
    if not task:
        return False
    # platform_admin 未进入学校视图时，可跨校访问
    if user.role == "platform_admin" and effective_school_id(user) is None:
        return True
    school_id = effective_school_id(user)
    if task.school_id != school_id:
        return False
    if is_school_scoped_admin(user):
        return True
    if user.role not in TEACHER_ROLES:
        return False

    class_ids = teacher_class_ids(db, user)
    target_ids = set(task.target_ids or [])
    if task.target_type == "all":
        return bool(class_ids)
    if task.target_type == "class":
        return bool(target_ids & class_ids)
    if task.target_type == "grade":
        assigned_grades = {
            gid
            for (gid,) in db.query(Class.grade_id)
            .filter(Class.id.in_(class_ids), Class.school_id == user.school_id)
            .all()
        }
        return bool(target_ids & assigned_grades)
    if task.target_type == "student":
        return (
            db.query(User.id)
            .filter(
                User.id.in_(target_ids),
                User.school_id == school_id,
                User.class_id.in_(class_ids),
                User.role == "student",
            )
            .first()
            is not None
        )
    return False
