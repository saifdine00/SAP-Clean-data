import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    READY = "ready"
    EXPORTED = "exported"


class CorrectionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MANUAL = "manual"


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    original_format: Mapped[str] = mapped_column(String(20))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), default=SessionStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    column_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    clean_data: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

    anomalies: Mapped[list["Anomaly"]] = relationship("Anomaly", back_populates="session", cascade="all, delete-orphan")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id", ondelete="CASCADE"))
    row_index: Mapped[int] = mapped_column(Integer)
    column_name: Mapped[str] = mapped_column(String(255))
    anomaly_type: Mapped[str] = mapped_column(String(100))
    original_value: Mapped[str] = mapped_column(Text, nullable=True)
    suggested_value: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(default=0.0)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[CorrectionStatus] = mapped_column(SAEnum(CorrectionStatus), default=CorrectionStatus.PENDING)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["UploadSession"] = relationship("UploadSession", back_populates="anomalies")
