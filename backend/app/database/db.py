"""SQLite Database Connection and Schema Initialization."""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

import sys

logger = logging.getLogger("huawei_bms.database")

def get_user_data_dir() -> Path:
    """Resolve writable data directory across development and frozen standalone modes."""
    if os.environ.get("HUAWEI_BMS_DB_PATH"):
        p = Path(os.environ["HUAWEI_BMS_DB_PATH"]).parent
        p.mkdir(parents=True, exist_ok=True)
        return p
    if getattr(sys, "frozen", False):
        user_dir = Path.home() / ".huawei_bms_manager"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    dev_dir = Path(__file__).resolve().parent.parent.parent / "data"
    dev_dir.mkdir(parents=True, exist_ok=True)
    return dev_dir

DB_DIR = get_user_data_dir()
DEFAULT_DB_PATH = DB_DIR / "huawei_bms.db"


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Obtain a SQLite connection with WAL mode enabled and Row factory."""
    path = db_path or str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    # Enable Write-Ahead Logging for concurrency and performance
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Telemetry History (Indexed on timestamp)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            device_id TEXT NOT NULL,
            is_simulation INTEGER NOT NULL DEFAULT 0,
            soc REAL,
            soh REAL,
            total_voltage REAL,
            current REAL,
            power REAL,
            temperature REAL,
            min_cell_voltage REAL,
            max_cell_voltage REAL,
            cell_voltage_delta REAL,
            min_cell_temp REAL,
            max_cell_temp REAL,
            bms_status INTEGER,
            active_alarms_count INTEGER DEFAULT 0,
            charge_energy REAL,
            discharge_energy REAL,
            raw_telemetry_json TEXT
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry_history(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_dev ON telemetry_history(device_id);")

    # 2. Alarms & Faults History
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarm_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alarm_code INTEGER NOT NULL,
            name TEXT NOT NULL,
            severity TEXT NOT NULL,
            subsystem TEXT,
            description TEXT,
            corrective_action TEXT,
            first_seen REAL NOT NULL,
            last_seen REAL NOT NULL,
            cleared_at REAL,
            is_active INTEGER NOT NULL DEFAULT 1,
            acknowledged INTEGER NOT NULL DEFAULT 0,
            acknowledged_by TEXT,
            acknowledged_at REAL
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarm_active ON alarm_events(is_active);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarm_code ON alarm_events(alarm_code);")

    # 3. Audit Log (Mandatory 10-step write tracking & security trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            parameter_name TEXT,
            parameter_address INTEGER,
            previous_value TEXT,
            requested_value TEXT,
            validation_result TEXT,
            device_response TEXT,
            read_back_value TEXT,
            status TEXT NOT NULL,  -- 'SUCCESS', 'VERIFICATION_FAILED', 'REJECTED', 'ABORTED'
            details TEXT
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);")

    # 4. Configuration Snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            snapshot_name TEXT NOT NULL,
            device_id TEXT,
            author_role TEXT,
            notes TEXT,
            parameters_json TEXT NOT NULL
        );
    """)

    # 5. Saved Connection Profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connection_profiles (
            name TEXT PRIMARY KEY,
            port TEXT NOT NULL,
            baudrate INTEGER NOT NULL,
            parity TEXT NOT NULL,
            stopbits REAL NOT NULL,
            data_bits INTEGER NOT NULL,
            slave_id INTEGER NOT NULL,
            timeout REAL NOT NULL,
            inter_frame_delay REAL NOT NULL,
            rs485_rts INTEGER NOT NULL DEFAULT 0,
            protocol TEXT NOT NULL DEFAULT 'modbus_rtu',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
    """)

    # 6. Application Settings & Thresholds
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")
