#!/usr/bin/env python3
"""Scan 0x1000 block on Huawei EMS-4805A1."""

import time
import serial

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


def read_chunk(ser, start_reg, count):
    pdu = bytes([SLAVE_ID, 0x03, (start_reg >> 8) & 0xFF, start_reg & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
    frame = pdu + calc_crc16(pdu)
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    time.sleep(0.08)
    rx = ser.read(256)
    return rx


def main():
    ser = serial.Serial(PORT, 9600, parity=serial.PARITY_NONE, timeout=0.6)
    time.sleep(0.05)
    
    rx = read_chunk(ser, 0x1000, 16)
    if rx and len(rx) >= 5 and rx[-2:] == calc_crc16(rx[:-2]):
        byte_cnt = rx[2]
        raw_bytes = rx[3:3+byte_cnt]
        words = [int.from_bytes(raw_bytes[i:i+2], "big") for i in range(0, len(raw_bytes), 2)]
        print(f"0x1000 block (count={len(words)}):")
        for i, w in enumerate(words):
            addr = 0x1000 + i
            print(f"  0x{addr:04X} ({addr}): 0x{w:04X} ({w})")
        # Try ASCII decoding of bytes
        ascii_chars = "".join([chr(b) if 32 <= b <= 126 else "." for b in raw_bytes])
        print(f"  ASCII representation: {ascii_chars}")
    else:
        print(f"Error reading 0x1000: {rx.hex(' ') if rx else 'Timeout'}")

    ser.close()


if __name__ == "__main__":
    main()
