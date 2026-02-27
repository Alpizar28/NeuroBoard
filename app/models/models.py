from sqlalchemy import Column, Integer, String, DateTime
from app.db.database import Base
from datetime import datetime, timezone

class ImageProcessed(Base):
    __tablename__ = "images_processed"
    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TaskCreated(Base):
    __tablename__ = "tasks_created"
    id = Column(Integer, primary_key=True, index=True)
    google_task_id = Column(String, index=True)
    parent_id = Column(String, nullable=True) # Used if it's a subtask
    list_name = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tasks_detected = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    status = Column(String)
    error_message = Column(String, nullable=True)

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True, index=True)
    encrypted_refresh_token = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
