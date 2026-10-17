"""Application State Singletons and Initialization."""

import json
from pathlib import Path
from typing import Optional
from .database.db import init_db
from .protocol.register_map import RegisterDatabase
from .serial_comm.serial_client import SerialClient, SerialConfig
from .services.alarm_service import AlarmService
from .services.config_service import ConfigService
from .services.report_service import ReportService
from .services.telemetry_service import TelemetryService
from .simulator.bms_simulator import BMSSimulator


class AppContext:
    def __init__(self):
        # 1. Database
        init_db()

        # 2. Register Database
        self.register_db = RegisterDatabase()
        self._load_default_registers()

        # 3. Simulator
        self.simulator = BMSSimulator()

        # 4. Serial Client
        self.serial_client = SerialClient()

        # 5. Core Services
        self.telemetry_service = TelemetryService(
            serial_client=self.serial_client,
            register_db=self.register_db,
            simulator=self.simulator
        )
        self.config_service = ConfigService(
            serial_client=self.serial_client,
            register_db=self.register_db,
            simulator=self.simulator
        )
        self.alarm_service = AlarmService()
        self.report_service = ReportService()

        # Default settings
        self.settings = {
            "low_soc_threshold": 15.0,
            "high_temp_threshold": 50.0,
            "max_delta_v_mv_threshold": 60.0,
            "telemetry_stale_seconds": 5.0,
            "theme": "dark",
            "retention_days": 30
        }

        # Start telemetry loop (starts in simulation mode by default so UI is immediately active)
        self.telemetry_service.start_polling()

    def _load_default_registers(self):
        import sys
        data_candidates = []
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            data_candidates.extend([
                meipass / "app" / "data",
                meipass / "data",
                meipass / "backend" / "app" / "data",
            ])
        data_candidates.append(Path(__file__).resolve().parent / "data")

        data_dir = None
        for d in data_candidates:
            if d.exists() and ((d / "huawei_esm_48150b1.json").exists() or (d / "huawei_ems_4805b1.json").exists()):
                data_dir = d
                break
        if not data_dir:
            data_dir = data_candidates[-1]

        # Load verified Huawei ESM-48150B1 / EMS-4805B1 physical registers
        esm_b1_path = data_dir / "huawei_esm_48150b1.json"
        if esm_b1_path.exists():
            self.register_db.import_from_json(esm_b1_path.read_text(encoding="utf-8"))
        else:
            ems_b1_path = data_dir / "huawei_ems_4805b1.json"
            if ems_b1_path.exists():
                self.register_db.import_from_json(ems_b1_path.read_text(encoding="utf-8"))
            else:
                ems_a1_path = data_dir / "huawei_ems_4805a1.json"
                if ems_a1_path.exists():
                    self.register_db.import_from_json(ems_a1_path.read_text(encoding="utf-8"))

        # Also load standard Huawei residential/commercial reference
        luna_path = data_dir / "huawei_luna2000_bms_v3.json"
        if luna_path.exists():
            self.register_db.import_from_json(luna_path.read_text(encoding="utf-8"))


# Global singleton instance
app_context = AppContext()
