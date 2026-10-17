#!/usr/bin/env python3
"""Scan for additional registers (alarms, status, identification) on Huawei EMS-4805A1."""

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


def read_reg_single(ser, addr, count=1, fc=0x03):
    pdu = bytes([SLAVE_ID, fc, (addr >> 8) & 0xFF, addr & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
    frame = pdu + calc_crc16(pdu)
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    time.sleep(0.06)
    rx = ser.read(128)
    if rx and len(rx) >= 5 and rx[-2:] == calc_crc16(rx[:-2]) and rx[1] == fc:
        return rx[3:-2]
    return None


def main():
    ser = serial.Serial(PORT, 9600, parity=serial.PARITY_NONE, timeout=0.5)
    time.sleep(0.1)

    print("Checking registers between 0x0008 and 0x0017 individually:")
    for a in range(0x0008, 0x0018):
        d = read_reg_single(ser, a, 1)
        if d:
            val = int.from_bytes(d, "big")
            print(f"  Reg 0x{a:04X} ({a}): 0x{val:04X} ({val})")
        time.sleep(0.03)

    print("\nScanning for possible ID / info registers at other offsets:")
    for base in [0x0040, 0x0050, 0x0060, 0x0070, 0x0080, 0x0090, 0x00A0, 0x00B0, 0x00C0, 0x00D0, 0x00E0, 0x00F0, 0x0100, 0x0200, 0x0300, 0x1000, 0x2000, 0x3000, 0x4000, 0x5000]:
        d = read_reg_single(ser, base, 1)
        if d:
            val = int.from_bytes(d, "big")
            print(f"  >> Found valid register at 0x{base:04X}: 0x{val:04X} ({val})")
        time.sleep(0.02)

    # Also test FC 0x04 (Read Input Registers)
    print("\nTesting FC 0x04 (Input Registers) at 0x0000:")
    d = read_reg_single(ser, 0x0000, 4, fc=0x04)
    if d:
        print(f"  FC04 0x0000 responded: {d.hex(' ').upper()}")
    else:
        print("  FC04 0x0000: No response or Exception")

    ser.close()


if __name__ == "__main__":
    main()
