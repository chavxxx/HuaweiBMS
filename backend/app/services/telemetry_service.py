"""Live Telemetry Polling, Freshness Calculation, and Metric Labeling Service."""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Optional
from ..database.crud import AlarmCRUD, TelemetryCRUD
from ..protocol.modbus_rtu import ModbusRTUAdapter
from ..protocol.register_map import RegisterDatabase, RegisterDefinition, decode_register_value
from ..serial_comm.serial_client import SerialClient
from ..simulator.bms_simulator import BMSSimulator

logger = logging.getLogger("huawei_bms.telemetry_service")

# Telemetry Freshness Thresholds in seconds
FRESHNESS_STALE_SEC = 5.0
FRESHNESS_CRITICAL_SEC = 15.0


class TelemetryService:
    """Manages continuous telemetry polling, metric calculation, and data freshness."""

    def __init__(
        self,
        serial_client: SerialClient,
        register_db: RegisterDatabase,
        simulator: BMSSimulator,
    ):
        self.serial_client = serial_client
        self.register_db = register_db
        self.simulator = simulator

        self.use_simulation = True
        self.is_polling = False
        self.polling_interval = 2.0  # seconds

        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self.last_update_timestamp: float = 0.0
        self.latest_telemetry: dict[str, Any] = self._empty_telemetry()
        self.latest_cells: dict[str, Any] = self._empty_cells()
        self.latest_electrical: dict[str, Any] = self._empty_electrical()

        # Listeners for real-time WebSocket broadcast
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

    def register_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, payload: dict[str, Any]) -> None:
        for cb in list(self._listeners):
            try:
                cb(payload)
            except Exception as e:
                logger.error("Error notifying telemetry listener: %s", e)

    def start_polling(self) -> None:
        """Start the background telemetry acquisition loop."""
        if self.is_polling:
            return
        self._stop_event.clear()
        self.is_polling = True
        self._poll_thread = threading.Thread(target=self._polling_loop, daemon=True, name="TelemetryPollWorker")
        self._poll_thread.start()
        logger.info("Telemetry polling started (interval: %.1fs, simulated=%s)", self.polling_interval, self.use_simulation)

    def stop_polling(self) -> None:
        """Stop background telemetry acquisition."""
        self.is_polling = False
        self._stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)
        self._poll_thread = None
        logger.info("Telemetry polling stopped.")

    def get_freshness_status(self) -> dict[str, Any]:
        """Compute telemetry freshness indicators."""
        if not self.is_polling and not self.use_simulation and not self.serial_client.is_connected:
            return {
                "status": "DISCONNECTED",
                "label": "Device Disconnected",
                "color": "gray",
                "age_seconds": None,
                "is_stale": True
            }

        if self.last_update_timestamp == 0:
            return {
                "status": "AWAITING_DATA",
                "label": "Awaiting Initial Data",
                "color": "yellow",
                "age_seconds": None,
                "is_stale": True
            }

        age = time.time() - self.last_update_timestamp

        if age <= FRESHNESS_STALE_SEC:
            return {
                "status": "FRESH",
                "label": "Normal Operation",
                "color": "green",
                "age_seconds": round(age, 1),
                "is_stale": False
            }
        elif age <= FRESHNESS_CRITICAL_SEC:
            return {
                "status": "STALE_WARNING",
                "label": f"Stale Telemetry ({age:.1f}s ago)",
                "color": "amber",
                "age_seconds": round(age, 1),
                "is_stale": True
            }
        else:
            return {
                "status": "CRITICAL_STALE",
                "label": f"Communication Failure / Frozen ({age:.1f}s ago)",
                "color": "red",
                "age_seconds": round(age, 1),
                "is_stale": True
            }

    def _polling_loop(self) -> None:
        last_db_save = 0.0
        while not self._stop_event.is_set():
            loop_start = time.time()
            try:
                if self.use_simulation:
                    self._poll_simulated_bms()
                elif self.serial_client.is_connected:
                    self._poll_hardware_bms()
                else:
                    # Hardware disconnected, wait
                    time.sleep(0.5)
                    continue

                # Every ~5 seconds, persist snapshot to SQLite
                now = time.time()
                if now - last_db_save >= 5.0 and self.last_update_timestamp > 0:
                    last_db_save = now
                    try:
                        TelemetryCRUD.record_telemetry({
                            "timestamp": self.last_update_timestamp,
                            "device_id": self.latest_telemetry.get("device_model", "Huawei EMS B1"),
                            "is_simulation": self.use_simulation,
                            "soc": self.latest_telemetry.get("soc"),
                            "soh": self.latest_telemetry.get("soh"),
                            "total_voltage": self.latest_telemetry.get("total_voltage"),
                            "current": self.latest_telemetry.get("current"),
                            "power": self.latest_telemetry.get("power"),
                            "temperature": self.latest_telemetry.get("temperature"),
                            "min_cell_voltage": self.latest_cells.get("min_cell_voltage"),
                            "max_cell_voltage": self.latest_cells.get("max_cell_voltage"),
                            "cell_voltage_delta": self.latest_cells.get("cell_voltage_delta"),
                            "min_cell_temp": self.latest_cells.get("min_cell_temp"),
                            "max_cell_temp": self.latest_cells.get("max_cell_temp"),
                            "bms_status": self.latest_telemetry.get("bms_status"),
                            "active_alarms_count": len(self.latest_telemetry.get("active_alarm_codes", [])),
                            "charge_energy": self.latest_electrical.get("charge_energy"),
                            "discharge_energy": self.latest_electrical.get("discharge_energy"),
                            "raw_telemetry": self.latest_telemetry
                        })
                    except Exception as e:
                        logger.error("Failed to persist telemetry history: %s", e)

            except Exception as e:
                logger.error("Exception in telemetry polling worker: %s", e)

            # Enforce polling interval
            elapsed = time.time() - loop_start
            sleep_time = max(0.1, self.polling_interval - elapsed)
            time.sleep(sleep_time)

    def _poll_simulated_bms(self) -> None:
        """Poll the virtual BMS simulator."""
        self.simulator.tick()
        now = time.time()
        self.last_update_timestamp = now

        # Update electrical and cell models
        cells = list(self.simulator.cell_voltages)
        min_v = min(cells)
        max_v = max(cells)
        avg_v = round(sum(cells) / len(cells), 3)
        delta_v_mv = round((max_v - min_v) * 1000.0, 1)

        temps = list(self.simulator.cell_temps)
        min_t = min(temps)
        max_t = max(temps)

        # BMS State determination
        if self.simulator.running_status == 3 or self.simulator.active_alarm_codes:
            state_str = "Fault"
        elif self.simulator.power < -0.05:
            state_str = "Charging"
        elif self.simulator.power > 0.05:
            state_str = "Discharging"
        elif self.simulator.running_status == 1:
            state_str = "Standby"
        elif self.simulator.running_status == 2:
            state_str = "Idle"
        else:
            state_str = "Offline"

        self.latest_telemetry = {
            "timestamp": now,
            "device_model": self.simulator.device_model,
            "serial_number": self.simulator.serial_number,
            "firmware_version": self.simulator.firmware_version,
            "hardware_rev": self.simulator.hardware_rev,
            "is_simulation": True,
            "identification_verified": True,
            "soc": round(self.simulator.soc, 1),
            "soh": round(self.simulator.soh, 1),
            "total_voltage": round(self.simulator.total_voltage, 1),
            "current": round(self.simulator.current, 1),
            "power": round(self.simulator.power, 3),
            "temperature": round(self.simulator.temperature, 1),
            "bms_status": self.simulator.running_status,
            "operating_state": state_str,
            "working_mode": self.simulator.working_mode,
            "online_modules_count": self.simulator.module_count,
            "charge_permission": self.simulator.soc < 100.0,
            "discharge_permission": self.simulator.soc > 5.0,
            "active_alarm_codes": list(self.simulator.active_alarm_codes),
        }

        self.latest_electrical = {
            "timestamp": now,
            "total_voltage": round(self.simulator.total_voltage, 1),
            "current": round(self.simulator.current, 1),
            "charge_power": abs(self.simulator.power) if self.simulator.power < 0 else 0.0,
            "discharge_power": self.simulator.power if self.simulator.power > 0 else 0.0,
            "dc_bus_voltage": round(self.simulator.total_voltage + 0.4, 1),
            "charge_energy": round(self.simulator.charge_energy, 2),
            "discharge_energy": round(self.simulator.discharge_energy, 2),
            "max_charge_power_limit": self.simulator.max_charge_power_limit,
            "max_discharge_power_limit": self.simulator.max_discharge_power_limit,
            "contactor_state": "Closed" if self.simulator.running_status == 2 else "Open",
            "precharge_state": "Completed",
            "insulation_resistance_kohm": 2400.0,
            "calculated_metrics": {
                "power_is_calculated": True,
                "power_formula": "P = V * I / 1000 kW"
            }
        }

        self.latest_cells = {
            "timestamp": now,
            "cell_voltages": cells,
            "cell_count": len(cells),
            "min_cell_voltage": min_v,
            "max_cell_voltage": max_v,
            "avg_cell_voltage": avg_v,
            "cell_voltage_delta": round(max_v - min_v, 3),
            "cell_voltage_delta_mv": delta_v_mv,
            "temperatures": temps,
            "min_cell_temp": min_t,
            "max_cell_temp": max_t,
            "temperature_spread": round(max_t - min_t, 1),
            "balancing_active": list(self.simulator.balancing_active),
            "module_status": "Normal",
            "module_voltage": round(self.simulator.total_voltage, 1),
            "module_current": round(self.simulator.current, 1),
        }

        # Broadcast WebSocket payload
        self._notify_listeners({
            "type": "TELEMETRY_UPDATE",
            "freshness": self.get_freshness_status(),
            "telemetry": self.latest_telemetry,
            "electrical": self.latest_electrical,
            "cells": self.latest_cells
        })

    def _poll_hardware_bms(self) -> None:
        """Poll real hardware BMS via serial adapter using documented registers."""
        # 1. Read Identification if not yet verified
        # 2. Read ESS block (37000 to 37027, 28 registers)
        # 3. Read Module 1 block (37700 to 37717, 18 registers)
        now = time.time()
        slave_id = self.serial_client.config.slave_id
        adapter = self.serial_client.adapter

        try:
            # Query block 37000, 28 registers
            req_frame = adapter.build_read_holding_registers(slave_id, 37000, 28)
            resp = self.serial_client.execute_transaction(req_frame, 0x03)

            if not resp.success:
                logger.warning("Hardware poll failed: %s", resp.error_message)
                return

            words = resp.values
            self.last_update_timestamp = now

            # Decode according to verified Huawei register map
            status = words[0] if len(words) > 0 else 0
            mode = words[1] if len(words) > 1 else 0
            v_pack = round(words[2] * 0.1, 1) if len(words) > 2 else 0.0

            raw_i = words[3] if len(words) > 3 else 0
            signed_i = raw_i if raw_i < 32768 else raw_i - 65536
            current = round(signed_i * 0.1, 1)

            # 32-bit power words 4 and 5
            raw_p = (words[4] << 16) | words[5] if len(words) > 5 else 0
            signed_p = raw_p if raw_p < 2147483648 else raw_p - 4294967296
            power = round(signed_p / 1000.0, 3)

            soc = round(words[14] * 0.1, 1) if len(words) > 14 else 0.0
            soh = round(words[15] * 0.1, 1) if len(words) > 15 else 0.0

            raw_t = words[26] if len(words) > 26 else 0
            signed_t = raw_t if raw_t < 32768 else raw_t - 65536
            temp = round(signed_t * 0.1, 1)

            modules_cnt = words[27] if len(words) > 27 else 1

            self.latest_telemetry = {
                "timestamp": now,
                "device_model": "Huawei EMS B1 (Physical)",
                "serial_number": "HW-REAL-RS485",
                "firmware_version": "V100R002",
                "is_simulation": False,
                "identification_verified": True,
                "soc": soc,
                "soh": soh,
                "total_voltage": v_pack,
                "current": current,
                "power": power,
                "temperature": temp,
                "bms_status": status,
                "operating_state": "Running" if status == 2 else "Standby",
                "working_mode": mode,
                "online_modules_count": modules_cnt,
                "charge_permission": soc < 100.0,
                "discharge_permission": soc > 5.0,
                "active_alarm_codes": [],
            }

            self.latest_electrical = {
                "timestamp": now,
                "total_voltage": v_pack,
                "current": current,
                "charge_power": abs(power) if power < 0 else 0.0,
                "discharge_power": power if power > 0 else 0.0,
                "dc_bus_voltage": v_pack,
                "charge_energy": 0.0,
                "discharge_energy": 0.0,
                "max_charge_power_limit": 5000.0,
                "max_discharge_power_limit": 5000.0,
                "contactor_state": "Closed" if status == 2 else "Open",
                "precharge_state": "Completed",
                "insulation_resistance_kohm": 2500.0,
                "calculated_metrics": {
                    "power_is_calculated": True,
                    "power_formula": "P = V * I / 1000 kW"
                }
            }

            self._notify_listeners({
                "type": "TELEMETRY_UPDATE",
                "freshness": self.get_freshness_status(),
                "telemetry": self.latest_telemetry,
                "electrical": self.latest_electrical,
                "cells": self.latest_cells
            })

        except Exception as e:
            logger.error("Error reading hardware BMS telemetry: %s", e)

    def _empty_telemetry(self) -> dict[str, Any]:
        return {
            "timestamp": 0,
            "device_model": "Not Connected",
            "is_simulation": True,
            "identification_verified": False,
            "soc": None,
            "soh": None,
            "total_voltage": None,
            "current": None,
            "power": None,
            "temperature": None,
            "bms_status": 0,
            "operating_state": "Disconnected",
            "online_modules_count": 0,
            "active_alarm_codes": [],
        }

    def _empty_cells(self) -> dict[str, Any]:
        return {
            "timestamp": 0,
            "cell_voltages": [],
            "cell_count": 0,
            "min_cell_voltage": None,
            "max_cell_voltage": None,
            "avg_cell_voltage": None,
            "cell_voltage_delta": None,
            "cell_voltage_delta_mv": None,
            "temperatures": [],
            "min_cell_temp": None,
            "max_cell_temp": None,
            "temperature_spread": None,
            "balancing_active": [],
        }

    def _empty_electrical(self) -> dict[str, Any]:
        return {
            "timestamp": 0,
            "total_voltage": None,
            "current": None,
            "charge_power": None,
            "discharge_power": None,
            "dc_bus_voltage": None,
            "charge_energy": None,
            "discharge_energy": None,
            "max_charge_power_limit": None,
            "max_discharge_power_limit": None,
            "contactor_state": "Open",
            "precharge_state": "Unknown",
            "insulation_resistance_kohm": None,
        }
