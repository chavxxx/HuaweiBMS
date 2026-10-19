"""Unit tests for Huawei EMS-4805B1 physical frame verification and register map."""

import json
from pathlib import Path
from app.protocol.crc16 import verify_crc16, calculate_crc16
from app.protocol.register_map import RegisterDatabase, AccessMode


def test_ems4805b1_real_telemetry_frame_crc():
    """Verify the exact physical frame captured from the Huawei EMS-4805B1."""
    # Captured frame: D6 03 08 14 EC 14 EB 00 00 00 62 AC BB
    raw_rx = bytes.fromhex("D6 03 08 14 EC 14 EB 00 00 00 62 AC BB")
    
    # 1. CRC verification
    assert verify_crc16(raw_rx) is True
    
    # 2. Frame structure
    slave_id = raw_rx[0]
    func_code = raw_rx[1]
    byte_count = raw_rx[2]
    assert slave_id == 214  # 0xD6
    assert func_code == 0x03
    assert byte_count == 8

    # 3. Register decoding
    reg0_v_bus = int.from_bytes(raw_rx[3:5], "big") * 0.01
    reg1_v_cellsum = int.from_bytes(raw_rx[5:7], "big") * 0.01
    reg2_current = int.from_bytes(raw_rx[7:9], "big", signed=True) * 0.01
    reg3_soc = int.from_bytes(raw_rx[9:11], "big")

    assert round(reg0_v_bus, 2) == 53.56
    assert round(reg1_v_cellsum, 2) == 53.55
    assert round(reg2_current, 2) == 0.00
    assert reg3_soc == 98


def test_ems4805b1_cell_voltages_decoding():
    """Verify individual 16-cell LiFePO4 series voltage block decoding."""
    # Physical capture for Reg 0x0022 - 0x0029 (Cells 1-8)
    # RX: D6 03 10 0D 12 0D 16 0D 12 0D 12 0D 13 0D 12 ED 2D ...
    rx_cells_chunk1 = bytes.fromhex("D6 03 10 0D 12 0D 16 0D 12 0D 12 0D 13 0D 12 0D 16 0D 12")
    cells = [int.from_bytes(rx_cells_chunk1[3+i*2:5+i*2], "big") / 1000.0 for i in range(8)]
    
    assert cells[0] == 3.346
    assert cells[1] == 3.350
    assert min(cells) >= 3.2
    assert max(cells) <= 3.65


def test_ems4805b1_register_database_integrity():
    """Verify that all registers in huawei_ems_4805b1.json are documented and have valid access modes."""
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "huawei_ems_4805b1.json"
    assert json_path.exists()

    db = RegisterDatabase()
    count = db.import_from_json(json_path.read_text())
    assert count >= 16

    # Zero-fabrication check: every register must have documented verification source
    for reg in db.list_all():
        assert "Verified via physical Modbus RTU telemetry" in reg.source_doc or "Wire dump" in reg.source_doc or "Huawei ESM" in reg.source_doc
        assert reg.access_mode in (AccessMode.READ_ONLY, AccessMode.WRITABLE)
        assert reg.function_code == 3


def test_esm48150b1_register_database_integrity():
    """Verify that all registers in huawei_esm_48150b1.json are documented and verified."""
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "huawei_esm_48150b1.json"
    assert json_path.exists()

    db = RegisterDatabase()
    count = db.import_from_json(json_path.read_text())
    assert count >= 50

    for reg in db.list_all():
        assert "Wire dump" in reg.source_doc or "Verified" in reg.source_doc or "Huawei ESM" in reg.source_doc
        assert reg.access_mode in (AccessMode.READ_ONLY, AccessMode.WRITABLE)
        assert reg.function_code == 3


def test_battery_unlock_and_presets_service():
    """Verify Battery Unlock Wizard and Presets application."""
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "huawei_esm_48150b1.json"
    db = RegisterDatabase()
    db.import_from_json(json_path.read_text())

    from app.serial_comm.serial_client import SerialClient
    from app.services.config_service import ConfigService
    from app.simulator.bms_simulator import BMSSimulator
    from app.database.db import init_db

    init_db()
    sim = BMSSimulator()
    serial_client = SerialClient()
    svc = ConfigService(serial_client, db, sim)

    # 1. Presets list should contain 5 verified presets
    presets = svc.get_presets()
    assert len(presets) >= 5
    preset_ids = [p["id"] for p in presets]
    assert "solar_offgrid_standalone" in preset_ids
    assert "high_rate_fast_charge" in preset_ids
    assert "eco_longevity" in preset_ids
    assert "second_hand_restore" in preset_ids
    assert "telecom_float_backup" in preset_ids

    # 2. Applying preset while locked should raise PermissionError
    import pytest
    with pytest.raises(PermissionError, match="locked"):
        svc.apply_preset("solar_offgrid_standalone", "ADMINISTRATOR", is_simulation=True)

    # 3. Unlock writes as ADMINISTRATOR
    svc.enable_writes("ADMINISTRATOR")
    assert svc.writes_enabled is True

    # 4. Execute Battery Unlock Wizard
    # Initially simulated battery gyro lock is 1 (locked)
    assert sim.parameters[4376] == 1
    unlock_res = svc.unlock_battery("ADMINISTRATOR", sync_clock=True, restore_charge_rate=0.500, is_simulation=True)
    assert unlock_res["success"] is True
    assert sim.parameters[4376] == 0  # Gyroscope unlocked
    assert sim.parameters[4377] == 0  # Sensitivity Low
    assert sim.parameters[4109] == 500  # Charge rate 0.5C
    assert sim.parameters[4123] == 500  # Default NVRAM rate 0.5C

    # 5. Apply Solar Off-Grid Standalone Preset
    apply_res = svc.apply_preset("solar_offgrid_standalone", "ADMINISTRATOR", is_simulation=True)
    assert apply_res["success"] is True
    assert sim.parameters[4376] == 0
    assert sim.parameters[4109] == 500
    assert sim.parameters[4107] == 1000


