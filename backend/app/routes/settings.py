"""App settings: concurrency, container limits, retention, default aggressiveness."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import AppSettings
from backend.app.config import settings as app_settings

router = APIRouter()


class SettingsOut(BaseModel):
    concurrency: int
    max_concurrency: int
    container_cpu: str
    container_memory_gb: int
    default_aggressiveness: int
    raw_retention_days: int
    log_retention_days: int


@router.get("", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsOut:
    r = await db.execute(select(AppSettings))
    rows = {row.key: row.value for row in r.scalars().all()}
    def int_val(k: str, default: int) -> int:
        try:
            return int(rows.get(k, default))
        except (ValueError, TypeError):
            return default
    def str_val(k: str, default: str) -> str:
        return str(rows.get(k, default))
    return SettingsOut(
        concurrency=int_val("concurrency", app_settings.default_concurrency),
        max_concurrency=int_val("max_concurrency", app_settings.max_concurrency),
        container_cpu=str_val("container_cpu", app_settings.default_container_cpu),
        container_memory_gb=int_val("container_memory_gb", app_settings.default_container_memory_gb),
        default_aggressiveness=int_val("default_aggressiveness", 5),
        raw_retention_days=int_val("raw_retention_days", app_settings.raw_retention_days),
        log_retention_days=int_val("log_retention_days", app_settings.log_retention_days),
    )


@router.patch("", response_model=SettingsOut)
async def update_settings(body: dict, db: AsyncSession = Depends(get_db)) -> SettingsOut:
    for key in ("concurrency", "max_concurrency", "container_cpu", "container_memory_gb", "default_aggressiveness", "raw_retention_days", "log_retention_days"):
        if key in body:
            r = await db.execute(select(AppSettings).where(AppSettings.key == key))
            row = r.scalar_one_or_none()
            val = str(body[key])
            if row:
                row.value = val
            else:
                db.add(AppSettings(key=key, value=val))
    await db.flush()
    return await get_settings(db)
