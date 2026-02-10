"""Results: correlated findings, filters, raw output viewer."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Finding, FindingNote, Project

router = APIRouter()


class FindingOut(BaseModel):
    id: UUID
    project_id: UUID
    job_id: UUID | None
    module: str
    finding_type: str
    title: str
    data: dict
    risk_score: int | None
    first_seen_at: str
    last_seen_at: str
    raw_output_ref: str | None
    is_internal: bool
    notes: list[dict] = []

    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/findings", response_model=list[FindingOut])
async def list_findings(
    project_id: UUID,
    module: str | None = None,
    finding_type: str | None = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[FindingOut]:
    q = select(Finding).where(Finding.project_id == project_id).order_by(Finding.last_seen_at.desc()).limit(limit)
    if module:
        q = q.where(Finding.module == module)
    if finding_type:
        q = q.where(Finding.finding_type == finding_type)
    r = await db.execute(q)
    findings = r.scalars().all()
    out = []
    for f in findings:
        notes_r = await db.execute(select(FindingNote).where(FindingNote.finding_id == f.id))
        notes = notes_r.scalars().all()
        out.append(
            FindingOut(
                id=f.id,
                project_id=f.project_id,
                job_id=f.job_id,
                module=f.module,
                finding_type=f.finding_type,
                title=f.title,
                data=__import__("json").loads(f.data or "{}"),
                risk_score=f.risk_score,
                first_seen_at=f.first_seen_at.isoformat(),
                last_seen_at=f.last_seen_at.isoformat(),
                raw_output_ref=f.raw_output_ref,
                is_internal=f.is_internal,
                notes=[{"kind": n.kind, "content": n.content, "created_at": n.created_at.isoformat()} for n in notes],
            )
        )
    return out


@router.post("/findings/{finding_id}/notes")
async def add_finding_note(
    finding_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    r = await db.execute(select(Finding).where(Finding.id == finding_id))
    f = r.scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Finding not found")
    note = FindingNote(finding_id=finding_id, kind=body.get("kind", "note"), content=body.get("content", ""))
    db.add(note)
    await db.flush()
    return {"id": str(note.id), "kind": note.kind, "content": note.content}
