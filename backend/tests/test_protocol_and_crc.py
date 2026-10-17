"""Unit tests for CRC-16, Modbus RTU Framing, and Exception Handling."""

import pytest
from app.protocol.crc16 import append_crc16, calculate_crc16, verify_crc16
from app.protocol.modbus_rtu import ModbusExceptionCode, ModbusFunctionCode, ModbusRTUAdapter


def test_crc16_known_vectors():
    # Standard Modbus test vector: 0x01 0x03 0x00 0x00 0x00 0x0A => CRC 0xC5CD (Lo=0xC5, Hi=0xCD)
    data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
    crc = calculate_crc16(data)
    assert crc == 0xCDC5  # int representation (Hi: 0xCD, Lo: 0xC5)

    frame = append_crc16(data)
    assert len(frame) == 8
    assert frame[-2] == 0xC5  # Low byte first
    assert frame[-1] == 0xCD  # High byte second
    assert verify_crc16(frame) is True


def test_crc16_corrupted_frame():
    data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
    frame = append_crc16(data)
    # Corrupt one bit
    corrupted = bytearray(frame)
    corrupted[2] ^= 0x01
    assert verify_crc16(corrupted) is False


def test_modbus_rtu_build_read_holding():
    adapter = ModbusRTUAdapter()
    frame = adapter.build_read_holding_registers(slave_id=1, start_address=37000, count=10)
    assert len(frame) == 8
    assert frame[0] == 1
    assert frame[1] == ModbusFunctionCode.READ_HOLDING_REGISTERS
    assert verify_crc16(frame) is True


def test_modbus_rtu_build_write_single():
    adapter = ModbusRTUAdapter()
    frame = adapter.build_write_single_register(slave_id=1, address=47085, value=50)
    assert len(frame) == 8
    assert frame[0] == 1
    assert frame[1] == ModbusFunctionCode.WRITE_SINGLE_REGISTER
    assert verify_crc16(frame) is True


def test_modbus_rtu_parse_valid_response():
    adapter = ModbusRTUAdapter()
    # Mock response for Read Holding 2 registers (4 bytes): [0x01, 0x03, 0x04, 0x0F, 0xA0, 0x00, 0x64]
    payload = bytes([0x01, 0x03, 0x04, 0x0F, 0xA0, 0x00, 0x64])
    resp_frame = append_crc16(payload)

    parsed = adapter.parse_response(expected_slave_id=1, expected_function_code=3, response_bytes=resp_frame)
    assert parsed.success is True
    assert parsed.values == [4000, 100]


def test_modbus_rtu_parse_exception_response():
    adapter = ModbusRTUAdapter()
    # Illegal Data Address (0x02) on Read Holding (0x03) => 0x83
    payload = bytes([0x01, 0x83, ModbusExceptionCode.ILLEGAL_DATA_ADDRESS])
    err_frame = append_crc16(payload)

    parsed = adapter.parse_response(expected_slave_id=1, expected_function_code=3, response_bytes=err_frame)
    assert parsed.success is False
    assert parsed.is_exception is True
    assert parsed.exception_code == ModbusExceptionCode.ILLEGAL_DATA_ADDRESS
    assert "Illegal Data Address" in parsed.error_message
