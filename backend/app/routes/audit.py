"""Audit log viewer with filters."""
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import AuditLog

router = APIRouter()


class AuditEntryOut(BaseModel):
    id: UUID
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[AuditEntryOut])
async def list_audit_logs(
    project_id: UUID | None = None,
    resource_type: str | None = None,
    since: datetime | None = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[AuditEntryOut]:
    import json
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if since:
        q = q.where(AuditLog.created_at >= since)
    if project_id:
        q = q.where(AuditLog.resource_id == str(project_id))
    r = await db.execute(q)
    rows = r.scalars().all()
    return [
        AuditEntryOut(
            id=row.id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            details=json.loads(row.details or "{}"),
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
