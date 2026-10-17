#!/usr/bin/env python3
"""Deep register probe for Huawei EMS-4805A1 at Slave 214, 9600 8N1."""

import time
import serial

PORT = "/dev/cu.usbserial-BG01GGUB"
SLAVE_ID = 214  # 0xD6


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


def read_registers(ser, start_reg: int, count: int, fc=0x03):
    pdu = bytes([
        SLAVE_ID,
        fc,
        (start_reg >> 8) & 0xFF,
        start_reg & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ])
    frame = pdu + calc_crc16(pdu)
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    time.sleep(0.08)
    resp = ser.read(256)
    return frame, resp


def main():
    ser = serial.Serial(
        port=PORT,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1.0,
    )
    time.sleep(0.1)

    print(f"=== Deep Scanning Huawei EMS-4805A1 Registers (Slave {SLAVE_ID}, 9600 8N1) ===")

    # Probe 0x0000 to 0x0030 in chunks of 8 registers
    for start in range(0, 0x0040, 8):
        tx, rx = read_registers(ser, start, 8, fc=0x03)
        if rx and len(rx) >= 5:
            rec_crc = rx[-2:]
            exp_crc = calc_crc16(rx[:-2])
            if rec_crc == exp_crc and rx[1] == 0x03:
                byte_cnt = rx[2]
                vals = [int.from_bytes(rx[3 + i*2 : 5 + i*2], "big") for i in range(byte_cnt // 2)]
                print(f"\n[Regs 0x{start:04X} - 0x{start+len(vals)-1:04X}]:")
                print(f"  TX: {tx.hex(' ').upper()}")
                print(f"  RX: {rx.hex(' ').upper()}")
                for idx, v in enumerate(vals):
                    reg_addr = start + idx
                    signed_v = int.from_bytes(rx[3 + idx*2 : 5 + idx*2], "big", signed=True)
                    print(f"    0x{reg_addr:04X} ({reg_addr:5d}): raw=0x{v:04X} | unsigned={v:6d} | signed={signed_v:6d}")
            else:
                print(f"Start 0x{start:04X}: Error response / CRC mismatch -> RX: {rx.hex(' ').upper()}")
        else:
            print(f"Start 0x{start:04X}: Timeout / No response")
        time.sleep(0.05)

    ser.close()


if __name__ == "__main__":
    main()
