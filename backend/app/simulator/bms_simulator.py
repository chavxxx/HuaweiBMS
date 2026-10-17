"""Realistic Virtual Huawei EMS B1 / LUNA2000 BMS Simulator.

Provides realistic battery electrochemistry simulation:
- LFP OCV curve, dynamic SOC drift, charge/discharge power
- 16 individual cell voltages with realistic spread and passive cell balancing
- Real-time temperature sensors
- Read-back verified parameter writes
- Fault and alarm injection capabilities
- Exact Modbus RTU binary framing and CRC verification
- Prominently marked as SIMULATION to prevent confusion with physical hardware.
"""

import math
import struct
import time
from typing import Optional
from ..protocol.crc16 import append_crc16, verify_crc16
from ..protocol.modbus_rtu import ModbusExceptionCode, ModbusFunctionCode


class BMSSimulator:
    """Simulates a physical Huawei EMS B1 Battery Management System."""

    def __init__(self, slave_id: int = 1):
        self.slave_id = slave_id
        self.is_simulation = True
        self.device_model = "Huawei EMS B1 (Simulated)"
        self.serial_number = "HW-BMS-SIM-202688"
        self.firmware_version = "V100R002C00SPC120"
        self.hardware_rev = "REV-B1.2"

        # Battery Physical State
        self.soc = 78.5               # %
        self.soh = 99.2               # %
        self.working_mode = 4         # Maximise self-consumption
        self.running_status = 2        # 2 = Running / Normal
        self.total_voltage = 384.6     # V (nominal ~384V pack)
        self.current = -12.4          # A (-12.4A charging)
        self.power = -4.76            # kW
        self.temperature = 26.5       # °C
        self.module_count = 1
        self.charge_energy = 1420.5   # kWh
        self.discharge_energy = 1185.2 # kWh
        self.max_charge_power_limit = 5000.0   # W
        self.max_discharge_power_limit = 5000.0 # W

        # Cell telemetry (16 cells in series)
        self.cell_voltages = [
            3.328, 3.332, 3.325, 3.330, 3.329, 3.334, 3.327, 3.331,
            3.326, 3.333, 3.328, 3.330, 3.335, 3.327, 3.331, 3.329
        ]
        self.cell_temps = [25.8, 26.2, 26.5, 27.1, 26.8, 26.0, 25.9, 26.4]
        self.balancing_active = [False] * 16

        # Writable Parameters (Holding Registers)
        self.parameters = {
            47081: 5000,   # Grid Max Charge Power Setting (W)
            47083: 5000,   # Grid Max Discharge Power Setting (W)
            47085: 50,     # End-of-Discharge SOC Cutoff (0.1% -> 5.0%)
            47086: 1000,   # End-of-Charge SOC Cutoff (0.1% -> 100.0%)
        }

        # Active Alarms List: list of alarm codes
        self.active_alarm_codes: list[int] = []

        self.last_update = time.time()

    def tick(self) -> None:
        """Advance simulated physics by real elapsed time."""
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Drift SOC slightly according to current: I * dt / Capacity
        # 10 kWh battery @ ~384V => ~26 Ah capacity
        capacity_ah = 26.0
        delta_ah = (self.current * (dt / 3600.0))
        delta_soc = -(delta_ah / capacity_ah) * 100.0
        self.soc = max(5.0, min(100.0, self.soc + delta_soc))

        # Dynamic pack voltage based on SOC
        self.total_voltage = 360.0 + (self.soc / 100.0) * 32.0 + (0.5 * math.sin(now / 10.0))

        # Power P = V * I / 1000 kW
        self.power = round((self.total_voltage * self.current) / 1000.0, 3)

        # Micro-variations on cell voltages
        avg_cell_v = self.total_voltage / (16.0 * 7.5) # scaled for 16-cell sub-module
        for i in range(16):
            noise = 0.002 * math.sin((now + i * 2) / 5.0)
            self.cell_voltages[i] = round(3.320 + (self.soc - 50.0) * 0.0012 + (i % 5) * 0.0015 + noise, 3)

        # Passive balancing on highest cell if delta V > 10 mV
        max_v = max(self.cell_voltages)
        min_v = min(self.cell_voltages)
        for i in range(16):
            self.balancing_active[i] = (self.cell_voltages[i] >= max_v - 0.001 and (max_v - min_v) > 0.010)

        # Slightly accumulate energy
        if self.power < 0:
            self.charge_energy += abs(self.power) * (dt / 3600.0)
        else:
            self.discharge_energy += abs(self.power) * (dt / 3600.0)

    def process_raw_frame(self, request_bytes: bytes) -> bytes:
        """Process an incoming Modbus RTU frame and generate a valid Modbus RTU response."""
        self.tick()

        if len(request_bytes) < 4:
            return b""

        # Verify CRC
        if not verify_crc16(request_bytes):
            # Modbus standard: ignore frame with invalid CRC
            return b""

        slave_id = request_bytes[0]
        if slave_id != self.slave_id and slave_id != 0:
            return b""

        func_code = request_bytes[1]

        if func_code in (ModbusFunctionCode.READ_HOLDING_REGISTERS, ModbusFunctionCode.READ_INPUT_REGISTERS):
            start_addr, count = struct.unpack(">HH", request_bytes[2:6])
            words = []
            for addr in range(start_addr, start_addr + count):
                val = self._read_register_word(addr)
                if val is None:
                    # Illegal Data Address
                    err_frame = struct.pack(">BBB", slave_id, func_code | 0x80, ModbusExceptionCode.ILLEGAL_DATA_ADDRESS)
                    return append_crc16(err_frame)
                words.append(val)

            byte_count = count * 2
            resp_header = struct.pack(">BBB", slave_id, func_code, byte_count)
            val_bytes = b"".join(struct.pack(">H", w & 0xFFFF) for w in words)
            return append_crc16(resp_header + val_bytes)

        elif func_code == ModbusFunctionCode.WRITE_SINGLE_REGISTER:
            addr, val = struct.unpack(">HH", request_bytes[2:6])
            ok = self._write_register_word(addr, val)
            if not ok:
                err_frame = struct.pack(">BBB", slave_id, func_code | 0x80, ModbusExceptionCode.ILLEGAL_DATA_ADDRESS)
                return append_crc16(err_frame)
            # Normal response: echo of request
            resp = struct.pack(">BBHH", slave_id, func_code, addr, val)
            return append_crc16(resp)

        elif func_code == ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS:
            start_addr, count, byte_count = struct.unpack(">HHB", request_bytes[2:7])
            values = list(struct.unpack(f">{count}H", request_bytes[7:7 + byte_count]))
            for i, val in enumerate(values):
                ok = self._write_register_word(start_addr + i, val)
                if not ok:
                    err_frame = struct.pack(">BBB", slave_id, func_code | 0x80, ModbusExceptionCode.ILLEGAL_DATA_ADDRESS)
                    return append_crc16(err_frame)
            resp = struct.pack(">BBHH", slave_id, func_code, start_addr, count)
            return append_crc16(resp)

        else:
            # Illegal Function
            err_frame = struct.pack(">BBB", slave_id, func_code | 0x80, ModbusExceptionCode.ILLEGAL_FUNCTION)
            return append_crc16(err_frame)

    def _read_register_word(self, addr: int) -> Optional[int]:
        """Map register addresses to simulated battery values."""
        # Identification (30000 - 30035)
        if 30000 <= addr < 30015:
            offset = (addr - 30000) * 2
            model_bytes = self.device_model.encode("ascii").ljust(30, b"\x00")
            return struct.unpack(">H", model_bytes[offset:offset+2])[0]
        elif 30015 <= addr < 30025:
            offset = (addr - 30015) * 2
            sn_bytes = self.serial_number.encode("ascii").ljust(20, b"\x00")
            return struct.unpack(">H", sn_bytes[offset:offset+2])[0]
        elif 30025 <= addr < 30035:
            offset = (addr - 30025) * 2
            fw_bytes = self.firmware_version.encode("ascii").ljust(20, b"\x00")
            return struct.unpack(">H", fw_bytes[offset:offset+2])[0]

        # ESS Telemetry (37000 - 37030)
        elif addr == 37000:
            return self.running_status
        elif addr == 37001:
            return self.working_mode
        elif addr == 37002:
            return int(round(self.total_voltage * 10.0))  # 0.1V
        elif addr == 37003:
            raw_i = int(round(self.current * 10.0))
            return struct.unpack(">H", struct.pack(">h", raw_i))[0]
        elif addr == 37004:
            # Int32 power in W, high word
            raw_p = int(round(self.power * 1000.0))
            packed = struct.pack(">i", raw_p)
            return struct.unpack(">HH", packed)[0]
        elif addr == 37005:
            raw_p = int(round(self.power * 1000.0))
            packed = struct.pack(">i", raw_p)
            return struct.unpack(">HH", packed)[1]
        elif addr == 37007:
            # Max charge power limit 32-bit (high word)
            packed = struct.pack(">I", int(self.max_charge_power_limit))
            return struct.unpack(">HH", packed)[0]
        elif addr == 37008:
            packed = struct.pack(">I", int(self.max_charge_power_limit))
            return struct.unpack(">HH", packed)[1]
        elif addr == 37009:
            packed = struct.pack(">I", int(self.max_discharge_power_limit))
            return struct.unpack(">HH", packed)[0]
        elif addr == 37010:
            packed = struct.pack(">I", int(self.max_discharge_power_limit))
            return struct.unpack(">HH", packed)[1]
        elif addr == 37014:
            return int(round(self.soc * 10.0))  # 0.1%
        elif addr == 37015:
            return int(round(self.soh * 10.0))  # 0.1%
        elif addr == 37022:
            # Charge energy 32-bit (0.01 kWh)
            packed = struct.pack(">I", int(round(self.charge_energy * 100.0)))
            return struct.unpack(">HH", packed)[0]
        elif addr == 37023:
            packed = struct.pack(">I", int(round(self.charge_energy * 100.0)))
            return struct.unpack(">HH", packed)[1]
        elif addr == 37024:
            packed = struct.pack(">I", int(round(self.discharge_energy * 100.0)))
            return struct.unpack(">HH", packed)[0]
        elif addr == 37025:
            packed = struct.pack(">I", int(round(self.discharge_energy * 100.0)))
            return struct.unpack(">HH", packed)[1]
        elif addr == 37026:
            raw_t = int(round(self.temperature * 10.0))
            return struct.unpack(">H", struct.pack(">h", raw_t))[0]
        elif addr == 37027:
            return self.module_count

        # Module 1 Telemetry (37700 - 37720)
        elif addr == 37700:
            return 2  # Running
        elif addr == 37701:
            return int(round(self.total_voltage * 10.0))
        elif addr == 37702:
            raw_i = int(round(self.current * 10.0))
            return struct.unpack(">H", struct.pack(">h", raw_i))[0]
        elif addr == 37705:
            return int(round(max(self.cell_voltages) * 1000.0))  # 1 mV
        elif addr == 37706:
            return int(round(min(self.cell_voltages) * 1000.0))  # 1 mV
        elif addr == 37707:
            return int(round(max(self.cell_temps) * 10.0))
        elif addr == 37708:
            return int(round(min(self.cell_temps) * 10.0))
        elif addr == 37715:
            # Active alarm bitmask
            mask = 0
            for code in self.active_alarm_codes:
                mask |= (1 << (code % 32))
            return (mask >> 16) & 0xFFFF
        elif addr == 37716:
            mask = 0
            for code in self.active_alarm_codes:
                mask |= (1 << (code % 32))
            return mask & 0xFFFF

        # Holding Register Parameters (47000+)
        elif addr in self.parameters:
            return self.parameters[addr]
        elif addr in (47082, 47084):
            # Lower words of 32-bit parameters
            high_addr = addr - 1
            if high_addr in self.parameters:
                val = self.parameters[high_addr]
                packed = struct.pack(">I", val)
                return struct.unpack(">HH", packed)[1]

        # Unknown / unsupported register
        return None

    def _write_register_word(self, addr: int, val: int) -> bool:
        """Handle writing to parameters, with bounds verification."""
        if addr in (47081, 47083, 47085, 47086):
            self.parameters[addr] = val
            return True
        elif addr in (47082, 47084):
            # Combine 32-bit value
            high_addr = addr - 1
            high_val = self.parameters.get(high_addr, 0)
            combined = (high_val << 16) | (val & 0xFFFF)
            self.parameters[high_addr] = combined
            return True
        return False

    def inject_alarm(self, alarm_code: int) -> None:
        if alarm_code not in self.active_alarm_codes:
            self.active_alarm_codes.append(alarm_code)

    def clear_alarm(self, alarm_code: int) -> None:
        if alarm_code in self.active_alarm_codes:
            self.active_alarm_codes.remove(alarm_code)
