"""Multi-Battery Fleet Management, Bus Scanning, and Comparative Diagnostics Service."""

import csv
import io
import json
import logging
import time
from typing import Any, Optional

from ..database.crud import AuditCRUD, MultiBatteryAuditCRUD
from ..protocol.register_map import RegisterDatabase
from ..serial_comm.serial_client import SerialClient
from ..simulator.bms_simulator import BMSSimulator

logger = logging.getLogger("huawei_bms.multi_battery")


class MultiBatteryService:
    """Manages multi-battery addressing, parallel string monitoring, and fleet audits."""

    def __init__(
        self,
        serial_client: SerialClient,
        register_db: RegisterDatabase,
        telemetry_service: Any,
    ):
        self.serial_client = serial_client
        self.register_db = register_db
        self.telemetry_service = telemetry_service

        # Active battery address currently monitored across all application views
        self.active_slave_id = 1

        # Multi-battery simulator registry for realistic virtual bank testing
        self._simulators: dict[int, BMSSimulator] = {}
        self._init_default_simulators()

        # Configured battery address book for physical bus monitoring
        # (Default to [1, 2, 3, 4] and [214] for Huawei ESM/EMS presets)
        self.configured_batteries: list[dict[str, Any]] = [
            {
                "slave_id": 1,
                "name": "Battery #1 (Bank Main)",
                "custom_name": "Battery #1 (Bank Main)",
                "online": True,
                "last_seen": time.time(),
            },
            {
                "slave_id": 2,
                "name": "Battery #2 (String A)",
                "custom_name": "Battery #2 (String A)",
                "online": True,
                "last_seen": time.time(),
            },
            {
                "slave_id": 3,
                "name": "Battery #3 (String B)",
                "custom_name": "Battery #3 (String B)",
                "online": True,
                "last_seen": time.time(),
            },
            {
                "slave_id": 4,
                "name": "Battery #4 (String C)",
                "custom_name": "Battery #4 (String C)",
                "online": True,
                "last_seen": time.time(),
            },
        ]

        self.last_audit_data: Optional[dict[str, Any]] = None

    def _init_default_simulators(self) -> None:
        """Create a realistic 4-pack parallel Huawei ESM-48150B1 battery bank."""
        # Battery 1 - Healthy baseline pack
        b1 = BMSSimulator(slave_id=1)
        b1.device_model = "Huawei ESM-48150B1"
        b1.serial_number = "UB2230030194"
        b1.soc = 78.5
        b1.soh = 99.2
        b1.total_voltage = 53.25
        b1.current = -12.4
        b1.power = round((53.25 * -12.4) / 1000.0, 3)
        b1.temperature = 26.5
        b1.cell_voltages = [
            3.328, 3.332, 3.325, 3.330, 3.329, 3.334, 3.327, 3.331,
            3.326, 3.333, 3.328, 3.330, 3.335, 3.327, 3.331, 3.329
        ]
        b1.cell_temps = [26.0 + (i % 3) * 0.3 for i in range(16)]
        self._simulators[1] = b1

        # Battery 2 - Slightly higher SOC, very healthy
        b2 = BMSSimulator(slave_id=2)
        b2.device_model = "Huawei ESM-48150B1"
        b2.serial_number = "UB2230030195"
        b2.soc = 81.0
        b2.soh = 97.8
        b2.total_voltage = 53.40
        b2.current = -11.8
        b2.power = round((53.40 * -11.8) / 1000.0, 3)
        b2.temperature = 27.2
        b2.cell_voltages = [
            3.332, 3.338, 3.335, 3.340, 3.337, 3.342, 3.336, 3.339,
            3.334, 3.341, 3.336, 3.339, 3.340, 3.335, 3.338, 3.337
        ]
        b2.cell_temps = [26.8 + (i % 4) * 0.25 for i in range(16)]
        self._simulators[2] = b2

        # Battery 3 - Moderate cycling, higher cell delta (outlier for diagnostics)
        b3 = BMSSimulator(slave_id=3)
        b3.device_model = "Huawei ESM-48150B1"
        b3.serial_number = "UB2230030196"
        b3.soc = 72.4
        b3.soh = 94.1
        b3.total_voltage = 52.80
        b3.current = -14.2
        b3.power = round((52.80 * -14.2) / 1000.0, 3)
        b3.temperature = 29.8
        # Cell #3 is noticeably lower (3.285V), creating a 47mV delta
        b3.cell_voltages = [
            3.320, 3.325, 3.285, 3.330, 3.324, 3.332, 3.321, 3.328,
            3.319, 3.326, 3.322, 3.325, 3.327, 3.321, 3.325, 3.323
        ]
        b3.cell_temps = [28.5 + (i % 4) * 0.4 for i in range(16)]
        b3.active_alarm_codes = [4]  # Cell Imbalance Warning
        self._simulators[3] = b3

        # Battery 4 - Healthy pack
        b4 = BMSSimulator(slave_id=4)
        b4.device_model = "Huawei ESM-48150B1"
        b4.serial_number = "UB2230030197"
        b4.soc = 79.2
        b4.soh = 98.5
        b4.total_voltage = 53.30
        b4.current = -12.0
        b4.power = round((53.30 * -12.0) / 1000.0, 3)
        b4.temperature = 26.8
        b4.cell_voltages = [
            3.325, 3.331, 3.327, 3.333, 3.329, 3.335, 3.328, 3.332,
            3.326, 3.334, 3.329, 3.331, 3.333, 3.327, 3.330, 3.329
        ]
        b4.cell_temps = [26.2 + (i % 3) * 0.3 for i in range(16)]
        self._simulators[4] = b4

        # Also support 214 (0xD6) as simulated fallback
        b214 = BMSSimulator(slave_id=214)
        b214.device_model = "Huawei ESM-48150B1"
        b214.serial_number = "UB2230030194"
        b214.soc = 78.5
        b214.soh = 99.2
        b214.total_voltage = 53.25
        b214.current = -12.4
        b214.power = -0.660
        self._simulators[214] = b214

    def get_simulator_for_slave(self, slave_id: int) -> BMSSimulator:
        """Retrieve or create a simulator instance for a given slave ID."""
        if slave_id not in self._simulators:
            sim = BMSSimulator(slave_id=slave_id)
            sim.device_model = "Huawei ESM-48150B1"
            sim.serial_number = f"UB22300{slave_id:04d}"
            sim.soc = 80.0
            sim.soh = 98.0
            sim.total_voltage = 53.3
            self._simulators[slave_id] = sim
        return self._simulators[slave_id]

    def list_batteries(self) -> list[dict[str, Any]]:
        """Return summary of all configured/discovered batteries."""
        is_sim = self.telemetry_service.use_simulation
        results = []

        for b in self.configured_batteries:
            slave_id = b["slave_id"]
            name = b.get("custom_name") or b.get("name") or f"Battery #{slave_id}"
            is_active = (slave_id == self.active_slave_id)

            if is_sim:
                sim = self.get_simulator_for_slave(slave_id)
                cells = list(sim.cell_voltages)
                min_v = min(cells)
                max_v = max(cells)
                delta_v_mv = round((max_v - min_v) * 1000.0, 1)

                results.append({
                    "slave_id": slave_id,
                    "name": name,
                    "model": sim.device_model,
                    "serial_number": sim.serial_number,
                    "is_active": is_active,
                    "online": True,
                    "soc": round(sim.soc, 1),
                    "soh": round(sim.soh, 1),
                    "total_voltage": round(sim.total_voltage, 2),
                    "current": round(sim.current, 2),
                    "power": round(sim.power, 3),
                    "temperature": round(sim.temperature, 1),
                    "cell_voltage_delta_mv": delta_v_mv,
                    "cycle_count": 400 + slave_id * 180,
                    "rated_capacity_ah": 100,
                    "alarm_count": len(sim.active_alarm_codes),
                    "active_alarms": list(sim.active_alarm_codes),
                    "operating_state": "Fault" if sim.active_alarm_codes else ("Charging" if sim.power < -0.05 else ("Discharging" if sim.power > 0.05 else "Standby")),
                })
            else:
                # Hardware mode: if it's the active battery, use latest live telemetry
                if is_active and self.telemetry_service.latest_telemetry:
                    t = self.telemetry_service.latest_telemetry
                    c = self.telemetry_service.latest_cells
                    results.append({
                        "slave_id": slave_id,
                        "name": name,
                        "model": t.get("device_model", "Huawei ESM-48150B1"),
                        "serial_number": t.get("serial_number", f"HW-ESM-{slave_id:02X}"),
                        "is_active": True,
                        "online": self.serial_client.is_connected,
                        "soc": t.get("soc", 0.0),
                        "soh": t.get("soh", 100.0),
                        "total_voltage": t.get("total_voltage", 0.0),
                        "current": t.get("current", 0.0),
                        "power": t.get("power", 0.0),
                        "temperature": t.get("temperature", 25.0),
                        "cell_voltage_delta_mv": c.get("cell_voltage_delta_mv", 0.0),
                        "cycle_count": t.get("cycle_count", 0),
                        "rated_capacity_ah": t.get("rated_capacity_ah", 100),
                        "alarm_count": len(t.get("active_alarm_codes", [])),
                        "active_alarms": t.get("active_alarm_codes", []),
                        "operating_state": t.get("operating_state", "Standby"),
                    })
                else:
                    results.append({
                        "slave_id": slave_id,
                        "name": name,
                        "model": b.get("model", "Huawei ESM-48150B1"),
                        "serial_number": b.get("serial_number", f"HW-ESM-{slave_id:02X}"),
                        "is_active": is_active,
                        "online": b.get("online", True),
                        "soc": b.get("soc", 75.0),
                        "soh": b.get("soh", 98.0),
                        "total_voltage": b.get("total_voltage", 53.2),
                        "current": b.get("current", 0.0),
                        "power": b.get("power", 0.0),
                        "temperature": b.get("temperature", 25.0),
                        "cell_voltage_delta_mv": b.get("cell_voltage_delta_mv", 12.0),
                        "cycle_count": b.get("cycle_count", 500),
                        "rated_capacity_ah": 100,
                        "alarm_count": 0,
                        "active_alarms": [],
                        "operating_state": "Standby",
                    })

        return results

    def set_active_battery(self, slave_id: int) -> dict[str, Any]:
        """Switch the globally active monitored battery across all views."""
        self.active_slave_id = slave_id
        is_sim = self.telemetry_service.use_simulation

        if is_sim:
            sim = self.get_simulator_for_slave(slave_id)
            self.telemetry_service.simulator = sim
            # Trigger an immediate tick and update
            self.telemetry_service._poll_simulated_bms()
        else:
            # Physical hardware mode: update serial client slave ID
            self.serial_client.config.slave_id = slave_id
            self.telemetry_service.reset_telemetry_for_hardware()

        logger.info("Active battery switched to Slave ID %d (simulated=%s)", slave_id, is_sim)
        return {
            "success": True,
            "active_slave_id": slave_id,
            "message": f"Active battery switched to Slave ID {slave_id}."
        }

    def add_battery(self, slave_id: int, name: Optional[str] = None) -> dict[str, Any]:
        """Add a battery address to the monitoring fleet."""
        for b in self.configured_batteries:
            if b["slave_id"] == slave_id:
                if name:
                    b["custom_name"] = name
                return {"success": True, "message": f"Battery {slave_id} already exists (name updated)."}

        new_entry = {
            "slave_id": slave_id,
            "name": name or f"Battery #{slave_id} (0x{slave_id:02X})",
            "custom_name": name or f"Battery #{slave_id} (0x{slave_id:02X})",
            "online": True,
            "last_seen": time.time(),
        }
        self.configured_batteries.append(new_entry)
        # Sort by slave_id
        self.configured_batteries.sort(key=lambda x: x["slave_id"])
        return {"success": True, "message": f"Added Battery {slave_id} to monitoring list."}

    def remove_battery(self, slave_id: int) -> dict[str, Any]:
        """Remove a battery address from the fleet."""
        if len(self.configured_batteries) <= 1:
            raise ValueError("Cannot remove the only configured battery.")

        self.configured_batteries = [b for b in self.configured_batteries if b["slave_id"] != slave_id]
        if self.active_slave_id == slave_id and self.configured_batteries:
            self.set_active_battery(self.configured_batteries[0]["slave_id"])

        return {"success": True, "message": f"Battery {slave_id} removed from monitoring list."}

    def scan_bus(self, candidate_ids: Optional[list[int]] = None) -> dict[str, Any]:
        """Scan RS485 bus for responding Modbus slave IDs."""
        is_sim = self.telemetry_service.use_simulation
        candidates = candidate_ids or [1, 2, 3, 4, 5, 6, 7, 8, 214, 215, 216, 217]

        discovered: list[dict[str, Any]] = []

        if is_sim:
            # In simulation, respond with configured simulated batteries
            for sid in candidates:
                if sid in self._simulators or sid in [1, 2, 3, 4, 214]:
                    sim = self.get_simulator_for_slave(sid)
                    discovered.append({
                        "slave_id": sid,
                        "model": sim.device_model,
                        "serial_number": sim.serial_number,
                        "status": "Online",
                        "latency_ms": 1.2
                    })
        else:
            if not self.serial_client.is_connected:
                raise ConnectionError("Cannot scan bus: Serial port is not connected.")

            adapter = self.serial_client.adapter
            orig_timeout = self.serial_client.config.timeout
            # Use faster timeout for scanning
            self.serial_client.config.timeout = 0.35

            try:
                for sid in candidates:
                    # Test read: Reg 0x0000 (total voltage), 1 word
                    req = adapter.build_read_holding_registers(sid, 0x0000, 1)
                    t0 = time.perf_counter()
                    resp = self.serial_client.execute_transaction(req, 0x03)
                    latency = round((time.perf_counter() - t0) * 1000.0, 1)

                    if resp.success:
                        # Attempt to read model
                        model_name = "Huawei ESM Battery"
                        m_req = adapter.build_read_holding_registers(sid, 818, 6)
                        m_resp = self.serial_client.execute_transaction(m_req, 0x03)
                        if m_resp.success and len(m_resp.values) == 6:
                            from .telemetry_service import decode_ascii_registers
                            raw_m = decode_ascii_registers(m_resp.values)
                            if raw_m:
                                model_name = f"Huawei {raw_m}"

                        discovered.append({
                            "slave_id": sid,
                            "model": model_name,
                            "serial_number": f"HW-ESM-{sid:02X}",
                            "status": "Online",
                            "latency_ms": latency
                        })
                        # Add to configured batteries if not already present
                        self.add_battery(sid, f"Battery #{sid} ({model_name})")
            finally:
                self.serial_client.config.timeout = orig_timeout

        return {
            "success": True,
            "scanned_count": len(candidates),
            "discovered_count": len(discovered),
            "discovered": discovered
        }

    def read_all_batteries(self) -> dict[str, Any]:
        """Perform a full, comprehensive readout of every battery in the fleet."""
        now = time.time()
        is_sim = self.telemetry_service.use_simulation
        battery_data: list[dict[str, Any]] = []

        # If in simulation mode, update all simulated modules to realistic current moment
        if is_sim:
            for sid, sim in self._simulators.items():
                sim.tick()

        for b in self.configured_batteries:
            sid = b["slave_id"]
            name = b.get("custom_name") or b.get("name") or f"Battery #{sid}"

            if is_sim:
                sim = self.get_simulator_for_slave(sid)
                cells = list(sim.cell_voltages)
                min_v = min(cells)
                max_v = max(cells)
                avg_v = round(sum(cells) / len(cells), 3)
                delta_v_mv = round((max_v - min_v) * 1000.0, 1)

                temps = list(sim.cell_temps)
                min_t = min(temps)
                max_t = max(temps)

                # Gyroscope lock state: 1 = Locked, 0 = Unlocked
                gyro_lock = sim.parameters.get(4376, 0)
                charge_limit_coef = sim.parameters.get(4109, 500)
                discharge_limit_coef = sim.parameters.get(4107, 1000)

                battery_data.append({
                    "slave_id": sid,
                    "name": name,
                    "model": sim.device_model,
                    "serial_number": sim.serial_number,
                    "mfg_date": "2022-03-14",
                    "firmware_version": sim.firmware_version,
                    "hardware_rev": sim.hardware_rev,
                    "online": True,
                    "soc": round(sim.soc, 1),
                    "soh": round(sim.soh, 1),
                    "total_voltage": round(sim.total_voltage, 2),
                    "current": round(sim.current, 2),
                    "power": round(sim.power, 3),
                    "dc_bus_voltage": round(sim.total_voltage + 0.3, 2),
                    "temperature": round(sim.temperature, 1),
                    "cycle_count": 400 + sid * 180,
                    "rated_capacity_ah": 100,
                    "remaining_capacity_ah": round(100.0 * (sim.soc / 100.0), 1),
                    "max_current_limit_a": 150,
                    "charge_energy_kwh": round(sim.charge_energy, 1),
                    "discharge_energy_kwh": round(sim.discharge_energy, 1),
                    # Cell details
                    "cell_count": len(cells),
                    "cell_voltages": cells,
                    "min_cell_voltage": min_v,
                    "max_cell_voltage": max_v,
                    "avg_cell_voltage": avg_v,
                    "min_cell_index": cells.index(min_v) + 1,
                    "max_cell_index": cells.index(max_v) + 1,
                    "cell_voltage_delta_mv": delta_v_mv,
                    # Temperatures
                    "cell_temps": temps,
                    "min_cell_temp": min_t,
                    "max_cell_temp": max_t,
                    "temp_spread": round(max_t - min_t, 1),
                    # Status & Alarms
                    "operating_state": "Fault" if sim.active_alarm_codes else ("Charging" if sim.power < -0.05 else ("Discharging" if sim.power > 0.05 else "Standby")),
                    "active_alarms": list(sim.active_alarm_codes),
                    "alarm_count": len(sim.active_alarm_codes),
                    # Capabilities & Settings
                    "parameters": {
                        "gyroscope_anti_theft_locked": (gyro_lock == 1),
                        "gyroscope_sensitivity": sim.parameters.get(4377, 1),
                        "charge_limit_c": round(charge_limit_coef / 1000.0, 3),
                        "charge_limit_a": round((charge_limit_coef / 1000.0) * 100.0, 1),
                        "discharge_limit_c": round(discharge_limit_coef / 1000.0, 3),
                        "discharge_limit_a": round((discharge_limit_coef / 1000.0) * 100.0, 1),
                        "float_voltage_v": 54.0,
                        "boost_voltage_v": 56.4,
                        "cutoff_voltage_v": 44.0,
                    }
                })
            else:
                # Hardware physical bus readout
                if not self.serial_client.is_connected:
                    # Offline record
                    battery_data.append({
                        "slave_id": sid,
                        "name": name,
                        "model": "Huawei ESM-48150B1",
                        "serial_number": f"HW-ESM-{sid:02X}",
                        "online": False,
                        "soc": 0.0,
                        "soh": 0.0,
                        "total_voltage": 0.0,
                        "current": 0.0,
                        "power": 0.0,
                        "temperature": 0.0,
                        "cell_voltage_delta_mv": 0.0,
                        "active_alarms": [],
                        "alarm_count": 0,
                    })
                    continue

                # Query physical registers for this slave ID
                adapter = self.serial_client.adapter
                try:
                    # 1. Base telemetry
                    req_base = adapter.build_read_holding_registers(sid, 0x0000, 8)
                    resp_base = self.serial_client.execute_transaction(req_base, 0x03)

                    v_pack = 53.2
                    current = 0.0
                    soc = 75.0
                    soh = 100.0
                    temp = 25.0

                    if resp_base.success and len(resp_base.values) >= 7:
                        w = resp_base.values
                        v_pack = round(w[1] * 0.01, 2)
                        raw_i = w[2]
                        signed_i = raw_i if raw_i < 32768 else raw_i - 65536
                        current = round(signed_i * 0.01, 2)
                        soc = round(float(w[3]), 1)
                        soh = round(float(w[4]), 1)
                        temp = float(w[6] if w[6] < 32768 else w[6] - 65536)

                    # 2. Cells (16 cell voltages at 34..49)
                    req_cells = adapter.build_read_holding_registers(sid, 34, 16)
                    resp_cells = self.serial_client.execute_transaction(req_cells, 0x03)
                    cells = []
                    if resp_cells.success and len(resp_cells.values) == 16:
                        cells = [round(mv / 1000.0, 3) for mv in resp_cells.values]
                    else:
                        cells = [round(v_pack / 16.0, 3)] * 16

                    min_v = min(cells)
                    max_v = max(cells)
                    avg_v = round(sum(cells) / len(cells), 3)
                    delta_v_mv = round((max_v - min_v) * 1000.0, 1)

                    # 3. Model & Serial
                    model_name = "Huawei ESM-48150B1"
                    req_m = adapter.build_read_holding_registers(sid, 818, 6)
                    resp_m = self.serial_client.execute_transaction(req_m, 0x03)
                    if resp_m.success and len(resp_m.values) == 6:
                        from .telemetry_service import decode_ascii_registers
                        raw_m = decode_ascii_registers(resp_m.values)
                        if raw_m:
                            model_name = f"Huawei {raw_m}"

                    sn = f"HW-ESM-{sid:02X}"
                    req_sn = adapter.build_read_holding_registers(sid, 529, 6)
                    resp_sn = self.serial_client.execute_transaction(req_sn, 0x03)
                    if resp_sn.success and len(resp_sn.values) == 6:
                        from .telemetry_service import decode_ascii_registers
                        raw_sn = decode_ascii_registers(resp_sn.values)
                        if raw_sn:
                            sn = raw_sn

                    # 4. Cycle count
                    cycles = 0
                    req_cyc = adapter.build_read_holding_registers(sid, 69, 1)
                    resp_cyc = self.serial_client.execute_transaction(req_cyc, 0x03)
                    if resp_cyc.success and len(resp_cyc.values) >= 1:
                        cycles = resp_cyc.values[0]

                    # 5. Parameters (Anti-theft lock at 4376)
                    req_lock = adapter.build_read_holding_registers(sid, 4376, 2)
                    resp_lock = self.serial_client.execute_transaction(req_lock, 0x03)
                    is_locked = False
                    if resp_lock.success and len(resp_lock.values) >= 1:
                        is_locked = (resp_lock.values[0] == 1)

                    power = round((v_pack * current) / 1000.0, 3)

                    battery_data.append({
                        "slave_id": sid,
                        "name": name,
                        "model": model_name,
                        "serial_number": sn,
                        "mfg_date": "2022-03-14",
                        "firmware_version": "V100R002",
                        "hardware_rev": "REV-B1",
                        "online": True,
                        "soc": soc,
                        "soh": soh,
                        "total_voltage": v_pack,
                        "current": current,
                        "power": power,
                        "dc_bus_voltage": v_pack,
                        "temperature": temp,
                        "cycle_count": cycles,
                        "rated_capacity_ah": 100,
                        "remaining_capacity_ah": round(100.0 * (soc / 100.0), 1),
                        "max_current_limit_a": 150,
                        "charge_energy_kwh": 0.0,
                        "discharge_energy_kwh": 0.0,
                        "cell_count": len(cells),
                        "cell_voltages": cells,
                        "min_cell_voltage": min_v,
                        "max_cell_voltage": max_v,
                        "avg_cell_voltage": avg_v,
                        "min_cell_index": cells.index(min_v) + 1,
                        "max_cell_index": cells.index(max_v) + 1,
                        "cell_voltage_delta_mv": delta_v_mv,
                        "cell_temps": [temp] * 16,
                        "min_cell_temp": temp,
                        "max_cell_temp": temp,
                        "temp_spread": 0.0,
                        "operating_state": "Charging" if current > 0.05 else ("Discharging" if current < -0.05 else "Standby"),
                        "active_alarms": [],
                        "alarm_count": 0,
                        "parameters": {
                            "gyroscope_anti_theft_locked": is_locked,
                            "gyroscope_sensitivity": 1,
                            "charge_limit_c": 0.5,
                            "charge_limit_a": 50.0,
                            "discharge_limit_c": 1.0,
                            "discharge_limit_a": 100.0,
                            "float_voltage_v": 54.0,
                            "boost_voltage_v": 56.4,
                            "cutoff_voltage_v": 44.0,
                        }
                    })
                except Exception as e:
                    logger.warning("Error reading battery %d: %s", sid, e)

        # Restore active battery address
        if not is_sim:
            self.serial_client.config.slave_id = self.active_slave_id

        # Compute Fleet Summary Metrics
        online_batts = [b for b in battery_data if b.get("online", False)]
        total_cap_ah = sum(b.get("rated_capacity_ah", 100) for b in online_batts)
        total_remaining_ah = sum(b.get("remaining_capacity_ah", 0) for b in online_batts)
        total_current = round(sum(b.get("current", 0) for b in online_batts), 2)
        total_power = round(sum(b.get("power", 0) for b in online_batts), 3)

        socs = [b.get("soc", 0) for b in online_batts if b.get("soc") is not None]
        sohs = [b.get("soh", 0) for b in online_batts if b.get("soh") is not None]
        deltas = [b.get("cell_voltage_delta_mv", 0) for b in online_batts]
        voltages = [b.get("total_voltage", 0) for b in online_batts]
        temps = [b.get("temperature", 0) for b in online_batts]

        avg_soc = round(sum(socs) / len(socs), 1) if socs else 0.0
        min_soc = min(socs) if socs else 0.0
        max_soc = max(socs) if socs else 0.0
        soc_divergence = round(max_soc - min_soc, 1)

        avg_soh = round(sum(sohs) / len(sohs), 1) if sohs else 0.0
        min_soh = min(sohs) if sohs else 0.0

        max_delta_v = max(deltas) if deltas else 0.0
        max_temp = max(temps) if temps else 0.0
        avg_voltage = round(sum(voltages) / len(voltages), 2) if voltages else 0.0

        # Outlier Detection
        outliers: list[dict[str, Any]] = []
        for b in online_batts:
            sid = b["slave_id"]
            name = b["name"]
            # Check cell delta
            if b.get("cell_voltage_delta_mv", 0) > 30.0:
                outliers.append({
                    "slave_id": sid,
                    "battery_name": name,
                    "type": "CELL_IMBALANCE",
                    "severity": "WARNING" if b["cell_voltage_delta_mv"] < 60.0 else "CRITICAL",
                    "message": f"{name} cell voltage spread is {b['cell_voltage_delta_mv']} mV (exceeds 30 mV recommended threshold)."
                })
            # Check anti-theft lock
            if b.get("parameters", {}).get("gyroscope_anti_theft_locked"):
                outliers.append({
                    "slave_id": sid,
                    "battery_name": name,
                    "type": "ANTI_THEFT_LOCKED",
                    "severity": "WARNING",
                    "message": f"{name} Gyroscope / Anti-Theft Lock is ACTIVE (charging/discharging may be throttled)."
                })
            # Check SOH degradation
            if b.get("soh", 100) < 90.0:
                outliers.append({
                    "slave_id": sid,
                    "battery_name": name,
                    "type": "SOH_DEGRADED",
                    "severity": "WARNING",
                    "message": f"{name} SOH degraded to {b['soh']}% (cycle count: {b.get('cycle_count')})."
                })

        # Check current sharing imbalance
        if len(online_batts) > 1 and abs(total_current) > 5.0:
            avg_i = total_current / len(online_batts)
            for b in online_batts:
                i_diff = abs(b.get("current", 0) - avg_i)
                if i_diff > 3.0:
                    outliers.append({
                        "slave_id": b["slave_id"],
                        "battery_name": b["name"],
                        "type": "CURRENT_IMBALANCE",
                        "severity": "INFO",
                        "message": f"{b['name']} carrying {b.get('current')} A (diverges by {i_diff:.1f} A from string average {avg_i:.1f} A)."
                    })

        total_alarms = sum(b.get("alarm_count", 0) for b in online_batts)

        summary = {
            "battery_count": len(self.configured_batteries),
            "online_count": len(online_batts),
            "total_capacity_ah": total_cap_ah,
            "total_remaining_ah": total_remaining_ah,
            "total_energy_kwh": round((total_cap_ah * avg_voltage) / 1000.0, 2),
            "total_current_a": total_current,
            "total_power_kw": total_power,
            "avg_pack_voltage_v": avg_voltage,
            "avg_soc": avg_soc,
            "min_soc": min_soc,
            "max_soc": max_soc,
            "soc_divergence": soc_divergence,
            "avg_soh": avg_soh,
            "min_soh": min_soh,
            "max_cell_delta_mv": max_delta_v,
            "max_temperature_c": max_temp,
            "total_alarms": total_alarms,
            "outliers": outliers,
        }

        result = {
            "timestamp": now,
            "summary": summary,
            "batteries": battery_data,
            "is_simulation": is_sim,
            "active_slave_id": self.active_slave_id
        }

        self.last_audit_data = result
        return result

    def save_audit_snapshot(
        self,
        operator: str = "ADMINISTRATOR",
        notes: str = ""
    ) -> dict[str, Any]:
        """Perform full read and persist fleet snapshot to database."""
        audit_res = self.read_all_batteries()
        audit_id = MultiBatteryAuditCRUD.save_audit(
            battery_count=audit_res["summary"]["battery_count"],
            summary=audit_res["summary"],
            audit_data=audit_res["batteries"],
            operator=operator,
            notes=notes
        )

        # Log action in audit trail
        AuditCRUD.log(
            user_role=operator,
            action="MULTI_BATTERY_AUDIT_SAVE",
            parameter_name="Fleet Snapshot",
            parameter_address=None,
            previous_value=None,
            requested_value=f"Audit #{audit_id} ({audit_res['summary']['battery_count']} packs)",
            status="SUCCESS",
            details=f"Saved fleet audit snapshot for {audit_res['summary']['battery_count']} batteries. Avg SOC: {audit_res['summary']['avg_soc']}%, Max Delta V: {audit_res['summary']['max_cell_delta_mv']} mV."
        )

        return {
            "success": True,
            "audit_id": audit_id,
            "timestamp": audit_res["timestamp"],
            "summary": audit_res["summary"],
            "message": f"Successfully saved fleet audit #{audit_id} with {audit_res['summary']['battery_count']} batteries."
        }

    def export_audit_csv(self, audit_data: Optional[dict[str, Any]] = None) -> str:
        """Generate structured CSV table comparing all batteries."""
        data = audit_data or self.last_audit_data or self.read_all_batteries()
        batteries = data.get("batteries", [])

        output = io.StringIO()
        writer = csv.writer(output)

        # Header comments
        writer.writerow(["# Huawei BMS Fleet Comparison & Capability Report"])
        writer.writerow(["# Generated At", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data.get("timestamp", time.time())))])
        writer.writerow(["# Total Batteries", data.get("summary", {}).get("battery_count", len(batteries))])
        writer.writerow(["# Bank Capacity (Ah)", data.get("summary", {}).get("total_capacity_ah", 0)])
        writer.writerow(["# Bank Net Current (A)", data.get("summary", {}).get("total_current_a", 0)])
        writer.writerow([])

        # Table headers
        headers = [
            "Slave ID",
            "Battery Name",
            "Device Model",
            "Serial Number",
            "Status",
            "SOC (%)",
            "SOH (%)",
            "Pack Voltage (V)",
            "Current (A)",
            "Power (kW)",
            "Temperature (°C)",
            "Cycle Count",
            "Rated Cap (Ah)",
            "Remaining Cap (Ah)",
            "Cell Delta (mV)",
            "Min Cell (V)",
            "Min Cell #",
            "Max Cell (V)",
            "Max Cell #",
            "Avg Cell (V)",
            "Max Temp (°C)",
            "Active Alarms",
            "Anti-Theft Locked",
            "Charge Limit (A)",
            "Discharge Limit (A)"
        ]
        writer.writerow(headers)

        for b in batteries:
            params = b.get("parameters", {})
            writer.writerow([
                b.get("slave_id"),
                b.get("name"),
                b.get("model"),
                b.get("serial_number"),
                b.get("operating_state"),
                b.get("soc"),
                b.get("soh"),
                b.get("total_voltage"),
                b.get("current"),
                b.get("power"),
                b.get("temperature"),
                b.get("cycle_count"),
                b.get("rated_capacity_ah"),
                b.get("remaining_capacity_ah"),
                b.get("cell_voltage_delta_mv"),
                b.get("min_cell_voltage"),
                b.get("min_cell_index"),
                b.get("max_cell_voltage"),
                b.get("max_cell_index"),
                b.get("avg_cell_voltage"),
                b.get("max_cell_temp"),
                "; ".join(str(a) for a in b.get("active_alarms", [])) if b.get("active_alarms") else "None",
                "YES" if params.get("gyroscope_anti_theft_locked") else "NO",
                params.get("charge_limit_a", 50.0),
                params.get("discharge_limit_a", 100.0)
            ])

        return output.getvalue()

    def export_audit_json(self, audit_data: Optional[dict[str, Any]] = None) -> str:
        """Export complete audit structure as formatted JSON."""
        data = audit_data or self.last_audit_data or self.read_all_batteries()
        return json.dumps(data, indent=2)
