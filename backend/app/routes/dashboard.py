"""Dashboard: top pathway to initial access, recent jobs, high-risk summary."""
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Job, Finding, Project

router = APIRouter()


class TopPathwayOut(BaseModel):
    hypothesis: str
    score: float
    evidence: list[str]
    finding_ids: list[str]


class DashboardOut(BaseModel):
    top_pathway: TopPathwayOut | None
    recent_jobs: list[dict]
    high_risk_count: int
    total_findings: int


@router.get("", response_model=DashboardOut)
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardOut:
    # Stub top pathway (correlation engine will compute)
    top_pathway = None
    r = await db.execute(select(Finding).where(Finding.risk_score >= 7).order_by(Finding.risk_score.desc()).limit(5))
    high = r.scalars().all()
    if high:
        f = high[0]
        top_pathway = TopPathwayOut(
            hypothesis=f.title,
            score=float(f.risk_score or 0) / 10.0,
            evidence=[f.title],
            finding_ids=[str(f.id)],
        )

    jobs = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(10))
    recent = jobs.scalars().all()
    high_risk = await db.execute(select(Finding).where(Finding.risk_score >= 7))
    high_risk_count = len(high_risk.scalars().all())
    total_f = await db.execute(select(Finding))
    total_findings = len(total_f.scalars().all())

    return DashboardOut(
        top_pathway=top_pathway,
        recent_jobs=[
            {
                "id": str(j.id),
                "project_id": str(j.project_id),
                "module": j.module,
                "status": j.status,
                "created_at": j.created_at.isoformat(),
            }
            for j in recent
        ],
        high_risk_count=high_risk_count,
        total_findings=total_findings,
    )
