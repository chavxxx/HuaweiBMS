"""Thread-safe native serial communication client with RS485 half-duplex timing."""

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Optional, Union
import serial
from ..protocol.base import ProtocolAdapter, ProtocolFrame, ProtocolResponse
from ..protocol.modbus_rtu import ModbusRTUAdapter

logger = logging.getLogger("huawei_bms.serial_client")


@dataclass
class SerialConfig:
    port: str = ""
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"          # 'N', 'E', 'O'
    stopbits: float = 1        # 1, 1.5, 2
    timeout: float = 1.0       # Seconds
    inter_frame_delay: float = 0.02  # 20ms inter-frame delay
    retry_count: int = 2
    slave_id: int = 1
    rs485_rts_control: bool = False
    auto_reconnect: bool = True
    reconnect_backoff_sec: float = 2.0
    protocol: str = "modbus_rtu"  # 'modbus_rtu' or 'huawei_proto'
    profile_name: Optional[str] = None


@dataclass
class CommStatistics:
    total_requests: int = 0
    total_responses: int = 0
    total_timeouts: int = 0
    total_crc_errors: int = 0
    total_retries: int = 0
    last_latency_ms: float = 0.0
    average_latency_ms: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    last_success_time: Optional[float] = None
    bytes_sent: int = 0
    bytes_received: int = 0


