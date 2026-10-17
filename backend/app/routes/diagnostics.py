"""Communication Diagnostics and Protocol Analyzer Routes."""

from fastapi import APIRouter, HTTPException
from ..database.crud import AuditCRUD
from ..schemas.schemas import RawFrameTransmitRequest
from ..state import app_context

router = APIRouter(prefix="/api/diagnostics", tags=["Diagnostics"])


@router.get("/comm")
def get_comm_diagnostics():
    """Get serial connection stats (requests, responses, latency, timeouts, CRC errors, retries)."""
    return app_context.serial_client.get_diagnostics()


@router.get("/trace")
def get_protocol_trace():
    """Retrieve recent protocol analyzer trace entries for live inspection."""
    return {"trace": app_context.serial_client.get_full_trace()}


@router.post("/transmit-raw")
def transmit_raw_frame(req: RawFrameTransmitRequest):
    """Transmit arbitrary raw Modbus frame (Strictly gated engineering tool)."""
    if req.user_role.upper() != "ADMINISTRATOR":
        raise HTTPException(status_code=403, detail="Raw frame transmission requires Administrator role.")

    if not req.safety_override or not req.operator_confirmed:
        raise HTTPException(status_code=400, detail="Explicit safety override and operator confirmation are required.")

    # Parse hex string
    cleaned_hex = req.raw_hex.replace(" ", "").strip()
    try:
        raw_bytes = bytes.fromhex(cleaned_hex)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid hex string: {str(e)}")

    if len(raw_bytes) < 4:
        raise HTTPException(status_code=400, detail="Frame too short (minimum 4 bytes required).")

    # Safety command filter: block destructive functions
    func_code = raw_bytes[1]
    if func_code in (0x05, 0x0F):  # Coil writes (contactors)
        raise HTTPException(status_code=403, detail="DANGER: Direct contactor coil commands are permanently prohibited via raw frame transmitter.")

    AuditCRUD.record_entry({
        "user_role": req.user_role,
        "action": "TRANSMIT_RAW_FRAME",
        "requested_value": req.raw_hex,
        "status": "EXECUTED",
        "details": f"Raw transmission of {len(raw_bytes)} bytes."
    })

    if app_context.telemetry_service.use_simulation:
        resp_bytes = app_context.simulator.process_raw_frame(raw_bytes)
        return {
            "success": True,
            "is_simulation": True,
            "response_hex": resp_bytes.hex(" ").upper() if resp_bytes else "",
            "message": "Processed by Virtual BMS."
        }
    else:
        if not app_context.serial_client.is_connected:
            raise HTTPException(status_code=400, detail="Physical serial port not connected.")
        # Execute on serial bus
        resp = app_context.serial_client.execute_transaction(raw_bytes, func_code, is_write=True)
        return {
            "success": resp.success,
            "is_simulation": False,
            "response_hex": resp.raw_frame.hex(" ").upper() if resp.raw_frame else "",
            "error": resp.error_message,
        }
