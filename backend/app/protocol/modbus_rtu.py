"""Standard Modbus RTU Protocol Implementation with Strict Frame Validation."""

import struct
from typing import Optional
from .base import (
    ModbusExceptionCode,
    ModbusFunctionCode,
    ProtocolAdapter,
    ProtocolFrame,
    ProtocolResponse,
)
from .crc16 import append_crc16, verify_crc16

EXCEPTION_DESCRIPTIONS = {
    ModbusExceptionCode.ILLEGAL_FUNCTION: "Illegal Function: Function code not supported by the BMS.",
    ModbusExceptionCode.ILLEGAL_DATA_ADDRESS: "Illegal Data Address: The requested register address is unsupported or out of range.",
    ModbusExceptionCode.ILLEGAL_DATA_VALUE: "Illegal Data Value: The value or register quantity in request is not permissible.",
    ModbusExceptionCode.SERVER_DEVICE_FAILURE: "Server Device Failure: BMS experienced an internal failure handling the command.",
    ModbusExceptionCode.ACKNOWLEDGE: "Acknowledge: BMS accepted request and is processing it asynchronously.",
    ModbusExceptionCode.SERVER_DEVICE_BUSY: "Server Device Busy: BMS is busy and cannot process request now. Retry after backoff.",
    ModbusExceptionCode.MEMORY_PARITY_ERROR: "Memory Parity Error: BMS detected parity error reading target memory.",
    ModbusExceptionCode.GATEWAY_PATH_UNAVAILABLE: "Gateway Path Unavailable.",
    ModbusExceptionCode.GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND: "Gateway Target Device Failed to Respond.",
}


