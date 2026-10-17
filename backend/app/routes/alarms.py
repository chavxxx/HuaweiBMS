"""Alarms and Faults Routes."""

from fastapi import APIRouter
from ..database.crud import AlarmCRUD
from ..state import app_context

router = APIRouter(prefix="/api/alarms", tags=["Alarms"])


@router.get("/active")
def get_active_alarms():
    """Retrieve all currently active alarms with manufacturer guidance."""
    raw_codes = app_context.telemetry_service.latest_telemetry.get("active_alarm_codes", [])
    active_enriched = app_context.alarm_service.process_active_alarms(raw_codes)
    return {"active_alarms": active_enriched}


@router.get("/history")
def get_alarm_history():
    """Retrieve historical alarm events."""
    return {"history": AlarmCRUD.get_alarms(active_only=False)}


@router.post("/simulate-inject")
def inject_alarm_simulation(alarm_code: int):
    """Test injecting an alarm code into the virtual simulator."""
    app_context.simulator.inject_alarm(alarm_code)
    return {"success": True, "message": f"Injected simulated alarm code {alarm_code}."}


@router.post("/simulate-clear")
def clear_alarm_simulation(alarm_code: int):
    """Clear an injected alarm code from the simulator."""
    app_context.simulator.clear_alarm(alarm_code)
    return {"success": True, "message": f"Cleared simulated alarm code {alarm_code}."}
