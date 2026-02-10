"""Projects CRUD and list. FIFO eviction when over limits."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Project
from backend.app.config import settings

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str


class ProjectOut(BaseModel):
    id: UUID
    name: str
    created_at: str
    updated_at: str
    storage_bytes: int
    targets: list
    eviction_order: int

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: list[ProjectOut]
    total_storage_bytes: int
    max_projects: int
    max_artifact_bytes: int
    eviction_warning: bool


@router.get("", response_model=ProjectListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)) -> ProjectListResponse:
    import json
    result = await db.execute(select(Project).order_by(Project.eviction_order.desc(), Project.updated_at.desc()).limit(settings.max_projects + 1))
    rows = result.scalars().all()
    projects = rows[: settings.max_projects]
    total = sum(p.storage_bytes for p in projects)
    eviction_warning = len(rows) > settings.max_projects or total > settings.max_artifact_bytes
    return ProjectListResponse(
        projects=[
            ProjectOut(
                id=p.id,
                name=p.name,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
                storage_bytes=p.storage_bytes,
                targets=json.loads(p.targets or "[]"),
                eviction_order=p.eviction_order,
            )
            for p in projects
        ],
        total_storage_bytes=total,
        max_projects=settings.max_projects,
        max_artifact_bytes=settings.max_artifact_bytes,
        eviction_warning=eviction_warning,
    )


@router.post("", response_model=ProjectOut)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    import json
    # Eviction: ensure we have room (FIFO)
    count_result = await db.execute(select(func.count(Project.id)))
    count = count_result.scalar() or 0
    if count >= settings.max_projects:
        # Delete oldest by eviction_order
        oldest = await db.execute(select(Project).order_by(Project.eviction_order.asc()).limit(1))
        to_del = oldest.scalar_one_or_none()
        if to_del:
            await db.delete(to_del)
    max_order = await db.execute(select(func.coalesce(func.max(Project.eviction_order), 0)))
    next_order = (max_order.scalar() or 0) + 1
    p = Project(name=body.name, targets="[]", eviction_order=next_order)
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return ProjectOut(
        id=p.id,
        name=p.name,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
        storage_bytes=p.storage_bytes,
        targets=json.loads(p.targets or "[]"),
        eviction_order=p.eviction_order,
    )


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    import json
    r = await db.execute(select(Project).where(Project.id == project_id))
    p = r.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")
    return ProjectOut(
        id=p.id,
        name=p.name,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
        storage_bytes=p.storage_bytes,
        targets=json.loads(p.targets or "[]"),
        eviction_order=p.eviction_order,
    )


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: UUID, body: dict, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    import json
    r = await db.execute(select(Project).where(Project.id == project_id))
    p = r.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")
    if "name" in body:
        p.name = body["name"]
    if "targets" in body:
        p.targets = json.dumps(body["targets"])
    await db.flush()
    await db.refresh(p)
    return ProjectOut(
        id=p.id,
        name=p.name,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
        storage_bytes=p.storage_bytes,
        targets=json.loads(p.targets or "[]"),
        eviction_order=p.eviction_order,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    r = await db.execute(select(Project).where(Project.id == project_id))
    p = r.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")
    await db.delete(p)
    return None
