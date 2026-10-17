"""Alarm and Fault Monitoring Service with Manufacturer Knowledge Base."""

import json
import logging
from pathlib import Path
from typing import Any, Optional
from ..database.crud import AlarmCRUD

logger = logging.getLogger("huawei_bms.alarm_service")


class AlarmService:
    """Manages active alarms, historical faults, code lookups, and operator acknowledgments."""

    def __init__(self, alarm_db_path: Optional[str] = None):
        self._alarm_kb: dict[int, dict[str, Any]] = {}
        self._load_knowledge_base(alarm_db_path)

    def _load_knowledge_base(self, path: Optional[str] = None) -> None:
        file_path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "huawei_bms_alarm_codes.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for item in data:
                    self._alarm_kb[int(item["code"])] = item
                logger.info("Loaded %d Huawei alarm definitions from knowledge base.", len(self._alarm_kb))
            except Exception as e:
                logger.error("Failed to load alarm knowledge base: %s", e)

    def lookup_alarm(self, code: int) -> dict[str, Any]:
        """Lookup alarm code. Unknown codes are explicitly marked as UNKNOWN."""
        if code in self._alarm_kb:
            return dict(self._alarm_kb[code])
        return {
            "code": code,
            "name": f"Unknown Alarm Code (0x{code:04X})",
            "severity": "Warning",
            "subsystem": "Unidentified Subsystem",
            "description": "This fault code is not listed in the verified Huawei EMS B1 alarm database.",
            "corrective_action": "Refer to official Huawei service documentation for unlisted fault code diagnostics."
        }

    def process_active_alarms(self, active_codes: list[int]) -> list[dict[str, Any]]:
        """Process incoming active codes, update database, and return enriched list."""
        enriched = []
        for code in active_codes:
            item = self.lookup_alarm(code)
            AlarmCRUD.upsert_active_alarm(item)
            enriched.append(item)

        AlarmCRUD.mark_cleared_if_absent(active_codes)
        return enriched

    def get_all_alarms(self, active_only: bool = False) -> list[dict[str, Any]]:
        return AlarmCRUD.get_alarms(active_only=active_only)
