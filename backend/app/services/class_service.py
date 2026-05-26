from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..models.user import Class, Grade, User, TeacherClass
from ..schemas.class_ import ClassCreate, ClassUpdate, ClassInfo


def list_classes(db: Session, school_id: int, grade_id: int | None = None, page: int = 1, page_size: int = 20):
    q = db.query(Class).filter(Class.school_id == school_id)
    if grade_id:
        q = q.filter(Class.grade_id == grade_id)

    total = q.count()
    items = (
        q.order_by(Class.grade_id, Class.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for c in items:
        student_count = db.query(func.count(User.id)).filter(User.class_id == c.id, User.role == "student").scalar()
        head_teacher = db.query(User).filter(User.id == c.head_teacher_id).first()
        counselor = db.query(User).filter(User.id == c.counselor_id).first()
        grade = db.query(Grade).filter(Grade.id == c.grade_id).first()
        result.append(
            ClassInfo(
                id=c.id,
                school_id=c.school_id,
                grade_id=c.grade_id,
                name=c.name,
                head_teacher_id=c.head_teacher_id,
                counselor_id=c.counselor_id,
                status=c.status,
                grade_name=grade.name if grade else "",
                head_teacher_name=head_teacher.real_name if head_teacher else "",
                counselor_name=counselor.real_name if counselor else "",
                student_count=student_count,
            )
        )

    return {"items": result, "total": total, "page": page, "page_size": page_size, "total_pages": max((total + page_size - 1) // page_size, 1)}


def create_class(db: Session, school_id: int, data: ClassCreate) -> Class:
    c = Class(school_id=school_id, grade_id=data.grade_id, name=data.name, head_teacher_id=data.head_teacher_id, counselor_id=data.counselor_id, status=data.status)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_class(db: Session, class_id: int, data: ClassUpdate) -> Class:
    c = db.query(Class).filter(Class.id == class_id).first()
    if not c:
        raise ValueError("班级不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


def delete_class(db: Session, class_id: int):
    c = db.query(Class).filter(Class.id == class_id).first()
    if c:
        # 移除班级下的学生
        db.query(User).filter(User.class_id == class_id, User.role == "student").update({User.class_id: None})
        db.delete(c)
        db.commit()


def get_my_classes(db: Session, teacher_id: int):
    """获取教师负责的班级"""
    tc_records = db.query(TeacherClass).filter(TeacherClass.teacher_id == teacher_id).all()
    class_ids = [tc.class_id for tc in tc_records]
    if not class_ids:
        return []
    classes = db.query(Class).filter(Class.id.in_(class_ids)).all()
    result = []
    for c in classes:
        grade = db.query(Grade).filter(Grade.id == c.grade_id).first()
        student_count = db.query(func.count(User.id)).filter(User.class_id == c.id, User.role == "student").scalar()
        result.append({"id": c.id, "name": c.name, "grade_name": grade.name if grade else "", "student_count": student_count, "status": c.status})
    return result
