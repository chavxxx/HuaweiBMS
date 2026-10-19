"""Pydantic Request and Response Schemas."""

from typing import Any, Optional, Union
from pydantic import BaseModel, Field


class SerialConnectRequest(BaseModel):
    port: str
    baudrate: int = Field(9600, description="Baud rate (e.g. 9600, 19200, 115200)")
    bytesize: int = Field(8, description="Data bits (7 or 8)")
    parity: str = Field("E", description="'N' (None), 'E' (Even), 'O' (Odd)")
    stopbits: float = Field(1.0, description="1 or 2 stop bits")
    timeout: float = Field(0.8, description="Response timeout in seconds")
    inter_frame_delay: float = Field(0.035, description="Inter-frame delay in seconds (RS485)")
    slave_id: int = Field(214, description="Modbus slave address (1-247, 214 for Huawei Standalone, 1-16 for DIP cascaded)")
    rs485_rts_control: bool = Field(False, description="Toggle RTS pin for half-duplex direction")
    auto_reconnect: bool = Field(True, description="Automatically attempt reconnect on drop")
    use_simulation: bool = Field(False, description="Explicitly toggle virtual BMS simulator")



class ParameterWriteRequest(BaseModel):
    address: int
    new_value: Union[int, float]
    user_role: str = "ADMINISTRATOR"
    operator_confirmed: bool = False


class EnableWritesRequest(BaseModel):
    user_role: str = "ADMINISTRATOR"
    confirmation_key: Optional[str] = None


class ApplyPresetRequest(BaseModel):
    preset_id: str = Field(..., description="ID of preset to apply")
    user_role: str = "ADMINISTRATOR"
    operator_confirmed: bool = True


class UnlockBatteryRequest(BaseModel):
    user_role: str = "ADMINISTRATOR"
    sync_clock: bool = True
    restore_charge_rate: float = Field(0.500, description="Charge limit coefficient in C (0.05-1.05)")


class SnapshotCreateRequest(BaseModel):
    snapshot_name: str
    notes: Optional[str] = ""
    author_role: str = "OPERATOR"


class RawFrameTransmitRequest(BaseModel):
    raw_hex: str
    safety_override: bool = False
    operator_confirmed: bool = False
    user_role: str = "ADMINISTRATOR"


class AppSettingsUpdate(BaseModel):
    low_soc_threshold: Optional[float] = 15.0
    high_temp_threshold: Optional[float] = 50.0
    max_delta_v_mv_threshold: Optional[float] = 60.0
    telemetry_stale_seconds: Optional[float] = 5.0
    theme: Optional[str] = "dark"
    retention_days: Optional[int] = 30
