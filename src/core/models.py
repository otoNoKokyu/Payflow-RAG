import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class DocumentRegistry(Base):
    __tablename__ = "document_registry"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), index=True, nullable=False)
    domain = Column(String(50), index=True, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # 'active' or 'archived'
    creation_date = Column(String(50), nullable=True)
    is_legacy = Column(Boolean, default=False)
    department = Column(String(100), nullable=True)
    project_codename = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