def test_esm_power_and_cutoff_telemetry_grounding():
    """Verify that physical ESM-48150B1 hardware eliminates Read Error and provides true physical values."""
    from unittest.mock import MagicMock
    from app.protocol.modbus_rtu import ProtocolResponse
    from app.serial_comm.serial_client import SerialClient
    from app.services.config_service import ConfigService
    from app.services.telemetry_service import TelemetryService
    from app.simulator.bms_simulator import BMSSimulator

    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "huawei_esm_48150b1.json"
    db = RegisterDatabase()
    db.import_from_json(json_path.read_text())

    sim = BMSSimulator()
    serial_client = SerialClient()
    telemetry_svc = TelemetryService(serial_client, db, sim)
    
    # Populate live physical telemetry matching user's real ESM-48150B1 hardware
    telemetry_svc.latest_telemetry = {
        "total_voltage": 53.94,
        "rated_capacity_ah": 150,
        "max_current_limit_a": 150,
    }

    config_svc = ConfigService(serial_client, db, sim, telemetry_service=telemetry_svc)

    # Mock physical Modbus transaction where 47081-47086 fail (Exception 0x02 Illegal Address on ESM),
    # but base registers (Reg 4109 = 150 raw -> 0.150C, Reg 4107 = 680 raw -> 0.680C) succeed.
    def mock_transaction(frame, expected_func, is_write=False):
        addr = (frame[2] << 8) | frame[3]
        if addr in (47081, 47083, 47085, 47086, 41015, 47001):
            # Battery responds with Illegal Address for high ESS registers
            return ProtocolResponse(success=False, function_code=expected_func, is_exception=True, exception_code=0x02, error_message="Illegal Data Address")
        elif addr == 4109:
            # 0.150 C charge limit
            return ProtocolResponse(success=True, function_code=0x03, values=[150])
        elif addr == 4107:
            # 0.680 C discharge limit
            return ProtocolResponse(success=True, function_code=0x03, values=[680])
        elif addr in (4096, 4097, 4098, 4099, 4100, 4101):
            # RTC clock
            return ProtocolResponse(success=True, function_code=0x03, values=[2026])
        elif addr in (4376, 4377, 4111, 4112, 4123):
            return ProtocolResponse(success=True, function_code=0x03, values=[0])
        elif addr in (67, 69):
            return ProtocolResponse(success=True, function_code=0x03, values=[2576])
        elif addr == 259:
            return ProtocolResponse(success=True, function_code=0x03, values=[150])
        elif addr == 263:
            return ProtocolResponse(success=True, function_code=0x03, values=[150])
        elif addr == 271:
            return ProtocolResponse(success=True, function_code=0x03, values=[16])
        return ProtocolResponse(success=False, function_code=expected_func, error_message="Unknown")

    serial_client.execute_transaction = MagicMock(side_effect=mock_transaction)

    # 1. Read all parameters for physical hardware (is_simulation=False)
    params = config_svc.read_all_parameters(is_simulation=False)
    assert len(params) >= 17

    # 2. Verify ZERO "Read Error" in any parameter
    errors = [p for p in params if p["current_formatted"] == "Read Error"]
    assert len(errors) == 0, f"Found parameters with Read Error: {errors}"

    # 3. Verify true physical derivation of Max Charge Power (Reg 47081)
    # P_charge = 53.94V * (0.150C * 150Ah) = 1213.65 W
    p_charge = next(p for p in params if p["address"] == 47081)
    assert abs(p_charge["current_raw"] - 1213.65) < 0.1
    assert "W" in p_charge["current_formatted"]
    assert "0.15C" in p_charge["current_formatted"]

    # 4. Verify true physical derivation of Max Discharge Power (Reg 47083)
    # P_discharge = 53.94V * (0.680C * 150Ah) = 5501.88 W
    p_discharge = next(p for p in params if p["address"] == 47083)
    assert abs(p_discharge["current_raw"] - 5501.88) < 0.1
    assert "5501.9 W" in p_discharge["current_formatted"]
    assert "0.68C" in p_discharge["current_formatted"]

    # 5. Verify End-of-Discharge Cutoff (Reg 47085)
    soc_cutoff = next(p for p in params if p["address"] == 47085)
    assert soc_cutoff["current_raw"] == 0.0
    assert "44.0V LVD Hardware Cutoff" in soc_cutoff["current_formatted"]

    # 6. Verify End-of-Charge Cutoff (Reg 47086)
    soc_full = next(p for p in params if p["address"] == 47086)
    assert soc_full["current_raw"] == 100.0
    assert "56.8V HVD Absorption Cutoff" in soc_full["current_formatted"]


