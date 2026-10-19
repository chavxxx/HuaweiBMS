"""Multi-Battery Fleet Management and Comparison Routes."""

import time
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional

from ..database.crud import MultiBatteryAuditCRUD
from ..state import app_context

router = APIRouter(prefix="/api/batteries", tags=["Multi-Battery"])


class SelectBatteryRequest(BaseModel):
    slave_id: int


class AddBatteryRequest(BaseModel):
    slave_id: int
    name: Optional[str] = None


class ScanBusRequest(BaseModel):
    candidate_ids: Optional[list[int]] = None


class SaveAuditRequest(BaseModel):
    operator: str = "ADMINISTRATOR"
    notes: Optional[str] = ""


@router.get("")
def list_batteries():
    """Retrieve list of all configured batteries, quick statuses, and active slave ID."""
    try:
        service = app_context.multi_battery_service
        batteries = service.list_batteries()
        return {
            "batteries": batteries,
            "active_slave_id": service.active_slave_id,
            "is_simulation": app_context.telemetry_service.use_simulation,
            "total_count": len(batteries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select")
def select_active_battery(req: SelectBatteryRequest):
    """Switch active battery monitored across Dashboard, Electrical, Cells, Alarms, and Config views."""
    try:
        service = app_context.multi_battery_service
        res = service.set_active_battery(req.slave_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan")
def scan_bus_for_batteries(req: ScanBusRequest):
    """Scan RS485 Modbus bus for responding battery slave IDs."""
    try:
        service = app_context.multi_battery_service
        res = service.scan_bus(req.candidate_ids)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/add")
def add_battery(req: AddBatteryRequest):
    """Add a battery address to the monitored fleet."""
    try:
        service = app_context.multi_battery_service
        res = service.add_battery(req.slave_id, req.name)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{slave_id}")
def remove_battery(slave_id: int):
    """Remove a battery address from the monitored fleet."""
    try:
        service = app_context.multi_battery_service
        res = service.remove_battery(slave_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/read-all")
def read_all_batteries():
    """Perform a comprehensive readout of all batteries on the bus and return comparative metrics."""
    try:
        service = app_context.multi_battery_service
        res = service.read_all_batteries()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-audit")
def save_audit(req: SaveAuditRequest):
    """Read all batteries and save an immutable audit snapshot into the database."""
    try:
        service = app_context.multi_battery_service
        res = service.save_audit_snapshot(operator=req.operator, notes=req.notes or "")
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audits")
def list_saved_audits(limit: int = 50):
    """Retrieve historical multi-battery audit snapshots."""
    try:
        audits = MultiBatteryAuditCRUD.list_audits(limit=limit)
        return {"audits": audits, "count": len(audits)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audits/{audit_id}")
def get_saved_audit(audit_id: int):
    """Retrieve full details of a specific saved multi-battery audit snapshot."""
    try:
        audit = MultiBatteryAuditCRUD.get_audit(audit_id)
        if not audit:
            raise HTTPException(status_code=404, detail=f"Audit #{audit_id} not found.")
        return audit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/audits/{audit_id}")
def delete_saved_audit(audit_id: int):
    """Delete a saved multi-battery audit."""
    try:
        success = MultiBatteryAuditCRUD.delete_audit(audit_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Audit #{audit_id} not found.")
        return {"success": True, "message": f"Audit #{audit_id} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
def export_csv():
    """Export the latest battery fleet comparison as a CSV file."""
    try:
        service = app_context.multi_battery_service
        csv_content = service.export_audit_csv()
        filename = f"huawei_bms_fleet_comparison_{int(time.time())}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/json")
def export_json():
    """Export the latest battery fleet comparison as formatted JSON."""
    try:
        service = app_context.multi_battery_service
        json_content = service.export_audit_json()
        filename = f"huawei_bms_fleet_audit_{int(time.time())}.json"
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
