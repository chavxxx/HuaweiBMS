"""Application Settings and Alert Thresholds Routes."""

from fastapi import APIRouter
from ..schemas.schemas import AppSettingsUpdate
from ..state import app_context

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("")
def get_settings():
    """Retrieve user configured warning thresholds and application settings."""
    return {"settings": app_context.settings}


@router.post("")
def update_settings(update: AppSettingsUpdate):
    """Update operator alert thresholds (clearly distinguished from BMS hardware protections)."""
    d = update.model_dump(exclude_unset=True)
    app_context.settings.update(d)
    return {"success": True, "settings": app_context.settings, "message": "Settings updated."}