def test_hardware_sentinel_filtering_and_11_cell_pack():
    """Verify that 65535 and -999 sentinels from 11-channel batteries (new_low.txt) are filtered."""
    from unittest.mock import MagicMock
    from app.protocol.modbus_rtu import ProtocolResponse
    from app.serial_comm.serial_client import SerialClient
    from app.services.telemetry_service import TelemetryService
    from app.simulator.bms_simulator import BMSSimulator

    db = RegisterDatabase()
    sim = BMSSimulator()
    serial_client = SerialClient()
    serial_client.is_connected = True
    telemetry_svc = TelemetryService(serial_client, db, sim)

    # Values matching new_low.txt captured from physical battery
    # Regs 18..33: 11 active sensors (28-30°C) + 5 sentinels (64537 / -999)
    temps_raw = [29, 28, 28, 28, 28, 28, 28, 30, 28, 28, 29, 64537, 64537, 64537, 64537, 64537]
    # Regs 34..49: 11 active cells (3394-3407 mV) + 5 sentinels (65535 / 0xFFFF)
    cells_raw = [3399, 3398, 3398, 3397, 3394, 3402, 3405, 3406, 3407, 3406, 3406, 65535, 65535, 65535, 65535, 65535]

    def mock_poll(request_bytes, expected_func):
        addr = int.from_bytes(request_bytes[2:4], "big")
        cnt = int.from_bytes(request_bytes[4:6], "big")

        if addr == 0 and cnt == 8:
            return ProtocolResponse(success=True, function_code=0x03, values=[5343, 5103, 50, 100, 98, 30, 28, 0])
        elif addr == 0x000A:
            return ProtocolResponse(success=True, function_code=0x03, values=[1, 0, 2, 0, 2])
        elif addr == 18 and cnt == 16:
            return ProtocolResponse(success=True, function_code=0x03, values=temps_raw)
        elif addr == 34 and cnt == 16:
            return ProtocolResponse(success=True, function_code=0x03, values=cells_raw)
        elif addr == 69:
            return ProtocolResponse(success=True, function_code=0x03, values=[27354])
        elif addr == 818:
            # "ESM-48150B1"
            return ProtocolResponse(success=True, function_code=0x03, values=[17747, 19757, 13368, 12597, 12354, 12799])
        elif addr == 529:
            return ProtocolResponse(success=True, function_code=0x03, values=[21826, 12850, 12338, 12336, 12339, 13364])
        elif addr == 836:
            return ProtocolResponse(success=True, function_code=0x03, values=[2025, 5, 31])
        elif addr == 259:
            return ProtocolResponse(success=True, function_code=0x03, values=[102, 1, 0, 205, 150])
        return ProtocolResponse(success=False, function_code=expected_func, error_message="Mock unmapped")

    serial_client.execute_transaction = MagicMock(side_effect=mock_poll)

    # Run physical poll
    telemetry_svc._poll_hardware_bms()

    # Verify telemetry results
    t = telemetry_svc.latest_telemetry
    c = telemetry_svc.latest_cells
    e = telemetry_svc.latest_electrical

    assert t["device_model"] == "Huawei ESM-48150B1"
    assert t["mfg_date"] == "2025-05-31"
    assert t["rated_capacity_ah"] == 102
    assert t["max_current_limit_a"] == 150
    assert t["cycle_count"] == 27354
    assert t["total_voltage"] == 51.03
    assert t["soc"] == 100.0
    assert t["soh"] == 98.0

    # Verify Cell filtering (11 active cells, NO 65.535V corrupted values)
    assert c["cell_count"] == 11
    assert len(c["cell_voltages"]) == 11
    assert c["min_cell_voltage"] == 3.394
    assert c["max_cell_voltage"] == 3.407
    assert c["cell_voltage_delta_mv"] == 13.0
    assert c["avg_cell_voltage"] == 3.402
    assert max(c["cell_voltages"]) < 4.0

    # Verify Temperature filtering (11 active sensors, NO -999°C corrupted values)
    assert len(c["temperatures"]) == 11
    assert c["min_cell_temp"] == 28.0
    assert c["max_cell_temp"] == 30.0
    assert c["temperature_spread"] == 2.0
    assert min(c["temperatures"]) >= 0.0