class SerialClient:
    """Thread-safe serial port wrapper managing requests, timeouts, retries, and trace logs."""

    def __init__(self, config: Optional[SerialConfig] = None):
        self.config = config or SerialConfig()
        self.adapter: ProtocolAdapter = ModbusRTUAdapter()
        self.stats = CommStatistics()
        self.is_connected = False
        self.is_reconnecting = False
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._trace_buffer: deque[ProtocolFrame] = deque(maxlen=250)
        self._latencies: deque[float] = deque(maxlen=50)

    def connect(self, config: Optional[SerialConfig] = None) -> bool:
        """Open the serial port with configured baudrate and parity."""
        with self._lock:
            if config:
                self.config = config
            if not self.config.port:
                raise ValueError("No serial port specified")

            self._close_internal()

            parity_map = {
                "N": serial.PARITY_NONE,
                "E": serial.PARITY_EVEN,
                "O": serial.PARITY_ODD,
            }
            parity_val = parity_map.get(self.config.parity.upper(), serial.PARITY_NONE)

            stopbits_map = {
                1: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2: serial.STOPBITS_TWO,
            }
            stopbits_val = stopbits_map.get(self.config.stopbits, serial.STOPBITS_ONE)

            try:
                self._serial = serial.Serial(
                    port=self.config.port,
                    baudrate=self.config.baudrate,
                    bytesize=self.config.bytesize,
                    parity=parity_val,
                    stopbits=stopbits_val,
                    timeout=self.config.timeout,
                    write_timeout=self.config.timeout,
                )
                # Flush input/output buffers
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
                self.is_connected = True
                self.stats.last_error = None
                logger.info("Connected to serial port %s at %d baud", self.config.port, self.config.baudrate)
                return True
            except Exception as e:
                self.is_connected = False
                self.stats.last_error = f"Failed to open port {self.config.port}: {str(e)}"
                self.stats.last_error_time = time.time()
                logger.error("Connection failed: %s", self.stats.last_error)
                raise ConnectionError(self.stats.last_error) from e

    def disconnect(self) -> None:
        """Cleanly close the serial port."""
        with self._lock:
            self._close_internal()
            self.is_connected = False

    def _close_internal(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def execute_transaction(
        self,
        request_frame: bytes,
        expected_func_code: int,
        is_write: bool = False
    ) -> ProtocolResponse:
        """Execute a full request/response cycle on the serial bus."""
        with self._lock:
            if not self.is_connected or not self._serial or not self._serial.is_open:
                raise ConnectionError("Serial port is not connected")

            start_t = time.perf_counter()
            self.stats.total_requests += 1
            self.stats.bytes_sent += len(request_frame)

            # Record TX frame in diagnostics trace
            tx_diag = self.adapter.decode_frame_for_diagnostics(request_frame, "TX", time.time())
            self._trace_buffer.append(tx_diag)

            # Inter-frame delay before transmitting
            if self.config.inter_frame_delay > 0:
                time.sleep(self.config.inter_frame_delay)

            # RTS half-duplex transmit toggle if enabled
            if self.config.rs485_rts_control and self._serial:
                try:
                    self._serial.rts = True
                except Exception:
                    pass

            try:
                self._serial.reset_input_buffer()
                self._serial.write(request_frame)
                self._serial.flush()
            except Exception as e:
                self.is_connected = False
                self.stats.last_error = f"Write error: {str(e)}"
                self.stats.last_error_time = time.time()
                raise ConnectionError(self.stats.last_error) from e
            finally:
                if self.config.rs485_rts_control and self._serial:
                    try:
                        self._serial.rts = False
                    except Exception:
                        pass

            # Read response
            read_bytes = bytearray()
            # Read first 3 bytes (Slave ID, Function Code, ByteCount / Subcode)
            header = self._serial.read(3)
            if not header or len(header) < 3:
                self.stats.total_timeouts += 1
                self.stats.last_error = f"Response timeout after {self.config.timeout:.2f}s (received {len(header)} bytes)"
                self.stats.last_error_time = time.time()
                return ProtocolResponse(
                    success=False,
                    function_code=expected_func_code,
                    raw_frame=bytes(header),
                    error_message=self.stats.last_error
                )

            read_bytes.extend(header)
            func_code = header[1]

            # If it's an exception response (func_code | 0x80)
            if func_code & 0x80:
                # 3 bytes already read: [SlaveID, Func|0x80, ExceptionCode]. Need 2 bytes for CRC.
                crc_bytes = self._serial.read(2)
                read_bytes.extend(crc_bytes)
            elif func_code in (0x03, 0x04):
                # Byte 2 is byte count
                data_len = header[2]
                payload_and_crc = self._serial.read(data_len + 2)
                read_bytes.extend(payload_and_crc)
            elif func_code in (0x06, 0x10):
                # Fixed 8-byte response: [SlaveID, Func, Addr_H, Addr_L, Val_H, Val_L, CRC_L, CRC_H]
                # 3 bytes read, need 5 more
                remaining = self._serial.read(5)
                read_bytes.extend(remaining)
            else:
                # Read whatever remains in timeout
                rem = self._serial.read(64)
                read_bytes.extend(rem)

            latency_ms = (time.perf_counter() - start_t) * 1000.0
            self.stats.last_latency_ms = latency_ms
            self._latencies.append(latency_ms)
            self.stats.average_latency_ms = sum(self._latencies) / len(self._latencies)
            self.stats.bytes_received += len(read_bytes)
            self.stats.total_responses += 1

            # Record RX frame in diagnostics trace
            rx_diag = self.adapter.decode_frame_for_diagnostics(bytes(read_bytes), "RX", time.time())
            self._trace_buffer.append(rx_diag)

            if not rx_diag.crc_valid:
                self.stats.total_crc_errors += 1

            # Parse and validate response
            response = self.adapter.parse_response(self.config.slave_id, expected_func_code, bytes(read_bytes))
            response.latency_ms = latency_ms

            if response.success:
                self.stats.last_success_time = time.time()
                self.stats.last_error = None
            else:
                self.stats.last_error = response.error_message
                self.stats.last_error_time = time.time()

            return response

    def get_diagnostics(self) -> dict:
        """Retrieve aggregated communication metrics and recent protocol traces."""
        return {
            "is_connected": self.is_connected,
            "port": self.config.port,
            "baudrate": self.config.baudrate,
            "slave_id": self.config.slave_id,
            "stats": asdict(self.stats),
            "recent_frames": [f.to_dict() for f in list(self._trace_buffer)[-50:]]
        }

    def get_full_trace(self) -> list[dict]:
        """Export full recent diagnostic traces."""
        return [f.to_dict() for f in list(self._trace_buffer)]
