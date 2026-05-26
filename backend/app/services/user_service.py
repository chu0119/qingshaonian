from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.user import User, Grade, Class, TeacherClass
from ..schemas.user import UserCreate, UserUpdate, UserInfo, ImportResult
from ..utils.password import hash_password
import openpyxl
from io import BytesIO


def list_users(db: Session, school_id: int, role: str, page: int = 1, page_size: int = 20,
               grade_id: int | None = None, class_id: int | None = None, keyword: str = "",
               teacher_type: str = "", class_ids: list[int] | None = None):
    q = db.query(User).filter(User.school_id == school_id, User.role == role)
    if grade_id:
        q = q.filter(User.grade_id == grade_id)
    if class_id:
        q = q.filter(User.class_id == class_id)
    if class_ids is not None:
        q = q.filter(User.class_id.in_(class_ids))
    if keyword:
        q = q.filter(User.real_name.contains(keyword) | User.username.contains(keyword) | User.student_no.contains(keyword))
    if teacher_type and role in ("teacher", "counselor"):
        q = q.filter(User.teacher_type == teacher_type)

    total = q.count()
    items = q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for u in items:
        grade_name = db.query(Grade).filter(Grade.id == u.grade_id).first()
        class_name = db.query(Class).filter(Class.id == u.class_id).first()
        result.append(
            UserInfo(
                id=u.id, school_id=u.school_id, username=u.username, real_name=u.real_name,
                role=u.role, teacher_type=u.teacher_type, gender=u.gender or "", phone=u.phone or "",
                student_no=u.student_no or "", birth_date=u.birth_date, grade_id=u.grade_id,
                class_id=u.class_id, status=u.status,
                grade_name=grade_name.name if grade_name else "",
                class_name=class_name.name if class_name else "",
                created_at=u.created_at,
            )
        )

    return {"items": result, "total": total, "page": page, "page_size": page_size, "total_pages": max((total + page_size - 1) // page_size, 1)}


def create_user(db: Session, data: UserCreate) -> User:
    u = User(
        school_id=data.school_id, username=data.username,
        password_hash=hash_password(data.password or "123456"),
        real_name=data.real_name, role=data.role or "student", teacher_type=data.teacher_type,
        gender=data.gender, phone=data.phone, student_no=data.student_no,
        birth_date=data.birth_date, grade_id=data.grade_id, class_id=data.class_id, status=data.status,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise ValueError("用户不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    return u


def delete_user(db: Session, user_id: int):
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        db.delete(u)
        db.commit()


def get_user_info(db: Session, user_id: int) -> UserInfo:
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise ValueError("用户不存在")
    grade_name = db.query(Grade).filter(Grade.id == u.grade_id).first()
    class_name = db.query(Class).filter(Class.id == u.class_id).first()
    return UserInfo(
        id=u.id, school_id=u.school_id, username=u.username, real_name=u.real_name,
        role=u.role, teacher_type=u.teacher_type, gender=u.gender or "", phone=u.phone or "",
        student_no=u.student_no or "", birth_date=u.birth_date, grade_id=u.grade_id,
        class_id=u.class_id, status=u.status,
        grade_name=grade_name.name if grade_name else "",
        class_name=class_name.name if class_name else "",
        created_at=u.created_at,
    )


def import_students_from_excel(db: Session, school_id: int, file_bytes: bytes) -> ImportResult:
    result = ImportResult()
    wb = openpyxl.load_workbook(BytesIO(file_bytes))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    grades_map = {g.name: g.id for g in db.query(Grade).filter(Grade.school_id == school_id).all()}
    classes_map = {c.name: c.id for c in db.query(Class).filter(Class.school_id == school_id).all()}

    for i, row in enumerate(rows):
        try:
            student_no = str(row[0]).strip() if row[0] else ""
            name = str(row[1]).strip() if row[1] else ""
            gender = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            grade_name = str(row[3]).strip() if len(row) > 3 and row[3] else ""
            class_name = str(row[4]).strip() if len(row) > 4 and row[4] else ""
            birth_date_str = str(row[5]).strip() if len(row) > 5 and row[5] else None
            phone = str(row[6]).strip() if len(row) > 6 and row[6] else ""

            if not student_no or not name:
                result.fail_count += 1
                result.errors.append(f"第{i + 2}行: 学号或姓名为空")
                continue

            grade_id = grades_map.get(grade_name)
            class_id = classes_map.get(class_name)

            existing = db.query(User).filter(User.username == student_no, User.school_id == school_id).first()
            if existing:
                result.fail_count += 1
                result.errors.append(f"第{i + 2}行: 学号 {student_no} 已存在")
                continue

            from datetime import datetime
            birth_date = None
            if birth_date_str:
                try:
                    if isinstance(birth_date_str, datetime):
                        birth_date = birth_date_str.date()
                    else:
                        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            u = User(
                school_id=school_id, username=student_no, password_hash=hash_password("123456"),
                real_name=name, role="student", gender=gender, student_no=student_no,
                phone=phone, birth_date=birth_date, grade_id=grade_id, class_id=class_id,
                status=True,
            )
            db.add(u)
            result.success_count += 1
        except Exception as e:
            result.fail_count += 1
            result.errors.append(f"第{i + 2}行: {str(e)}")

    db.commit()
    return result


def generate_student_template():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "学生导入模板"
    ws.append(["学号", "姓名", "性别", "年级", "班级", "出生日期", "手机号"])
    ws.append(["2024001", "张三", "男", "初一", "初一(1)班", "2010-01-15", "13800000000"])
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def assign_teacher_classes(db: Session, teacher_id: int, class_ids: list[int]):
    db.query(TeacherClass).filter(TeacherClass.teacher_id == teacher_id).delete()
    for cid in class_ids:
        db.add(TeacherClass(teacher_id=teacher_id, class_id=cid))
    db.commit()
