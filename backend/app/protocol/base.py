"""Protocol Adapter Interface and Data Classes for BMS Communication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ModbusFunctionCode(int, Enum):
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_REGISTERS = 0x10


class ModbusExceptionCode(int, Enum):
    ILLEGAL_FUNCTION = 0x01
    ILLEGAL_DATA_ADDRESS = 0x02
    ILLEGAL_DATA_VALUE = 0x03
    SERVER_DEVICE_FAILURE = 0x04
    ACKNOWLEDGE = 0x05
    SERVER_DEVICE_BUSY = 0x06
    MEMORY_PARITY_ERROR = 0x08
    GATEWAY_PATH_UNAVAILABLE = 0x0A
    GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND = 0x0B


@dataclass
class ProtocolFrame:
    """Diagnostic protocol frame representation for tracing and analysis."""
    timestamp: float
    direction: str  # 'TX' or 'RX'
    raw_bytes: bytes
    raw_hex: str
    slave_id: int
    function_code: int
    function_name: str
    is_exception: bool = False
    exception_code: Optional[int] = None
    exception_message: Optional[str] = None
    register_address: Optional[int] = None
    register_count: Optional[int] = None
    values: list[int] = field(default_factory=list)
    crc_valid: bool = True
    error: Optional[str] = None


@dataclass
class ProtocolResponse:
    """Result of an executed protocol request."""
    success: bool
    function_code: int
    values: list[int] = field(default_factory=list)
    raw_frame: bytes = b""
    is_exception: bool = False
    exception_code: Optional[int] = None
    exception_message: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: float = 0.0


class ProtocolAdapter(ABC):
    """Abstract base class for BMS serial protocol implementations."""

    @abstractmethod
    def build_read_holding_registers(self, slave_id: int, start_address: int, count: int) -> bytes:
        """Construct frame to read holding registers."""
        pass

    @abstractmethod
    def build_read_input_registers(self, slave_id: int, start_address: int, count: int) -> bytes:
        """Construct frame to read input registers."""
        pass

    @abstractmethod
    def build_write_single_register(self, slave_id: int, address: int, value: int) -> bytes:
        """Construct frame to write a single register."""
        pass

    @abstractmethod
    def build_write_multiple_registers(self, slave_id: int, start_address: int, values: list[int]) -> bytes:
        """Construct frame to write multiple registers."""
        pass

    @abstractmethod
    def parse_response(self, expected_slave_id: int, expected_function_code: int, response_bytes: bytes) -> ProtocolResponse:
        """Parse, validate CRC, check framing and extract values or exceptions."""
        pass

    @abstractmethod
    def decode_frame_for_diagnostics(self, frame_bytes: bytes, direction: str, timestamp: float) -> ProtocolFrame:
        """Decode raw frame for human-readable live protocol analyzer."""
        pass
