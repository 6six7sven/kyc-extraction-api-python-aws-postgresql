from sqlalchemy import Column, String, DateTime, JSON, Integer
from datetime import datetime, timezone
from .database import Base

class KYCTask(Base):
    __tablename__ = "kyc_tasks"

    # We use the Celery task ID as our primary key
    task_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="PENDING")
    extracted_fields = Column(JSON, nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)