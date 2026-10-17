"""Configuration Parameters and Guarded Writes Routes."""

from dataclasses import asdict
from fastapi import APIRouter, HTTPException
from ..database.crud import SnapshotCRUD
from ..schemas.schemas import EnableWritesRequest, ParameterWriteRequest, SnapshotCreateRequest
from ..state import app_context

router = APIRouter(prefix="/api/config", tags=["Configuration"])


@router.get("/parameters")
def get_parameters():
    """Retrieve all readable parameters with raw, decoded, and allowlist statuses."""
    is_sim = app_context.telemetry_service.use_simulation
    params = app_context.config_service.read_all_parameters(is_simulation=is_sim)
    return {
        "writes_enabled": app_context.config_service.writes_enabled,
        "parameters": params
    }


@router.post("/enable-writes")
def enable_writes(req: EnableWritesRequest):
    """Enable parameter write modifications (Administrator role required)."""
    try:
        ok = app_context.config_service.enable_writes(req.user_role, req.confirmation_key)
        return {"success": ok, "writes_enabled": True, "message": "Configuration writes are now UNLOCKED."}
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/disable-writes")
def disable_writes():
    """Lock parameter writes back to safe Read-Only mode."""
    app_context.config_service.disable_writes()
    return {"success": True, "writes_enabled": False, "message": "System returned to Read-Only mode."}


@router.post("/write")
def write_parameter(req: ParameterWriteRequest):
    """Execute the mandatory 10-Step Guarded Write Workflow with read-back verification."""
    is_sim = app_context.telemetry_service.use_simulation
    try:
        res = app_context.config_service.execute_guarded_write(
            address=req.address,
            new_value=req.new_value,
            user_role=req.user_role,
            operator_confirmed=req.operator_confirmed,
            is_simulation=is_sim
        )
        return {
            "success": res.success,
            "parameter_address": res.parameter_address,
            "parameter_name": res.parameter_name,
            "previous_value": res.previous_value,
            "requested_value": res.requested_value,
            "verified_value": res.verified_value,
            "message": res.message,
            "steps": [asdict(s) for s in res.steps],
            "audit_id": res.audit_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/snapshots")
def list_snapshots():
    """List saved configuration snapshots."""
    return {"snapshots": SnapshotCRUD.list_snapshots()}


@router.post("/snapshots")
def create_snapshot(req: SnapshotCreateRequest):
    """Capture snapshot of current parameters."""
    is_sim = app_context.telemetry_service.use_simulation
    params = app_context.config_service.read_all_parameters(is_simulation=is_sim)
    param_dict = {p["address"]: p["current_raw"] for p in params}
    s_id = SnapshotCRUD.save_snapshot(
        name=req.snapshot_name,
        device_id="Huawei EMS B1",
        role=req.author_role,
        notes=req.notes or "",
        params=param_dict
    )
    return {"success": True, "snapshot_id": s_id, "message": f"Snapshot '{req.snapshot_name}' saved."}


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: int):
    """Retrieve full details of a specific snapshot."""
    s = SnapshotCRUD.get_snapshot(snapshot_id)
    if not s:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return s


@router.post("/snapshots/compare")
def compare_snapshot_with_current(snapshot_id: int):
    """Compare a saved snapshot against current live parameter values."""
    s = SnapshotCRUD.get_snapshot(snapshot_id)
    if not s:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    is_sim = app_context.telemetry_service.use_simulation
    current_params = app_context.config_service.read_all_parameters(is_simulation=is_sim)
    snap_params = s["parameters"]

    diffs = []
    for curr in current_params:
        addr = str(curr["address"])
        snap_val = snap_params.get(addr) or snap_params.get(int(addr))
        curr_val = curr["current_raw"]
        is_diff = snap_val != curr_val
        diffs.append({
            "address": curr["address"],
            "name": curr["name"],
            "unit": curr["unit"],
            "snapshot_value": snap_val,
            "current_value": curr_val,
            "has_changed": is_diff
        })

    return {
        "snapshot_id": snapshot_id,
        "snapshot_name": s["snapshot_name"],
        "timestamp": s["timestamp"],
        "comparisons": diffs
    }
