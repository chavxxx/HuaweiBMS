"""Software Updates and Git Synchronization Routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..state import app_context

router = APIRouter(prefix="/api/updates", tags=["Updates"])


class PullUpdateRequest(BaseModel):
    user_role: str = "ADMINISTRATOR"


@router.get("/check")
def check_for_updates():
    """Check remote GitHub repository for newer releases or commits."""
    try:
        res = app_context.update_service.check_for_updates()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull")
def pull_latest_update(req: PullUpdateRequest):
    """Pull the latest git commits from origin/main (Administrator role required)."""
    if req.user_role.upper() != "ADMINISTRATOR":
        raise HTTPException(status_code=403, detail="Only Administrator role can pull application updates.")
    try:
        res = app_context.update_service.pull_latest_update(user_role=req.user_role)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
