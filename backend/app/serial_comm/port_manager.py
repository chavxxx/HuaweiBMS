"""Serial Port Discovery, Enumeration, and Connection Manager."""

import logging
import platform
import re
import time
from dataclasses import asdict, dataclass
from typing import Optional
import serial.tools.list_ports

logger = logging.getLogger("huawei_bms.port_manager")

KNOWN_RS485_VIDS = {
    0x0403: "FTDI",            # FT232R, FT232H, FT2232
    0x1A86: "WCH",             # CH340, CH341
    0x10C4: "Silicon Labs",    # CP2102, CP2104
    0x067B: "Prolific",        # PL2303
    0x04D8: "Microchip",
    0x2341: "Arduino",
}


@dataclass
class SerialPortInfo:
    device: str
    name: str
    description: str
    hwid: str
    vid: Optional[int] = None
    pid: Optional[int] = None
    vid_hex: Optional[str] = None
    pid_hex: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    is_rs485_candidate: bool = False
    interface: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class PortManager:
    """Discovers and inspects serial adapters across Windows, Linux, and macOS."""

    @staticmethod
    def list_ports() -> list[SerialPortInfo]:
        """Enumerate available system serial ports with rich metadata."""
        ports = serial.tools.list_ports.comports()
        result: list[SerialPortInfo] = []

        for p in ports:
            vid = p.vid
            pid = p.pid
            vid_hex = f"0x{vid:04X}" if vid is not None else None
            pid_hex = f"0x{pid:04X}" if pid is not None else None

            # Detect if adapter is likely a USB-to-RS485 adapter
            desc_lower = (p.description or "").lower()
            mfg_lower = (p.manufacturer or "").lower()
            is_candidate = False

            if vid in KNOWN_RS485_VIDS:
                is_candidate = True
            elif any(k in desc_lower for k in ("rs485", "rs-485", "ftdi", "ch340", "cp210", "uart", "serial", "prolific")):
                is_candidate = True
            elif any(k in mfg_lower for k in ("ftdi", "wch", "silicon labs", "prolific")):
                is_candidate = True

            # Filter out obvious Bluetooth/audio ports on macOS unless explicitly chosen
            if platform.system() == "Darwin" and any(b in p.device.lower() for b in ("bluetooth", "bose", "jbl", "emberton", "buds")):
                is_candidate = False

            info = SerialPortInfo(
                device=p.device,
                name=p.name or p.device,
                description=p.description or "Standard Serial Port",
                hwid=p.hwid or "",
                vid=vid,
                pid=pid,
                vid_hex=vid_hex,
                pid_hex=pid_hex,
                serial_number=p.serial_number,
                manufacturer=p.manufacturer or KNOWN_RS485_VIDS.get(vid, "Unknown"),
                is_rs485_candidate=is_candidate,
                interface=p.interface
            )
            result.append(info)

        # Sort so candidate RS485 adapters appear at the top
        result.sort(key=lambda x: (not x.is_rs485_candidate, x.device))
        return result

    @staticmethod
    def port_exists(port_path: str) -> bool:
        """Check if a specific port device path is physically connected."""
        available = [p.device for p in serial.tools.list_ports.comports()]
        return port_path in available
