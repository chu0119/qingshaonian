"""初次部署初始化 — 创建默认学校和管理员"""
import sys
sys.path.insert(0, '/www/wwwroot/qingshaonian/backend')

from app.database import SessionLocal, init_db, create_builtin_dictionaries
from app.utils.password import hash_password
from app.models.user import School, User, Grade, Class

def setup():
    init_db()
    db = SessionLocal()

    # 1. 系统字典
    create_builtin_dictionaries(db)

    # 2. 创建学校
    school = db.query(School).filter(School.code == 'DEFAULT').first()
    if not school:
        school = School(name='默认学校', code='DEFAULT', address='', phone='')
        db.add(school)
        db.flush()

        # 创建默认年级
        for gname, gsort in [('初一', 1), ('初二', 2), ('初三', 3)]:
            grade = Grade(school_id=school.id, name=gname, sort_order=gsort)
            db.add(grade)
            db.flush()
            for cname in [f'{gname}(1)班', f'{gname}(2)班']:
                db.add(Class(school_id=school.id, grade_id=grade.id, name=cname))

    # 3. 创建学校管理员
    admin = db.query(User).filter(User.username == 'admin').first()
    if not admin:
        db.add(User(
            school_id=school.id,
            username='admin',
            password_hash=hash_password('Admin@2026'),
            real_name='系统管理员',
            role='school_admin',
            must_change_password=True,
            status=True,
        ))

    db.commit()
    db.close()
    print('初始化完成：学校、年级、班级、管理员账号已创建')
    print('学校管理员: admin / Admin@2026')
    print('平台管理员: padm / Padm@2026')

if __name__ == '__main__':
    setup()
