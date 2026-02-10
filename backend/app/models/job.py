from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.project import Project


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELED = "canceled"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class JobModule(str, enum.Enum):
    OSINT = "osint"
    ACTIVE_SCAN = "active_scan"
    WEB = "web"
    CLOUD = "cloud"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    module: Mapped[str] = mapped_column(String(32), nullable=False)  # JobModule value
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.PENDING.value)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # higher = run first
    progress_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aggressiveness: Mapped[int] = mapped_column(Integer, default=5)  # 1-10
    noise_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    # Parameters JSON (targets, ports, wordlist path, etc.)
    parameters: Mapped[str] = mapped_column(Text, default="{}")
    # Internal: external target = requires admin approval
    is_external: Mapped[bool] = mapped_column(default=False)
    admin_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorization_confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Raw output path (relative to artifact root); expires in 7 days
    raw_output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    container_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="jobs")

    def __repr__(self) -> str:
        return f"Job(id={self.id}, module={self.module}, status={self.status})"


class JobEventType(str, enum.Enum):
    CREATED = "created"
    STARTED = "started"
    PAUSED = "paused"
    CANCELED = "canceled"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload: Mapped[str] = mapped_column(Text, default="{}")  # optional JSON
