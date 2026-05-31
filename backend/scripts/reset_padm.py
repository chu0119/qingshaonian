"""Reset platform admin password"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.utils.password import hash_password

db_url = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
db = Session()
h = hash_password("Admin@2026!")
db.execute(text("UPDATE users SET password_hash=:h, must_change_password=1 WHERE username='padm'"), {"h": h})
db.commit()
print("Password reset done for padm")
db.close()
