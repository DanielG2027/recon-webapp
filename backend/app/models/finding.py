from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.project import Project


class Finding(Base):
    """Immutable finding. Notes/tags are append-only annotations."""
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    # Normalized type: host, port, service, web_route, cloud_asset, etc.
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Human-readable summary
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    # Structured data JSON (ip, port, protocol, banner, cve_id, etc.)
    data: Mapped[str] = mapped_column(Text, default="{}")
    # Risk heuristics: 0-10 or null
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # For correlation: link to other finding ids
    related_finding_ids: Mapped[str] = mapped_column(Text, default="[]")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    raw_output_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)  # path or null after expiry
    # Internal vs external (auto-tagged)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=True)

    project: Mapped["Project"] = relationship("Project", back_populates="findings")
    notes: Mapped[list["FindingNote"]] = relationship("FindingNote", back_populates="finding", cascade="all, delete-orphan")


class FindingNote(Base):
    """Append-only annotation on a finding."""
    __tablename__ = "finding_notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="note")  # note, tag
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    finding: Mapped["Finding"] = relationship("Finding", back_populates="notes")
