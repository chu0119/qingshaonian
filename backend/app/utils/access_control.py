from sqlalchemy.orm import Session
from datetime import datetime

from ..models.task import Task
from ..models.user import Class, TeacherClass, User


TEACHER_ROLES = {"teacher", "counselor"}
TASK_FILLABLE_STATUSES = {"in_progress", "active"}


def teacher_class_ids(db: Session, user: User) -> set[int]:
    if user.role not in TEACHER_ROLES:
        return set()

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
            Class.school_id == user.school_id,
            ((Class.head_teacher_id == user.id) | (Class.counselor_id == user.id)),
        )
        .all()
    }
    return assigned | direct


def can_access_class(db: Session, user: User, class_id: int | None) -> bool:
    if not class_id:
        return False
    klass = db.query(Class).filter(Class.id == class_id).first()
    if not klass or klass.school_id != user.school_id:
        return False
    if user.role == "school_admin":
        return True
    return klass.id in teacher_class_ids(db, user)


def can_access_student(db: Session, user: User, student: User | None) -> bool:
    if not student or student.school_id != user.school_id or student.role != "student":
        return False
    if user.role == "school_admin":
        return True
    if user.role in TEACHER_ROLES:
        return bool(student.class_id and student.class_id in teacher_class_ids(db, user))
    return user.role == "student" and student.id == user.id


def task_matches_student(student: User, task: Task) -> bool:
    target_ids = set(task.target_ids or [])
    if task.school_id != student.school_id or task.status not in TASK_FILLABLE_STATUSES:
        return False
    now = datetime.now()
    if task.start_time and task.start_time > now:
        return False
    if task.end_time and task.end_time < now:
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
    if not task or task.school_id != user.school_id:
        return False
    if user.role == "school_admin":
        return True
    if user.role not in TEACHER_ROLES:
        return False

    class_ids = teacher_class_ids(db, user)
    target_ids = set(task.target_ids or [])
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
                User.school_id == user.school_id,
                User.class_id.in_(class_ids),
                User.role == "student",
            )
            .first()
            is not None
        )
    return False
