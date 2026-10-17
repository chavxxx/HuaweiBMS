#!/usr/bin/env python3
"""Hardware probe script for Huawei EMS-4805A1 BMS over USB-to-RS485 adapter."""

import sys
import time
import serial

PORT = "/dev/cu.usbserial-BG01GGUB"


def calc_crc16(data: bytes) -> bytes:
    """Calculate Modbus RTU CRC-16 (low-byte first)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def build_modbus_read(slave_id: int, func_code: int, start_reg: int, count: int) -> bytes:
    """Construct standard Modbus RTU Read request frame."""
    pdu = bytes([
        slave_id,
        func_code,
        (start_reg >> 8) & 0xFF,
        start_reg & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ])
    crc = calc_crc16(pdu)
    return pdu + crc


def probe():
    print(f"=== Probing Hardware on {PORT} ===")
    
    # Priority matrix
    baudrates = [9600, 19200]
    parities = [serial.PARITY_EVEN, serial.PARITY_NONE]
    slave_ids = [214, 1, 2, 16, 3, 215, 0]
    registers_to_try = [
        (0x03, 0x0000, 4, "FC03 Holding Reg 0x0000 count 4"),
        (0x03, 0x0001, 4, "FC03 Holding Reg 0x0001 count 4"),
        (0x04, 0x0000, 4, "FC04 Input Reg 0x0000 count 4"),
    ]

    for baud in baudrates:
        for parity in parities:
            parity_str = "E" if parity == serial.PARITY_EVEN else "N"
            print(f"\n--- Testing Baud: {baud}, Parity: 8{parity_str}1 ---")
            
            try:
                ser = serial.Serial(
                    port=PORT,
                    baudrate=baud,
                    bytesize=serial.EIGHTBITS,
                    parity=parity,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.6,
                    write_timeout=0.5
                )
            except Exception as e:
                print(f"Could not open port {PORT}: {e}")
                return

            try:
                # Flush existing buffer
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                time.sleep(0.05)

                for slave_id in slave_ids:
                    for fc, reg, count, desc in registers_to_try:
                        frame = build_modbus_read(slave_id, fc, reg, count)
                        hex_req = frame.hex(" ").upper()
                        
                        ser.reset_input_buffer()
                        ser.write(frame)
                        ser.flush()
                        
                        time.sleep(0.08) # Wait for turnaround
                        
                        resp = ser.read(128)
                        if resp:
                            hex_resp = resp.hex(" ").upper()
                            print(f"\n[SUCCESS/DATA RECEIVED!] -> Slave {slave_id} (0x{slave_id:02X}) | {desc}")
                            print(f"  TX: {hex_req}")
                            print(f"  RX ({len(resp)} bytes): {hex_resp}")
                            
                            # Validate CRC
                            if len(resp) >= 5:
                                pdu = resp[:-2]
                                exp_crc = calc_crc16(pdu)
                                rec_crc = resp[-2:]
                                if exp_crc == rec_crc:
                                    print("  >> CRC-16 VALID! Verified frame received!")
                                    # Decode response
                                    if resp[1] == fc and len(resp) >= 3 + resp[2]:
                                        byte_count = resp[2]
                                        data_bytes = resp[3:3+byte_count]
                                        print(f"  >> Byte count: {byte_count}")
                                        words = [int.from_bytes(data_bytes[i:i+2], byteorder="big", signed=False) 
                                                 for i in range(0, len(data_bytes), 2)]
                                        print(f"  >> Registers (raw 16-bit): {[hex(w) for w in words]} / {words}")
                                        if reg == 0x0000 and len(words) >= 4:
                                            v_raw = words[0]
                                            c_raw = int.from_bytes(data_bytes[2:4], byteorder="big", signed=True)
                                            soc_raw = words[2]
                                            soh_raw = words[3]
                                            print(f"  >> Decoded Telemetry: Voltage = {v_raw*0.01:.2f}V, Current = {c_raw*0.01:.2f}A, SOC = {soc_raw*0.1:.1f}%, SOH = {soh_raw*0.1:.1f}%")
                                    return
                                else:
                                    print(f"  >> CRC-16 MISMATCH! Expected {exp_crc.hex()}, got {rec_crc.hex()}")
                        else:
                            # Print a dot for timeout
                            sys.stdout.write(".")
                            sys.stdout.flush()
            finally:
                ser.close()
                time.sleep(0.05)

    print("\n\nNo response received across matrix.")


if __name__ == "__main__":
    probe()
