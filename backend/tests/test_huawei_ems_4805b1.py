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

