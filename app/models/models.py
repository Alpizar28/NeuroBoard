from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime, timezone


class ImageProcessed(Base):
    """Stores hashes of processed media (images and audio) for deduplication."""
    __tablename__ = "images_processed"
    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String, unique=True, index=True)
    media_type = Column(String, default="image")  # "image" | "audio"
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
    """Persists the current Google OAuth access token between requests.
    The refresh_token is read from environment variables (settings).
    The access_token here is refreshed automatically when it expires."""
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, default="google", index=True)
    access_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    refresh_token = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PendingPreview(Base):
    __tablename__ = "pending_previews"
    id = Column(Integer, primary_key=True, index=True)
    # Stores hash of the processed media (image or audio) for deduplication tracking
    image_hash = Column(String, nullable=True, index=True)
    payload_json = Column(Text)
    source = Column(String, default="unknown")
    # Valid statuses: pending | editing | confirmed | completed | creation_failed | cancelled | expired
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    task_creations = relationship(
        "PreviewTaskCreation",
        back_populates="preview",
        cascade="all, delete-orphan",
    )


class PreviewTaskCreation(Base):
    __tablename__ = "preview_task_creations"
    id = Column(Integer, primary_key=True, index=True)
    preview_id = Column(Integer, ForeignKey("pending_previews.id"), index=True)
    task_key = Column(String, unique=True, index=True)
    google_task_id = Column(String, index=True)
    list_name = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    preview = relationship("PendingPreview", back_populates="task_creations")
