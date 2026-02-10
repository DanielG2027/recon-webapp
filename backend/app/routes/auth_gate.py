"""Authorization gate: confirm user has authorization before any active recon."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AuthorizationState(BaseModel):
    confirmed: bool
    blocked_reason: str | None = None


# In-memory for single-user local app. No persistence needed.
_authorization_confirmed = False


@router.get("/authorization", response_model=AuthorizationState)
async def get_authorization_state() -> AuthorizationState:
    return AuthorizationState(
        confirmed=_authorization_confirmed,
        blocked_reason=None if _authorization_confirmed else "Blocked: Authorization not confirmed.",
    )


class AuthorizationConfirm(BaseModel):
    confirmed: bool


@router.post("/authorization")
async def set_authorization_confirmed(body: AuthorizationConfirm) -> dict:
    global _authorization_confirmed
    _authorization_confirmed = body.confirmed
    return {"confirmed": _authorization_confirmed}


class AdminApprovalPayload(BaseModel):
    job_id: str
    token: str


@router.post("/admin-approval")
async def submit_admin_approval(payload: AdminApprovalPayload) -> dict:
    # Backend will verify via reconctl or local file; for now accept and record.
    return {"status": "pending", "message": "Run: sudo reconctl approve " + payload.job_id + " " + payload.token}
