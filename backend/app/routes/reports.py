"""Reports: one-click MD + PDF generation, history per project."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Report, Project

router = APIRouter()


class ReportOut(BaseModel):
    id: UUID
    project_id: UUID
    format: str
    file_path: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/reports", response_model=list[ReportOut])
async def list_reports(project_id: UUID, db: AsyncSession = Depends(get_db)) -> list[ReportOut]:
    r = await db.execute(select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc()))
    reports = r.scalars().all()
    return [
        ReportOut(
            id=rep.id,
            project_id=rep.project_id,
            format=rep.format,
            file_path=rep.file_path,
            created_at=rep.created_at.isoformat(),
        )
        for rep in reports
    ]


@router.post("/projects/{project_id}/generate")
async def generate_report(
    project_id: UUID,
    formats: list[str] = ["md", "pdf"],
    db: AsyncSession = Depends(get_db),
) -> dict:
    r = await db.execute(select(Project).where(Project.id == project_id))
    proj = r.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "Project not found")
    # Stub: actual generation will use WeasyPrint + template
    return {"status": "queued", "message": "Report generation not yet implemented; use stub."}


@router.get("/{report_id}/download")
async def download_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Report).where(Report.id == report_id))
    rep = r.scalar_one_or_none()
    if not rep:
        raise HTTPException(404, "Report not found")
    # Serve file from report_root
    from backend.app.config import settings
    path = settings.report_root / rep.file_path
    if not path.exists():
        raise HTTPException(404, "Report file not found")
    return FileResponse(path, filename=path.name)
