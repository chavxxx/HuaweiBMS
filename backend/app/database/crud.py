"""Database CRUD Operations with Indexed Filtering and Retention Management."""

import json
import sqlite3
import time
from typing import Any, Optional
from .db import get_db_connection


class TelemetryCRUD:
    @staticmethod
    def record_telemetry(data: dict[str, Any], db_path: Optional[str] = None) -> int:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry_history (
                timestamp, device_id, is_simulation, soc, soh, total_voltage,
                current, power, temperature, min_cell_voltage, max_cell_voltage,
                cell_voltage_delta, min_cell_temp, max_cell_temp, bms_status,
                active_alarms_count, charge_energy, discharge_energy, raw_telemetry_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("timestamp", time.time()),
            data.get("device_id", "Unknown"),
            1 if data.get("is_simulation", False) else 0,
            data.get("soc"),
            data.get("soh"),
            data.get("total_voltage"),
            data.get("current"),
            data.get("power"),
            data.get("temperature"),
            data.get("min_cell_voltage"),
            data.get("max_cell_voltage"),
            data.get("cell_voltage_delta"),
            data.get("min_cell_temp"),
            data.get("max_cell_temp"),
            data.get("bms_status"),
            data.get("active_alarms_count", 0),
            data.get("charge_energy"),
            data.get("discharge_energy"),
            json.dumps(data.get("raw_telemetry", {}))
        ))
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id

    @staticmethod
    def query_history(
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 500,
        db_path: Optional[str] = None
    ) -> list[dict[str, Any]]:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM telemetry_history WHERE 1=1"
        params: list[Any] = []

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        # Return in chronological order
        return sorted(rows, key=lambda x: x["timestamp"])

    @staticmethod
    def purge_older_than(days: int = 30, db_path: Optional[str] = None) -> int:
        cutoff = time.time() - (days * 86400)
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM telemetry_history WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted


class AlarmCRUD:
    @staticmethod
    def upsert_active_alarm(alarm: dict[str, Any], db_path: Optional[str] = None) -> None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        code = alarm["code"]
        now = time.time()

        cursor.execute("SELECT id FROM alarm_events WHERE alarm_code = ? AND is_active = 1", (code,))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE alarm_events SET last_seen = ? WHERE id = ?", (now, row["id"]))
        else:
            cursor.execute("""
                INSERT INTO alarm_events (
                    alarm_code, name, severity, subsystem, description,
                    corrective_action, first_seen, last_seen, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                code, alarm["name"], alarm["severity"], alarm.get("subsystem", ""),
                alarm.get("description", ""), alarm.get("corrective_action", ""), now, now
            ))
        conn.commit()
        conn.close()

    @staticmethod
    def mark_cleared_if_absent(active_codes: list[int], db_path: Optional[str] = None) -> None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        now = time.time()
        if not active_codes:
            cursor.execute("UPDATE alarm_events SET is_active = 0, cleared_at = ? WHERE is_active = 1", (now,))
        else:
            placeholders = ",".join("?" for _ in active_codes)
            cursor.execute(f"UPDATE alarm_events SET is_active = 0, cleared_at = ? WHERE is_active = 1 AND alarm_code NOT IN ({placeholders})", [now] + active_codes)
        conn.commit()
        conn.close()

    @staticmethod
    def get_alarms(active_only: bool = False, db_path: Optional[str] = None) -> list[dict[str, Any]]:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM alarm_events WHERE is_active = 1 ORDER BY first_seen DESC")
        else:
            cursor.execute("SELECT * FROM alarm_events ORDER BY first_seen DESC LIMIT 200")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


class AuditCRUD:
    @staticmethod
    def record_entry(entry: dict[str, Any], db_path: Optional[str] = None) -> int:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (
                timestamp, user_role, action, parameter_name, parameter_address,
                previous_value, requested_value, validation_result,
                device_response, read_back_value, status, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get("timestamp", time.time()),
            entry.get("user_role", "OPERATOR"),
            entry.get("action", "WRITE_PARAMETER"),
            entry.get("parameter_name"),
            entry.get("parameter_address"),
            str(entry.get("previous_value", "")),
            str(entry.get("requested_value", "")),
            entry.get("validation_result", "PASSED"),
            entry.get("device_response", ""),
            str(entry.get("read_back_value", "")),
            entry.get("status", "SUCCESS"),
            entry.get("details", "")
        ))
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id

    @staticmethod
    def get_audit_trail(limit: int = 200, db_path: Optional[str] = None) -> list[dict[str, Any]]:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


class SnapshotCRUD:
    @staticmethod
    def save_snapshot(name: str, device_id: str, role: str, notes: str, params: dict[str, Any], db_path: Optional[str] = None) -> int:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO config_snapshots (
                timestamp, snapshot_name, device_id, author_role, notes, parameters_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (time.time(), name, device_id, role, notes, json.dumps(params)))
        s_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return s_id

    @staticmethod
    def list_snapshots(db_path: Optional[str] = None) -> list[dict[str, Any]]:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, snapshot_name, device_id, author_role, notes FROM config_snapshots ORDER BY timestamp DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_snapshot(snapshot_id: int, db_path: Optional[str] = None) -> Optional[dict[str, Any]]:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM config_snapshots WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["parameters"] = json.loads(d["parameters_json"])
        return d
