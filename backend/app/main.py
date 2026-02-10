# Recon Web App - FastAPI entrypoint. Serves API + static SPA.
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.routes import projects, jobs, results, reports, settings as settings_routes, auth_gate, audit, scope, dashboard, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure artifact/report dirs exist
    settings.artifact_root.mkdir(parents=True, exist_ok=True)
    settings.report_root.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: nothing for now
    pass


app = FastAPI(
    title="BLACKWALL",
    description="Local reconnaissance suite — beyond the wall, data doesn't sleep.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Local only - allow same origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (under /api)
app.include_router(auth_gate.router, prefix="/api", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["settings"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(scope.router, prefix="/api/scope", tags=["scope"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}

# SPA static files (must be last)
spa_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if spa_dist.exists():
    app.mount("/", StaticFiles(directory=str(spa_dist), html=True), name="spa")
else:
    # Dev: no build yet - return a minimal placeholder
    @app.get("/")
    async def root():
        return {"message": "Recon Web App", "hint": "Build frontend: cd frontend && npm run build"}
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}
