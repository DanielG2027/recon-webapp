"""Scope preview: CIDR notation, host count, large-scope warning."""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.scope import parse_targets_for_scope

router = APIRouter()


class TargetInput(BaseModel):
    type: str  # ip, fqdn, cidr, url
    value: str


class ScopePreviewResponse(BaseModel):
    cidrs: list[dict]
    total_hosts: int
    has_external: bool
    large_scope_warning: bool


class ScopePreviewRequest(BaseModel):
    targets: list[TargetInput]


@router.post("/preview", response_model=ScopePreviewResponse)
async def scope_preview(body: ScopePreviewRequest) -> ScopePreviewResponse:
    tlist = [{"type": t.type, "value": t.value} for t in body.targets]
    out = parse_targets_for_scope(tlist)
    return ScopePreviewResponse(
        cidrs=out["cidrs"],
        total_hosts=out["total_hosts"],
        has_external=out["has_external"],
        large_scope_warning=out["large_scope_warning"],
    )