class ModbusRTUAdapter(ProtocolAdapter):
    """Modbus RTU framing engine with strict CRC verification and error reporting."""

    def build_read_holding_registers(self, slave_id: int, start_address: int, count: int) -> bytes:
        """Function 0x03: Read Holding Registers.
        Format: [SlaveID] [0x03] [StartAddr_Hi] [StartAddr_Lo] [Count_Hi] [Count_Lo] [CRC_Lo] [CRC_Hi]
        """
        if not (1 <= slave_id <= 247):
            raise ValueError(f"Invalid slave ID {slave_id} (must be 1-247)")
        if not (1 <= count <= 125):
            raise ValueError(f"Invalid register count {count} for Read Holding (max 125)")
        payload = struct.pack(">BBHH", slave_id, ModbusFunctionCode.READ_HOLDING_REGISTERS, start_address, count)
        return append_crc16(payload)

    def build_read_input_registers(self, slave_id: int, start_address: int, count: int) -> bytes:
        """Function 0x04: Read Input Registers.
        Format: [SlaveID] [0x04] [StartAddr_Hi] [StartAddr_Lo] [Count_Hi] [Count_Lo] [CRC_Lo] [CRC_Hi]
        """
        if not (1 <= slave_id <= 247):
            raise ValueError(f"Invalid slave ID {slave_id} (must be 1-247)")
        if not (1 <= count <= 125):
            raise ValueError(f"Invalid register count {count} for Read Input (max 125)")
        payload = struct.pack(">BBHH", slave_id, ModbusFunctionCode.READ_INPUT_REGISTERS, start_address, count)
        return append_crc16(payload)

    def build_write_single_register(self, slave_id: int, address: int, value: int) -> bytes:
        """Function 0x06: Write Single Register.
        Format: [SlaveID] [0x06] [Addr_Hi] [Addr_Lo] [Val_Hi] [Val_Lo] [CRC_Lo] [CRC_Hi]
        """
        if not (1 <= slave_id <= 247):
            raise ValueError(f"Invalid slave ID {slave_id} (must be 1-247)")
        payload = struct.pack(">BBHH", slave_id, ModbusFunctionCode.WRITE_SINGLE_REGISTER, address, value & 0xFFFF)
        return append_crc16(payload)

    def build_write_multiple_registers(self, slave_id: int, start_address: int, values: list[int]) -> bytes:
        """Function 0x10: Write Multiple Registers.
        Format: [SlaveID] [0x10] [StartAddr_Hi] [StartAddr_Lo] [Count_Hi] [Count_Lo] [ByteCount] [Val1_Hi] [Val1_Lo] ... [CRC_Lo] [CRC_Hi]
        """
        if not (1 <= slave_id <= 247):
            raise ValueError(f"Invalid slave ID {slave_id} (must be 1-247)")
        count = len(values)
        if not (1 <= count <= 123):
            raise ValueError(f"Invalid register count {count} for Write Multiple (max 123)")
        byte_count = count * 2
        header = struct.pack(">BBHHB", slave_id, ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS, start_address, count, byte_count)
        val_bytes = b"".join(struct.pack(">H", v & 0xFFFF) for v in values)
        return append_crc16(header + val_bytes)

    def parse_response(self, expected_slave_id: int, expected_function_code: int, response_bytes: bytes) -> ProtocolResponse:
        """Parse raw response from BMS, verifying length, CRC, address, and function code."""
        if not response_bytes or len(response_bytes) < 5:
            return ProtocolResponse(
                success=False,
                function_code=expected_function_code,
                raw_frame=response_bytes,
                error_message=f"Response frame too short ({len(response_bytes)} bytes; minimum is 5 bytes)"
            )

        # 1. Strict CRC Verification
        if not verify_crc16(response_bytes):
            return ProtocolResponse(
                success=False,
                function_code=expected_function_code,
                raw_frame=response_bytes,
                error_message="CRC verification failed: corrupted transmission frame"
            )

        slave_id = response_bytes[0]
        if slave_id != expected_slave_id:
            return ProtocolResponse(
                success=False,
                function_code=expected_function_code,
                raw_frame=response_bytes,
                error_message=f"Slave ID mismatch: expected {expected_slave_id}, received {slave_id}"
            )

        func_code = response_bytes[1]

        # 2. Check for Modbus Exception Response (Function Code | 0x80)
        if func_code == (expected_function_code | 0x80):
            exception_code = response_bytes[2]
            msg = EXCEPTION_DESCRIPTIONS.get(exception_code, f"Unknown Modbus exception code 0x{exception_code:02X}")
            return ProtocolResponse(
                success=False,
                function_code=func_code,
                raw_frame=response_bytes,
                is_exception=True,
                exception_code=exception_code,
                exception_message=msg,
                error_message=f"BMS Exception 0x{exception_code:02X}: {msg}"
            )

        if func_code != expected_function_code:
            return ProtocolResponse(
                success=False,
                function_code=func_code,
                raw_frame=response_bytes,
                error_message=f"Unexpected function code in response: expected 0x{expected_function_code:02X}, received 0x{func_code:02X}"
            )

        # 3. Handle Normal Data Responses
        if func_code in (ModbusFunctionCode.READ_HOLDING_REGISTERS, ModbusFunctionCode.READ_INPUT_REGISTERS):
            byte_count = response_bytes[2]
            expected_total_len = 3 + byte_count + 2
            if len(response_bytes) != expected_total_len:
                return ProtocolResponse(
                    success=False,
                    function_code=func_code,
                    raw_frame=response_bytes,
                    error_message=f"Data length mismatch: byte count says {byte_count}, frame is {len(response_bytes)} bytes"
                )
            # Unpack 16-bit register values (Big Endian)
            reg_bytes = response_bytes[3:3 + byte_count]
            num_registers = byte_count // 2
            values = list(struct.unpack(f">{num_registers}H", reg_bytes))
            return ProtocolResponse(
                success=True,
                function_code=func_code,
                values=values,
                raw_frame=response_bytes
            )

        elif func_code == ModbusFunctionCode.WRITE_SINGLE_REGISTER:
            # Echo of address and value
            if len(response_bytes) != 8:
                return ProtocolResponse(
                    success=False,
                    function_code=func_code,
                    raw_frame=response_bytes,
                    error_message=f"Write single register echo invalid length ({len(response_bytes)} bytes)"
                )
            addr, val = struct.unpack(">HH", response_bytes[2:6])
            return ProtocolResponse(
                success=True,
                function_code=func_code,
                values=[addr, val],
                raw_frame=response_bytes
            )

        elif func_code == ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS:
            # Echo of address and count
            if len(response_bytes) != 8:
                return ProtocolResponse(
                    success=False,
                    function_code=func_code,
                    raw_frame=response_bytes,
                    error_message=f"Write multiple registers echo invalid length ({len(response_bytes)} bytes)"
                )
            addr, count = struct.unpack(">HH", response_bytes[2:6])
            return ProtocolResponse(
                success=True,
                function_code=func_code,
                values=[addr, count],
                raw_frame=response_bytes
            )

        return ProtocolResponse(
            success=True,
            function_code=func_code,
            raw_frame=response_bytes
        )

    def decode_frame_for_diagnostics(self, frame_bytes: bytes, direction: str, timestamp: float) -> ProtocolFrame:
        """Decode a raw frame into detailed diagnostics for the live protocol analyzer."""
        hex_repr = frame_bytes.hex(" ").upper()
        if len(frame_bytes) < 3:
            return ProtocolFrame(
                timestamp=timestamp,
                direction=direction,
                raw_bytes=frame_bytes,
                raw_hex=hex_repr,
                slave_id=frame_bytes[0] if len(frame_bytes) > 0 else 0,
                function_code=frame_bytes[1] if len(frame_bytes) > 1 else 0,
                function_name="MALFORMED_SHORT",
                crc_valid=False,
                error="Frame shorter than 3 bytes"
            )

        crc_ok = verify_crc16(frame_bytes)
        slave_id = frame_bytes[0]
        raw_func = frame_bytes[1]
        is_exception = bool(raw_func & 0x80)
        base_func = raw_func & 0x7F

        func_names = {
            0x01: "Read Coils",
            0x02: "Read Discrete Inputs",
            0x03: "Read Holding Registers",
            0x04: "Read Input Registers",
            0x05: "Write Single Coil",
            0x06: "Write Single Register",
            0x10: "Write Multiple Registers",
        }
        name = func_names.get(base_func, f"Custom Func 0x{base_func:02X}")
        if is_exception:
            name += " [EXCEPTION RESPONSE]"

        exc_code = None
        exc_msg = None
        addr = None
        cnt = None
        vals = []

        if is_exception and len(frame_bytes) >= 5:
            exc_code = frame_bytes[2]
            exc_msg = EXCEPTION_DESCRIPTIONS.get(exc_code, f"Exception 0x{exc_code:02X}")
        elif direction == "TX" and len(frame_bytes) >= 6:
            if base_func in (0x03, 0x04):
                addr, cnt = struct.unpack(">HH", frame_bytes[2:6])
            elif base_func == 0x06:
                addr, val = struct.unpack(">HH", frame_bytes[2:6])
                vals = [val]
            elif base_func == 0x10 and len(frame_bytes) >= 7:
                addr, cnt = struct.unpack(">HH", frame_bytes[2:6])
        elif direction == "RX" and not is_exception and len(frame_bytes) >= 5:
            if base_func in (0x03, 0x04):
                byte_cnt = frame_bytes[2]
                reg_count = byte_cnt // 2
                if len(frame_bytes) >= 3 + byte_cnt + 2:
                    vals = list(struct.unpack(f">{reg_count}H", frame_bytes[3:3 + byte_cnt]))

        return ProtocolFrame(
            timestamp=timestamp,
            direction=direction,
            raw_bytes=frame_bytes,
            raw_hex=hex_repr,
            slave_id=slave_id,
            function_code=raw_func,
            function_name=name,
            is_exception=is_exception,
            exception_code=exc_code,
            exception_message=exc_msg,
            register_address=addr,
            register_count=cnt,
            values=vals,
            crc_valid=crc_ok,
            error=None if crc_ok else "CRC mismatch"
        )
