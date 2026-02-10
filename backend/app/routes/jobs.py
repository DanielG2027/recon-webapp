"""Jobs: create, list, priority, pause/cancel/rerun, progress, log tail."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Job, JobEvent, Project

router = APIRouter()


class JobCreate(BaseModel):
    project_id: UUID
    module: str
    aggressiveness: int = 5
    parameters: dict = {}
    authorization_confirmed: bool = False


class JobOut(BaseModel):
    id: UUID
    project_id: UUID
    module: str
    status: str
    priority: int
    progress_pct: int | None
    eta_seconds: int | None
    aggressiveness: int
    noise_score: int | None
    is_external: bool
    admin_approved_at: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    exit_code: int | None
    error_message: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[JobOut])
async def list_jobs(
    project_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[JobOut]:
    q = select(Job).order_by(Job.priority.desc(), Job.created_at.desc()).limit(limit)
    if project_id:
        q = q.where(Job.project_id == project_id)
    if status:
        q = q.where(Job.status == status)
    r = await db.execute(q)
    jobs = r.scalars().all()
    return [
        JobOut(
            id=j.id,
            project_id=j.project_id,
            module=j.module,
            status=j.status,
            priority=j.priority,
            progress_pct=j.progress_pct,
            eta_seconds=j.eta_seconds,
            aggressiveness=j.aggressiveness,
            noise_score=j.noise_score,
            is_external=j.is_external,
            admin_approved_at=j.admin_approved_at.isoformat() if j.admin_approved_at else None,
            created_at=j.created_at.isoformat(),
            started_at=j.started_at.isoformat() if j.started_at else None,
            finished_at=j.finished_at.isoformat() if j.finished_at else None,
            exit_code=j.exit_code,
            error_message=j.error_message,
        )
        for j in jobs
    ]


@router.post("", response_model=JobOut)
async def create_job(body: JobCreate, db: AsyncSession = Depends(get_db)) -> JobOut:
    if not body.authorization_confirmed:
        raise HTTPException(403, "Blocked: Authorization not confirmed.")
    r = await db.execute(select(Project).where(Project.id == body.project_id))
    proj = r.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "Project not found")
    job = Job(
        project_id=body.project_id,
        module=body.module,
        aggressiveness=body.aggressiveness,
        parameters=__import__("json").dumps(body.parameters),
        authorization_confirmed=body.authorization_confirmed,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return JobOut(
        id=job.id,
        project_id=job.project_id,
        module=job.module,
        status=job.status,
        priority=job.priority,
        progress_pct=job.progress_pct,
        eta_seconds=job.eta_seconds,
        aggressiveness=job.aggressiveness,
        noise_score=job.noise_score,
        is_external=job.is_external,
        admin_approved_at=job.admin_approved_at.isoformat() if job.admin_approved_at else None,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        exit_code=job.exit_code,
        error_message=job.error_message,
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)) -> JobOut:
    r = await db.execute(select(Job).where(Job.id == job_id))
    j = r.scalar_one_or_none()
    if not j:
        raise HTTPException(404, "Job not found")
    return JobOut(
        id=j.id,
        project_id=j.project_id,
        module=j.module,
        status=j.status,
        priority=j.priority,
        progress_pct=j.progress_pct,
        eta_seconds=j.eta_seconds,
        aggressiveness=j.aggressiveness,
        noise_score=j.noise_score,
        is_external=j.is_external,
        admin_approved_at=j.admin_approved_at.isoformat() if j.admin_approved_at else None,
        created_at=j.created_at.isoformat(),
        started_at=j.started_at.isoformat() if j.started_at else None,
        finished_at=j.finished_at.isoformat() if j.finished_at else None,
        exit_code=j.exit_code,
        error_message=j.error_message,
    )


@router.post("/{job_id}/cancel", status_code=200)
async def cancel_job(job_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    r = await db.execute(select(Job).where(Job.id == job_id))
    j = r.scalar_one_or_none()
    if not j:
        raise HTTPException(404, "Job not found")
    j.status = "canceled"
    await db.flush()
    return {"status": "canceled"}


@router.post("/{job_id}/rerun", response_model=JobOut)
async def rerun_job(job_id: UUID, db: AsyncSession = Depends(get_db)) -> JobOut:
    r = await db.execute(select(Job).where(Job.id == job_id))
    orig = r.scalar_one_or_none()
    if not orig:
        raise HTTPException(404, "Job not found")
    new_job = Job(
        project_id=orig.project_id,
        module=orig.module,
        aggressiveness=orig.aggressiveness,
        parameters=orig.parameters,
        authorization_confirmed=orig.authorization_confirmed,
        priority=orig.priority,
    )
    db.add(new_job)
    await db.flush()
    await db.refresh(new_job)
    return JobOut(
        id=new_job.id,
        project_id=new_job.project_id,
        module=new_job.module,
        status=new_job.status,
        priority=new_job.priority,
        progress_pct=new_job.progress_pct,
        eta_seconds=new_job.eta_seconds,
        aggressiveness=new_job.aggressiveness,
        noise_score=new_job.noise_score,
        is_external=new_job.is_external,
        admin_approved_at=new_job.admin_approved_at.isoformat() if new_job.admin_approved_at else None,
        created_at=new_job.created_at.isoformat(),
        started_at=new_job.started_at.isoformat() if new_job.started_at else None,
        finished_at=new_job.finished_at.isoformat() if new_job.finished_at else None,
        exit_code=new_job.exit_code,
        error_message=new_job.error_message,
    )


@router.get("/{job_id}/logs")
async def get_job_logs(job_id: UUID, tail: int = Query(500, le=5000)) -> dict:
    # Stub: return path or last N lines from artifact store
    return {"logs": [], "tail": tail}
