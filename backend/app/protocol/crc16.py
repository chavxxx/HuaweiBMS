"""Modbus RTU standard CRC-16 implementation.

Uses polynomial 0xA001 (reversed representation of 0x8005) with initial value 0xFFFF.
Matches standard Modbus RTU specification (Low-byte first in transmitted frames).
"""

from typing import Union


def calculate_crc16(data: Union[bytes, bytearray, list[int]]) -> int:
    """Calculate the 16-bit CRC for a given byte buffer.

    Returns the integer CRC value (0x0000 to 0xFFFF).
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def append_crc16(data: Union[bytes, bytearray]) -> bytes:
    """Append low-byte then high-byte of CRC-16 to the data.

    Returns complete Modbus RTU frame as bytes.
    """
    crc = calculate_crc16(data)
    # Modbus RTU transmits CRC Low Byte first, then High Byte
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    return bytes(data) + bytes([crc_low, crc_high])


def verify_crc16(frame: Union[bytes, bytearray]) -> bool:
    """Verify that the frame's last two bytes match the CRC-16 of preceding bytes."""
    if len(frame) < 3:
        return False
    payload = frame[:-2]
    expected_crc = calculate_crc16(payload)
    actual_low = frame[-2]
    actual_high = frame[-1]
    actual_crc = actual_low | (actual_high << 8)
    return expected_crc == actual_crc
