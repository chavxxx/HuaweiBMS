#!/usr/bin/env python3
"""Find ASCII strings and device identifiers on Huawei EMS-4805A1."""

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


def read_block(ser, start, count):
    pdu = bytes([SLAVE_ID, 0x03, (start >> 8) & 0xFF, start & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
    frame = pdu + calc_crc16(pdu)
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    time.sleep(0.06)
    rx = ser.read(256)
    if rx and len(rx) >= 5 and rx[-2:] == calc_crc16(rx[:-2]) and rx[1] == 0x03:
        return rx[3:-2]
    return None


def main():
    ser = serial.Serial(PORT, 9600, parity=serial.PARITY_NONE, timeout=0.5)
    time.sleep(0.05)
    
    # Check 0x0080 to 0x00FF
    print("Checking 0x0080 - 0x00FF...")
    for addr in range(0x0080, 0x0100, 8):
        data = read_block(ser, addr, 8)
        if data:
            print(f"  Valid 0x{addr:04X}: {data.hex(' ')} | ASCII: {''.join(chr(c) if 32<=c<=126 else '.' for c in data)}")
        time.sleep(0.03)

    # Check 0x0100 to 0x0200
    print("Checking 0x0100 - 0x0150...")
    for addr in range(0x0100, 0x0150, 8):
        data = read_block(ser, addr, 8)
        if data:
            print(f"  Valid 0x{addr:04X}: {data.hex(' ')} | ASCII: {''.join(chr(c) if 32<=c<=126 else '.' for c in data)}")
        time.sleep(0.03)

    # Check 0x0300
    print("Checking 0x0300 - 0x0330...")
    for addr in range(0x0300, 0x0330, 8):
        data = read_block(ser, addr, 8)
        if data:
            print(f"  Valid 0x{addr:04X}: {data.hex(' ')} | ASCII: {''.join(chr(c) if 32<=c<=126 else '.' for c in data)}")
        time.sleep(0.03)

    # Check 0x1010 - 0x1030
    print("Checking 0x1010 - 0x1040...")
    for addr in range(0x1010, 0x1040, 8):
        data = read_block(ser, addr, 8)
        if data:
            print(f"  Valid 0x{addr:04X}: {data.hex(' ')} | ASCII: {''.join(chr(c) if 32<=c<=126 else '.' for c in data)}")
        time.sleep(0.03)

    ser.close()


if __name__ == "__main__":
    main()
