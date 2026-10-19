"""Serial Ports and Connection Routes."""

from fastapi import APIRouter, HTTPException
from ..schemas.schemas import SerialConnectRequest
from ..serial_comm.port_manager import PortManager
from ..serial_comm.serial_client import SerialConfig
from ..state import app_context

router = APIRouter(prefix="/api/ports", tags=["Ports"])


@router.get("")
def list_ports():
    """Enumerate all serial ports with detailed OS metadata."""
    ports = PortManager.list_ports()
    return {"ports": [p.to_dict() for p in ports]}


@router.get("/status")
def get_connection_status():
    """Retrieve current connection status, parameters, and simulation flag."""
    freshness = app_context.telemetry_service.get_freshness_status()
    comm_diag = app_context.serial_client.get_diagnostics()
    return {
        "is_connected": app_context.serial_client.is_connected,
        "is_simulation": app_context.telemetry_service.use_simulation,
        "port": app_context.serial_client.config.port,
        "baudrate": app_context.serial_client.config.baudrate,
        "slave_id": app_context.serial_client.config.slave_id,
        "parity": app_context.serial_client.config.parity,
        "stopbits": app_context.serial_client.config.stopbits,
        "timeout": app_context.serial_client.config.timeout,
        "inter_frame_delay": app_context.serial_client.config.inter_frame_delay,
        "freshness": freshness,
        "stats": comm_diag["stats"],
    }


@router.post("/connect")
def connect_port(req: SerialConnectRequest):
    """Open serial port connection or switch to simulated BMS."""
    if req.use_simulation:
        app_context.telemetry_service.use_simulation = True
        app_context.serial_client.disconnect()
        return {
            "success": True,
            "message": "Switched to Virtual Huawei EMS B1 BMS Simulator.",
            "is_simulation": True
        }

    config = SerialConfig(
        port=req.port,
        baudrate=req.baudrate,
        bytesize=req.bytesize,
        parity=req.parity,
        stopbits=req.stopbits,
        timeout=req.timeout,
        inter_frame_delay=req.inter_frame_delay,
        slave_id=req.slave_id,
        rs485_rts_control=req.rs485_rts_control,
        auto_reconnect=req.auto_reconnect
    )

    try:
        app_context.serial_client.connect(config)
        app_context.telemetry_service.reset_telemetry_for_hardware()
        app_context.multi_battery_service.active_slave_id = req.slave_id
        app_context.multi_battery_service.add_battery(req.slave_id, f"Battery #{req.slave_id}")

        # Auto-detect whether battery is responding at req.slave_id or alternate common Huawei address
        detected_id = app_context.telemetry_service.probe_and_detect_slave_id(req.slave_id)
        if detected_id and detected_id != req.slave_id:
            msg = f"Connected to {req.port} ({req.baudrate} 8{req.parity}{int(req.stopbits)}) — Auto-detected battery responding at Slave ID {detected_id}."
        else:
            msg = f"Connected to {req.port} ({req.baudrate} 8{req.parity}{int(req.stopbits)}, Slave ID {app_context.serial_client.config.slave_id})."

        return {
            "success": True,
            "message": msg,
            "is_simulation": False,
            "active_slave_id": app_context.serial_client.config.slave_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/disconnect")
def disconnect_port():
    """Close physical serial port and stop polling."""
    app_context.serial_client.disconnect()
    app_context.telemetry_service.reset_telemetry_for_hardware()
    return {"success": True, "message": "Serial port disconnected."}


@router.post("/toggle-simulation")
def toggle_simulation(enabled: bool):
    """Explicitly enable or disable virtual simulation mode."""
    if enabled:
        app_context.telemetry_service.use_simulation = True
        app_context.serial_client.disconnect()
    else:
        app_context.telemetry_service.reset_telemetry_for_hardware()

    return {
        "success": True,
        "is_simulation": app_context.telemetry_service.use_simulation,
        "message": "Simulation mode activated." if enabled else "Physical hardware mode selected (simulated state cleared)."
    }
