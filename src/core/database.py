import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# We will reuse CELERY_BACKEND_URL for the Document Registry since it's a MySQL database
DATABASE_URL = os.getenv("CELERY_BACKEND_URL", "db+mysql+pymysql://root:hello%40123@localhost:3306/orbitflow")
# Clean up the URL if it starts with db+ (celery format)
if DATABASE_URL.startswith("db+"):
    DATABASE_URL = DATABASE_URL[3:]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
