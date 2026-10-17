"""Register Database Management, Search, and Import/Export Routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from ..state import app_context

router = APIRouter(prefix="/api/registers", tags=["Registers"])


@router.get("")
def list_registers(category: str = None):
    """List registered Modbus definitions with metadata."""
    regs = app_context.register_db.filter(category=category)
    return {"registers": [r.to_dict() for r in regs], "total": len(regs)}


@router.post("/import-json")
async def import_registers_json(file: UploadFile = File(...)):
    """Import register map from an uploaded JSON file."""
    content = await file.read()
    try:
        count = app_context.register_db.import_from_json(content.decode("utf-8"))
        return {"success": True, "imported_count": count, "message": f"Successfully imported {count} registers."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import JSON: {str(e)}")


@router.post("/import-csv")
async def import_registers_csv(file: UploadFile = File(...)):
    """Import register map from an uploaded CSV file."""
    content = await file.read()
    try:
        count = app_context.register_db.import_from_csv(content.decode("utf-8"))
        return {"success": True, "imported_count": count, "message": f"Successfully imported {count} registers."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import CSV: {str(e)}")


@router.get("/export-json")
def export_registers_json():
    """Export current register database as formatted JSON."""
    return PlainTextResponse(app_context.register_db.export_to_json(), media_type="application/json")


@router.get("/export-csv")
def export_registers_csv():
    """Export current register database as CSV."""
    return PlainTextResponse(app_context.register_db.export_to_csv(), media_type="text/csv")
