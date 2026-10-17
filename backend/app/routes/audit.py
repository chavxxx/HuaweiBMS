"""Audit Logging Routes."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from ..database.crud import AuditCRUD
from ..services.report_service import ReportService

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/logs")
def get_audit_logs(limit: int = 200):
    """Retrieve permanent audit trail records."""
    logs = AuditCRUD.get_audit_trail(limit=limit)
    return {"logs": logs}


@router.get("/export-csv")
def export_audit_csv(limit: int = 1000):
    """Export complete audit log to CSV."""
    csv_str = ReportService.export_audit_log_csv(limit=limit)
    return PlainTextResponse(csv_str, media_type="text/csv")
