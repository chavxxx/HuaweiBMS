"""Historical Trends, Reporting, and Database Backup Routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from ..database.crud import TelemetryCRUD
from ..services.report_service import ReportService

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("/query")
def query_history(start_time: float = None, end_time: float = None, limit: int = 500):
    """Query telemetry history points for trend charts."""
    pts = TelemetryCRUD.query_history(start_time=start_time, end_time=end_time, limit=limit)
    return {"points": pts, "count": len(pts)}


@router.get("/report")
def generate_report(days: int = 7):
    """Generate high-level operational statistics report."""
    return ReportService.generate_summary_report(days=days)


@router.get("/export-csv")
def export_csv(limit: int = 2000):
    """Export historical telemetry data to CSV format."""
    csv_str = ReportService.export_telemetry_csv(limit=limit)
    return PlainTextResponse(csv_str, media_type="text/csv")


@router.post("/backup")
def trigger_backup():
    """Trigger immediate SQLite database backup."""
    try:
        path = ReportService.backup_database()
        return {"success": True, "backup_path": path, "message": "Database backup created successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
