"""Historical Reporting, CSV/JSON Data Export, and Database Backup/Restore."""

import csv
import io
import json
import logging
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from ..database.crud import AlarmCRUD, AuditCRUD, TelemetryCRUD
from ..database.db import DEFAULT_DB_PATH, get_db_connection

logger = logging.getLogger("huawei_bms.report_service")


class ReportService:
    @staticmethod
    def generate_summary_report(days: int = 7) -> dict[str, Any]:
        """Generate high-level operational statistics over a time window."""
        start_t = time.time() - (days * 86400)
        history = TelemetryCRUD.query_history(start_time=start_t, limit=5000)

        if not history:
            return {
                "period_days": days,
                "data_points": 0,
                "summary": "No historical data recorded for this period."
            }

        voltages = [h["total_voltage"] for h in history if h.get("total_voltage") is not None]
        temperatures = [h["temperature"] for h in history if h.get("temperature") is not None]
        socs = [h["soc"] for h in history if h.get("soc") is not None]
        powers = [h["power"] for h in history if h.get("power") is not None]

        # Calculate energy charged & discharged over period
        min_charge_e = min((h["charge_energy"] for h in history if h.get("charge_energy") is not None), default=0.0)
        max_charge_e = max((h["charge_energy"] for h in history if h.get("charge_energy") is not None), default=0.0)
        energy_charged_kwh = max(0.0, max_charge_e - min_charge_e)

        min_disch_e = min((h["discharge_energy"] for h in history if h.get("discharge_energy") is not None), default=0.0)
        max_disch_e = max((h["discharge_energy"] for h in history if h.get("discharge_energy") is not None), default=0.0)
        energy_discharged_kwh = max(0.0, max_disch_e - min_disch_e)

        efficiency = round((energy_discharged_kwh / energy_charged_kwh * 100.0), 1) if energy_charged_kwh > 0 else None

        alarms = AlarmCRUD.get_alarms(active_only=False)
        alarms_in_period = [a for a in alarms if a["first_seen"] >= start_t]

        return {
            "period_days": days,
            "data_points": len(history),
            "start_time": start_t,
            "end_time": time.time(),
            "voltage": {
                "min": min(voltages) if voltages else None,
                "max": max(voltages) if voltages else None,
                "avg": round(sum(voltages) / len(voltages), 1) if voltages else None,
            },
            "temperature": {
                "min": min(temperatures) if temperatures else None,
                "max": max(temperatures) if temperatures else None,
                "avg": round(sum(temperatures) / len(temperatures), 1) if temperatures else None,
            },
            "soc": {
                "min": min(socs) if socs else None,
                "max": max(socs) if socs else None,
                "avg": round(sum(socs) / len(socs), 1) if socs else None,
            },
            "energy": {
                "charged_kwh": round(energy_charged_kwh, 2),
                "discharged_kwh": round(energy_discharged_kwh, 2),
                "round_trip_efficiency_pct": efficiency,
            },
            "alarms": {
                "total_events": len(alarms_in_period),
                "critical_count": sum(1 for a in alarms_in_period if a["severity"].lower() == "critical"),
                "major_count": sum(1 for a in alarms_in_period if a["severity"].lower() == "major"),
                "warning_count": sum(1 for a in alarms_in_period if a["severity"].lower() == "warning"),
            }
        }

    @staticmethod
    def export_telemetry_csv(limit: int = 1000) -> str:
        rows = TelemetryCRUD.query_history(limit=limit)
        if not rows:
            return "timestamp,iso_time,soc,soh,total_voltage,current,power,temperature,min_cell_v,max_cell_v,delta_v,status\n"

        output = io.StringIO()
        fieldnames = [
            "timestamp", "iso_time", "device_id", "is_simulation", "soc", "soh",
            "total_voltage", "current", "power", "temperature", "min_cell_voltage",
            "max_cell_voltage", "cell_voltage_delta", "bms_status", "active_alarms_count"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            row_copy = dict(r)
            row_copy["iso_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["timestamp"]))
            writer.writerow(row_copy)
        return output.getvalue()

    @staticmethod
    def export_audit_log_csv(limit: int = 500) -> str:
        rows = AuditCRUD.get_audit_trail(limit=limit)
        output = io.StringIO()
        fieldnames = [
            "id", "timestamp", "iso_time", "user_role", "action", "parameter_name",
            "parameter_address", "previous_value", "requested_value", "status", "read_back_value", "details"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            row_copy = dict(r)
            row_copy["iso_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["timestamp"]))
            writer.writerow(row_copy)
        return output.getvalue()

    @staticmethod
    def backup_database(destination_path: Optional[str] = None) -> str:
        """Create a safe SQLite online backup."""
        if not destination_path:
            ts = time.strftime("%Y%m%d_%H%M%S")
            destination_path = str(DEFAULT_DB_PATH.parent / f"huawei_bms_backup_{ts}.db")

        src_conn = get_db_connection()
        dst_conn = sqlite3.connect(destination_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        logger.info("Database backup created at %s", destination_path)
        return destination_path
