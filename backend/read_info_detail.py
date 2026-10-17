#!/usr/bin/env python3
"""Read 0x0100 - 0x0130 in detail."""

import serial
import time

PORT = "/dev/cu.usbserial-BG01GGUB"
SLAVE_ID = 214

def calc_crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

ser = serial.Serial(PORT, 9600, parity=serial.PARITY_NONE, timeout=0.6)
time.sleep(0.05)

for addr in range(0x0100, 0x0120):
    pdu = bytes([SLAVE_ID, 0x03, (addr >> 8) & 0xFF, addr & 0xFF, 0x00, 0x01])
    frame = pdu + calc_crc16(pdu)
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    time.sleep(0.03)
    rx = ser.read(32)
    if rx and len(rx) >= 5 and rx[-2:] == calc_crc16(rx[:-2]) and rx[1] == 0x03:
        b1, b2 = rx[3], rx[4]
        c1 = chr(b1) if 32 <= b1 <= 126 else f"\\x{b1:02x}"
        c2 = chr(b2) if 32 <= b2 <= 126 else f"\\x{b2:02x}"
        print(f"0x{addr:04X} ({addr:3d}): 0x{b1:02X}{b2:02X} ({int.from_bytes([b1,b2], 'big'):5d}) -> '{c1}{c2}'")

ser.close()
