"""Unit tests for BMS Simulator and Telemetry Freshness Calculation."""

import time
import pytest
from app.protocol.crc16 import append_crc16
from app.protocol.modbus_rtu import ModbusRTUAdapter
from app.protocol.register_map import RegisterDatabase
from app.serial_comm.serial_client import SerialClient
from app.services.telemetry_service import TelemetryService
from app.simulator.bms_simulator import BMSSimulator


def test_bms_simulator_response_to_read():
    sim = BMSSimulator(slave_id=1)
    adapter = ModbusRTUAdapter()

    # Read Holding Registers 37000 (status), 3 registers
    req = adapter.build_read_holding_registers(slave_id=1, start_address=37000, count=3)
    resp_bytes = sim.process_raw_frame(req)

    assert len(resp_bytes) >= 5
    parsed = adapter.parse_response(1, 0x03, resp_bytes)
    assert parsed.success is True
    assert len(parsed.values) == 3
    # Check running status, mode, voltage
    assert parsed.values[0] == sim.running_status
    assert parsed.values[1] == sim.working_mode


def test_bms_simulator_illegal_address_exception():
    sim = BMSSimulator(slave_id=1)
    adapter = ModbusRTUAdapter()

    # Query unmapped address 59999
    req = adapter.build_read_holding_registers(slave_id=1, start_address=59999, count=1)
    resp_bytes = sim.process_raw_frame(req)

    parsed = adapter.parse_response(1, 0x03, resp_bytes)
    assert parsed.success is False
    assert parsed.is_exception is True
    assert parsed.exception_code == 0x02  # Illegal Data Address


def test_telemetry_freshness():
    sim = BMSSimulator()
    serial_client = SerialClient()
    reg_db = RegisterDatabase()
    svc = TelemetryService(serial_client, reg_db, sim)

    # Initial state
    freshness = svc.get_freshness_status()
    assert freshness["is_stale"] is True

    # After update
    svc.last_update_timestamp = time.time()
    freshness = svc.get_freshness_status()
    assert freshness["status"] == "FRESH"
    assert freshness["is_stale"] is False

    # Simulate stale (8 seconds ago)
    svc.last_update_timestamp = time.time() - 8.0
    freshness = svc.get_freshness_status()
    assert freshness["status"] == "STALE_WARNING"
    assert freshness["is_stale"] is True

    # Simulate critical stale (20 seconds ago)
    svc.last_update_timestamp = time.time() - 20.0
    freshness = svc.get_freshness_status()
    assert freshness["status"] == "CRITICAL_STALE"
    assert freshness["is_stale"] is True
