"""Unit tests for Register Mapping, Bounds Validation, and Safety Guards."""

import pytest
from app.database.crud import AuditCRUD
from app.database.db import init_db
from app.protocol.register_map import (
    AccessMode,
    ByteOrder,
    DataType,
    RegisterDatabase,
    RegisterDefinition,
    decode_register_value,
    encode_register_value,
)
from app.serial_comm.serial_client import SerialClient
from app.services.config_service import ConfigService
from app.simulator.bms_simulator import BMSSimulator


@pytest.fixture
def reg_db():
    db = RegisterDatabase()
    # Register 37002: Pack Voltage (uint16, 0.1V)
    db.register(RegisterDefinition(
        name="Battery Voltage",
        address=37002,
        function_code=3,
        data_type=DataType.UINT16,
        length_registers=1,
        scaling_divisor=10.0,
        unit="V",
        access_mode=AccessMode.READ_ONLY
    ))
    # Register 37003: Pack Current (int16, 0.1A, negative is charging)
    db.register(RegisterDefinition(
        name="Battery Current",
        address=37003,
        function_code=3,
        data_type=DataType.INT16,
        length_registers=1,
        scaling_divisor=10.0,
        unit="A",
        access_mode=AccessMode.READ_ONLY
    ))
    # Register 47085: Lower SOC Cutoff (uint16, 0.1%, range 0 to 20%)
    db.register(RegisterDefinition(
        name="End-of-Discharge SOC Cutoff",
        address=47085,
        function_code=3,
        data_type=DataType.UINT16,
        length_registers=1,
        scaling_divisor=10.0,
        unit="%",
        access_mode=AccessMode.WRITABLE,
        min_value=0.0,
        max_value=20.0,
        description="Low SOC cutoff",
        category="parameter"
    ))
    # Register 99999: Dangerous/Undocumented register
    db.register(RegisterDefinition(
        name="Secret Undocumented Register",
        address=99999,
        function_code=3,
        data_type=DataType.UINT16,
        length_registers=1,
        access_mode=AccessMode.WRITABLE,
        is_undocumented=True
    ))
    return db


def test_decode_signed_current(reg_db):
    curr_def = reg_db.get(37003)
    # 0xFF38 = -200 decimal => -20.0 A
    raw_val = 0xFF38
    val, formatted = decode_register_value([raw_val], curr_def)
    assert val == -20.0
    assert "A" in formatted


def test_decode_sentinel_unavailable(reg_db):
    volt_def = reg_db.get(37002)
    # Huawei sentinel 0xFFFF indicates unmeasured / disconnected
    val, formatted = decode_register_value([0xFFFF], volt_def)
    assert val is None
    assert formatted == "N/A"


def test_encode_with_bounds_enforcement(reg_db):
    soc_def = reg_db.get(47085)
    # Valid: 10.0% => raw 100
    raw = encode_register_value(10.0, soc_def)
    assert raw == [100]

    # Out of bounds: 25.0% (> 20.0% max)
    with pytest.raises(ValueError, match="above allowed maximum"):
        encode_register_value(25.0, soc_def)

    # Out of bounds: -5.0% (< 0.0% min)
    with pytest.raises(ValueError, match="below allowed minimum"):
        encode_register_value(-5.0, soc_def)


def test_undocumented_register_write_prohibited(reg_db):
    undoc = reg_db.get(99999)
    with pytest.raises(PermissionError, match="undocumented"):
        encode_register_value(10, undoc)


def test_guarded_write_workflow(reg_db):
    init_db()
    simulator = BMSSimulator()
    serial_client = SerialClient()
    config_svc = ConfigService(serial_client, reg_db, simulator)

    # 1. By default, writes must be disabled (Read-only mode)
    assert config_svc.writes_enabled is False

    with pytest.raises(PermissionError, match="locked"):
        config_svc.execute_guarded_write(
            address=47085,
            new_value=12.0,
            user_role="OPERATOR",
            operator_confirmed=True,
            is_simulation=True
        )

    # 2. Enable writes as ADMINISTRATOR
    config_svc.enable_writes("ADMINISTRATOR")
    assert config_svc.writes_enabled is True

    # 3. Non-allowlisted register write must be rejected
    res = config_svc.execute_guarded_write(
        address=99999,
        new_value=1,
        user_role="ADMINISTRATOR",
        operator_confirmed=True,
        is_simulation=True
    )
    assert res.success is False
    assert "NOT on the verified writable allowlist" in res.message

    # 4. Successful 10-step write to allowlisted register 47085
    res = config_svc.execute_guarded_write(
        address=47085,
        new_value=12.0,
        user_role="ADMINISTRATOR",
        operator_confirmed=True,
        is_simulation=True
    )
    assert res.success is True
    assert res.verified_value == 12.0
    assert len(res.steps) == 10
    assert all(s.status == "COMPLETED" for s in res.steps)

    # 5. Verify audit entry was created
    assert res.audit_id is not None
    trail = AuditCRUD.get_audit_trail(limit=5)
    assert any(t["id"] == res.audit_id for t in trail)
