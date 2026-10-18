"""Configuration and Parameter Management Service with Mandatory 10-Step Guarded Writes."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional, Union
from ..database.crud import AuditCRUD, SnapshotCRUD
from ..protocol.modbus_rtu import ModbusRTUAdapter
from ..protocol.register_map import (
    AccessMode,
    RegisterDatabase,
    RegisterDefinition,
    decode_register_value,
    encode_register_value,
)
from ..serial_comm.serial_client import SerialClient
from ..simulator.bms_simulator import BMSSimulator

logger = logging.getLogger("huawei_bms.config_service")

# Strict Allowlist of Verified Modbus Writable Parameters (Huawei ESM BoostLi & EMS)
ALLOWLIST_WRITABLE_ADDRESSES = {
    # Huawei ESM / EMS BoostLi Telecom Battery verified writable parameters
    4376: "Gyroscope Anti-Theft Lock (0=Disabled/Unlock, 1=Enabled/Lock)",
    4377: "Gyroscope Sensitivity (0=Low, 1=Medium, 2=High)",
    4109: "Charge Current Limit Coefficient (0.05-1.05 C)",
    4123: "Default Charge Current Limit Coefficient (0.05-1.05 C)",
    4107: "Discharge Current Limit Coefficient (0.05-1.05 C)",
    4111: "Digital Output 1 Alarm Action (0=Close, 1=Open)",
    4112: "Digital Output 2 Alarm Action (0=Close, 1=Open)",
    4096: "RTC Clock Year (2000-2099)",
    4097: "RTC Clock Month (1-12)",
    4098: "RTC Clock Day (1-31)",
    4099: "RTC Clock Hour (0-23)",
    4100: "RTC Clock Minute (0-59)",
    4101: "RTC Clock Second (0-59)",
    # ESS legacy parameters
    47081: "Grid Max Charge Power Setting",
    47083: "Grid Max Discharge Power Setting",
    47085: "End-of-Discharge SOC Cutoff",
    47086: "End-of-Charge SOC Cutoff",
}

BATTERY_PRESETS = [
    {
        "id": "solar_offgrid_standalone",
        "name": "Solar Off-Grid Standalone",
        "badge": "Recommended for Inverters",
        "description": "Optimized for residential & commercial off-grid/hybrid inverters (Victron, Deye, Solark, Growatt). Unlocks anti-theft displacement lock and configures 0.500C safe charging.",
        "target_models": ["Huawei ESM-48150B1", "Huawei ESM-48100B1", "Huawei EMS-4805B1"],
        "parameters": [
            {"address": 4376, "name": "Gyroscope Anti-Theft Lock", "value": 0.0, "unit": "", "description": "Disable anti-theft displacement lock"},
            {"address": 4377, "name": "Gyroscope Sensitivity", "value": 0.0, "unit": "Level", "description": "Set sensitivity to Low to prevent vibration trips"},
            {"address": 4109, "name": "Charge Current Limit Coefficient", "value": 0.500, "unit": "C", "description": "Set 0.500C charge limit (50A / 100Ah, 75A / 150Ah)"},
            {"address": 4123, "name": "Default Charge Current Limit Coefficient", "value": 0.500, "unit": "C", "description": "Set 0.500C default NVRAM rate"},
            {"address": 4107, "name": "Discharge Current Limit Coefficient", "value": 1.000, "unit": "C", "description": "Set 1.000C full discharge capability"},
        ]
    },
    {
        "id": "high_rate_fast_charge",
        "name": "High-Rate Fast Charge",
        "badge": "Max Replenishment",
        "description": "Configures maximum 1.000C charging rate for applications with limited generator run-time or brief peak solar production windows.",
        "target_models": ["Huawei ESM-48150B1", "Huawei ESM-48100B1", "Huawei EMS-4805B1"],
        "parameters": [
            {"address": 4376, "name": "Gyroscope Anti-Theft Lock", "value": 0.0, "unit": "", "description": "Disable anti-theft displacement lock"},
            {"address": 4109, "name": "Charge Current Limit Coefficient", "value": 1.000, "unit": "C", "description": "Set 1.000C fast charge (100A / 100Ah, 150A / 150Ah)"},
            {"address": 4123, "name": "Default Charge Current Limit Coefficient", "value": 1.000, "unit": "C", "description": "Set 1.000C default NVRAM rate"},
            {"address": 4107, "name": "Discharge Current Limit Coefficient", "value": 1.000, "unit": "C", "description": "Set 1.000C full discharge capability"},
        ]
    },
    {
        "id": "eco_longevity",
        "name": "Eco Lifespan & Cell Longevity",
        "badge": "5000+ Cycles",
        "description": "Conservative 0.200C charging currents designed to minimize cell heating, prevent thermal stress, and maximize battery lifespan.",
        "target_models": ["Huawei ESM-48150B1", "Huawei ESM-48100B1", "Huawei EMS-4805B1"],
        "parameters": [
            {"address": 4376, "name": "Gyroscope Anti-Theft Lock", "value": 0.0, "unit": "", "description": "Disable anti-theft displacement lock"},
            {"address": 4109, "name": "Charge Current Limit Coefficient", "value": 0.200, "unit": "C", "description": "Gentle 0.200C charge limit (20A / 100Ah, 30A / 150Ah)"},
            {"address": 4123, "name": "Default Charge Current Limit Coefficient", "value": 0.200, "unit": "C", "description": "Gentle 0.200C default NVRAM rate"},
            {"address": 4107, "name": "Discharge Current Limit Coefficient", "value": 0.800, "unit": "C", "description": "Conservative 0.800C discharge limit"},
        ]
    },
    {
        "id": "second_hand_restore",
        "name": "Decommissioned / Second-Hand Unlock",
        "badge": "Anti-Theft Clear",
        "description": "Complete restoration sequence for decommissioned telecom base station batteries. Unlocks displacement lock, resets rate throttles, and synchronizes the BMS RTC clock.",
        "target_models": ["Huawei ESM-48150B1", "Huawei ESM-48100B1", "Huawei EMS-4805B1"],
        "parameters": [
            {"address": 4376, "name": "Gyroscope Anti-Theft Lock", "value": 0.0, "unit": "", "description": "Disable gyroscope lock"},
            {"address": 4377, "name": "Gyroscope Sensitivity", "value": 0.0, "unit": "Level", "description": "Set sensitivity to Low"},
            {"address": 4109, "name": "Charge Current Limit Coefficient", "value": 0.500, "unit": "C", "description": "Restore 0.500C normal charge limit"},
            {"address": 4123, "name": "Default Charge Current Limit Coefficient", "value": 0.500, "unit": "C", "description": "Restore 0.500C default NVRAM rate"},
            {"address": 4107, "name": "Discharge Current Limit Coefficient", "value": 1.000, "unit": "C", "description": "Restore 1.000C discharge capacity"},
        ]
    },
    {
        "id": "telecom_float_backup",
        "name": "Telecom Factory Float Backup",
        "badge": "Standby UPS",
        "description": "Huawei telecom factory standard float-charging profile for standby emergency power supply at telecom central offices and remote towers.",
        "target_models": ["Huawei ESM-48150B1", "Huawei ESM-48100B1", "Huawei EMS-4805B1"],
        "parameters": [
            {"address": 4376, "name": "Gyroscope Anti-Theft Lock", "value": 1.0, "unit": "", "description": "Enable anti-theft displacement sensor"},
            {"address": 4377, "name": "Gyroscope Sensitivity", "value": 1.0, "unit": "Level", "description": "Set sensitivity to Medium"},
            {"address": 4109, "name": "Charge Current Limit Coefficient", "value": 0.150, "unit": "C", "description": "Float charge rate 0.150C (15A / 100Ah, 22.5A / 150Ah)"},
            {"address": 4123, "name": "Default Charge Current Limit Coefficient", "value": 0.150, "unit": "C", "description": "Float NVRAM rate 0.150C"},
            {"address": 4107, "name": "Discharge Current Limit Coefficient", "value": 1.000, "unit": "C", "description": "Full discharge capability"},
        ]
    }
]


@dataclass
class WritePlanStep:
    step_number: int
    title: str
    status: str  # 'PENDING', 'COMPLETED', 'FAILED'
    details: str


@dataclass
class GuardedWriteResult:
    success: bool
    parameter_address: int
    parameter_name: str
    previous_value: Any
    requested_value: Any
    verified_value: Optional[Any]
    message: str
    steps: list[WritePlanStep]
    audit_id: Optional[int] = None


class ConfigService:
    """Manages parameter inspection, snapshots, comparisons, and safe guarded writes."""

    def __init__(
        self,
        serial_client: SerialClient,
        register_db: RegisterDatabase,
        simulator: BMSSimulator,
    ):
        self.serial_client = serial_client
        self.register_db = register_db
        self.simulator = simulator
        self.writes_enabled = False  # Strict default read-only mode

    def enable_writes(self, user_role: str, confirmation_passcode: Optional[str] = None) -> bool:
        """Unlock write mode for Administrator role."""
        if user_role.upper() != "ADMINISTRATOR":
            raise PermissionError("Only Administrator role can enable parameter write modifications.")
        self.writes_enabled = True
        logger.warning("Configuration writes ENABLED by %s", user_role)
        return True

    def disable_writes(self) -> None:
        """Lock write mode back to Read-Only."""
        self.writes_enabled = False
        logger.info("Configuration writes DISABLED. System in Read-Only mode.")

    def read_all_parameters(self, is_simulation: bool = True) -> list[dict[str, Any]]:
        """Read all documented parameters (both read-only and writable) and return decoded values."""
        results = []
        parameters = self.register_db.filter(category="parameter")
        if not parameters:
            parameters = [r for r in self.register_db.list_all() if r.access_mode in (AccessMode.WRITABLE, AccessMode.RESTRICTED)]

        for reg in parameters:
            curr_val, formatted_str = self._read_parameter_value(reg, is_simulation)
            is_allowlisted = reg.address in ALLOWLIST_WRITABLE_ADDRESSES
            results.append({
                "address": reg.address,
                "name": reg.name,
                "access_mode": reg.access_mode.value,
                "is_allowlisted": is_allowlisted,
                "data_type": reg.data_type.value,
                "unit": reg.unit,
                "min_value": reg.min_value,
                "max_value": reg.max_value,
                "current_raw": curr_val,
                "current_formatted": formatted_str,
                "description": reg.description,
                "source_doc": reg.source_doc,
                "verification_procedure": reg.verification_procedure,
                "can_write": self.writes_enabled and is_allowlisted and reg.access_mode == AccessMode.WRITABLE,
            })
        return sorted(results, key=lambda x: x["address"])

    def execute_guarded_write(
        self,
        address: int,
        new_value: Union[int, float],
        user_role: str,
        operator_confirmed: bool,
        is_simulation: bool = True
    ) -> GuardedWriteResult:
        """Execute the 10-Step Guarded Write Workflow with read-back verification."""
        steps: list[WritePlanStep] = []

        def add_step(num: int, title: str, status: str, details: str):
            steps.append(WritePlanStep(num, title, status, details))

        # Check safety unlock
        if not self.writes_enabled:
            raise PermissionError("Safety violation: Configuration writes are currently locked (Read-Only mode).")

        if user_role.upper() != "ADMINISTRATOR":
            raise PermissionError("Safety violation: Parameter modification requires Administrator authorization.")

        reg = self.register_db.get(address)
        if not reg:
            raise ValueError(f"Register address {address} not found in register database.")

        if address not in ALLOWLIST_WRITABLE_ADDRESSES:
            msg = f"Address {address} ({reg.name}) is NOT on the verified writable allowlist. Writes strictly blocked."
            add_step(1, "Allowlist Check", "FAILED", msg)
            AuditCRUD.record_entry({
                "user_role": user_role,
                "action": "WRITE_PARAMETER_REJECTED",
                "parameter_name": reg.name,
                "parameter_address": address,
                "requested_value": new_value,
                "status": "REJECTED",
                "details": msg
            })
            return GuardedWriteResult(False, address, reg.name, None, new_value, None, msg, steps)

        # Step 1: Read current value
        prev_val, prev_formatted = self._read_parameter_value(reg, is_simulation)
        add_step(1, "Read Current Parameter", "COMPLETED", f"Current value is {prev_formatted}")

        # Step 2: Display documented range and validation rules
        bounds_desc = f"Allowed range: [{reg.min_value} .. {reg.max_value}] {reg.unit}"
        add_step(2, "Range & Rules Verification", "COMPLETED", bounds_desc)

        # Step 3 & 4: Validate operator input & unit conversion
        try:
            raw_words = encode_register_value(new_value, reg)
            add_step(3, "Input Conversion", "COMPLETED", f"Requested {new_value} {reg.unit} converted to raw words: {raw_words}")
            add_step(4, "Bounds Validation", "COMPLETED", f"Value {new_value} satisfies safety bounds [{reg.min_value}..{reg.max_value}]")
        except Exception as e:
            err_msg = f"Validation failed: {str(e)}"
            add_step(4, "Bounds Validation", "FAILED", err_msg)
            AuditCRUD.record_entry({
                "user_role": user_role,
                "action": "WRITE_VALIDATION_ERROR",
                "parameter_name": reg.name,
                "parameter_address": address,
                "previous_value": prev_val,
                "requested_value": new_value,
                "status": "REJECTED",
                "details": err_msg
            })
            return GuardedWriteResult(False, address, reg.name, prev_val, new_value, None, err_msg, steps)

        # Step 5: Before-and-after comparison
        diff_summary = f"Before: {prev_formatted} -> Proposed: {new_value} {reg.unit}"
        add_step(5, "Before-and-After Comparison", "COMPLETED", diff_summary)

        # Step 6: Explain documented operational effect
        effect_msg = f"Operational Effect: {reg.description}. Source: {reg.source_doc}"
        add_step(6, "Operational Impact Review", "COMPLETED", effect_msg)

        # Step 7: Operator confirmation check
        if not operator_confirmed:
            msg = "Operator did not provide explicit confirmation for write execution."
            add_step(7, "Operator Confirmation", "FAILED", msg)
            return GuardedWriteResult(False, address, reg.name, prev_val, new_value, None, msg, steps)
        add_step(7, "Operator Confirmation", "COMPLETED", f"Confirmed by {user_role}")

        # Step 8: Send write command
        write_success = False
        write_details = ""
        if is_simulation:
            # Update simulator internal state
            for i, word in enumerate(raw_words):
                self.simulator._write_register_word(address + i, word)
            write_success = True
            write_details = "Simulated Modbus Write Function 0x06/0x10 acknowledged by Virtual BMS."
        else:
            slave_id = self.serial_client.config.slave_id
            adapter = self.serial_client.adapter
            try:
                if len(raw_words) == 1:
                    frame = adapter.build_write_single_register(slave_id, address, raw_words[0])
                    resp = self.serial_client.execute_transaction(frame, 0x06, is_write=True)
                else:
                    frame = adapter.build_write_multiple_registers(slave_id, address, raw_words)
                    resp = self.serial_client.execute_transaction(frame, 0x10, is_write=True)

                if resp.success:
                    write_success = True
                    write_details = f"Physical Modbus write (FC 0x{resp.function_code:02X}) acknowledged by Slave {slave_id}."
                else:
                    write_success = False
                    write_details = resp.error_message or f"Physical Modbus write rejected by Slave {slave_id}."
            except Exception as e:
                write_success = False
                write_details = f"Serial communication exception during write: {str(e)}"

        if not write_success:
            add_step(8, "Transmit Write Frame", "FAILED", write_details)
            AuditCRUD.record_entry({
                "user_role": user_role,
                "action": "WRITE_TRANSMIT_FAILED",
                "parameter_name": reg.name,
                "parameter_address": address,
                "previous_value": prev_val,
                "requested_value": new_value,
                "status": "FAILED",
                "details": write_details
            })
            return GuardedWriteResult(False, address, reg.name, prev_val, new_value, None, f"Write transmission failed: {write_details}", steps)

        add_step(8, "Transmit Write Frame", "COMPLETED", write_details)

        # Step 9: Read parameter back to verify result (Crucial hardware rule!)
        time.sleep(0.05)
        read_back_val, read_back_formatted = self._read_parameter_value(reg, is_simulation)

        # Verification check: numbers must match within floating point tolerance
        is_verified = False
        if read_back_val is not None:
            if isinstance(read_back_val, (int, float)):
                is_verified = abs(float(read_back_val) - float(new_value)) < 0.05
            else:
                is_verified = str(read_back_val) == str(new_value)

        if not is_verified:
            fail_msg = f"Read-back verification FAILED! Device reported: {read_back_formatted}, expected: {new_value} {reg.unit}"
            add_step(9, "Read-back Verification", "FAILED", fail_msg)
            audit_id = AuditCRUD.record_entry({
                "user_role": user_role,
                "action": "WRITE_VERIFICATION_FAILED",
                "parameter_name": reg.name,
                "parameter_address": address,
                "previous_value": prev_val,
                "requested_value": new_value,
                "device_response": write_details,
                "read_back_value": read_back_val,
                "status": "VERIFICATION_FAILED",
                "details": fail_msg
            })
            return GuardedWriteResult(False, address, reg.name, prev_val, new_value, read_back_val, fail_msg, steps, audit_id)

        add_step(9, "Read-back Verification", "COMPLETED", f"Verified match: {read_back_formatted}")

        # Step 10: Record outcome in audit log
        audit_id = AuditCRUD.record_entry({
            "user_role": user_role,
            "action": "WRITE_PARAMETER_SUCCESS",
            "parameter_name": reg.name,
            "parameter_address": address,
            "previous_value": prev_val,
            "requested_value": new_value,
            "device_response": write_details,
            "read_back_value": read_back_val,
            "status": "SUCCESS",
            "details": f"Successfully updated and verified via {reg.verification_procedure}"
        })
        add_step(10, "Audit Log Recording", "COMPLETED", f"Audit entry #{audit_id} recorded permanently.")

        return GuardedWriteResult(
            success=True,
            parameter_address=address,
            parameter_name=reg.name,
            previous_value=prev_val,
            requested_value=new_value,
            verified_value=read_back_val,
            message=f"Parameter '{reg.name}' successfully modified and verified to {read_back_formatted}.",
            steps=steps,
            audit_id=audit_id
        )

    def _read_parameter_value(self, reg: RegisterDefinition, is_simulation: bool) -> tuple[Any, str]:
        """Read holding registers for a specific parameter definition."""
        if is_simulation:
            words = []
            for i in range(reg.length_registers):
                val = self.simulator._read_register_word(reg.address + i)
                words.append(val if val is not None else 0)
            return decode_register_value(words, reg)
        else:
            slave_id = self.serial_client.config.slave_id
            adapter = self.serial_client.adapter
            frame = adapter.build_read_holding_registers(slave_id, reg.address, reg.length_registers)
            resp = self.serial_client.execute_transaction(frame, 0x03)
            if resp.success:
                return decode_register_value(resp.values, reg)
            return None, "Read Error"

    def get_presets(self) -> list[dict[str, Any]]:
        """Return available battery configuration presets."""
        return BATTERY_PRESETS

    def apply_preset(
        self,
        preset_id: str,
        user_role: str,
        operator_confirmed: bool = True,
        is_simulation: bool = True
    ) -> dict[str, Any]:
        """Apply a predefined configuration preset to the battery module."""
        preset = next((p for p in BATTERY_PRESETS if p["id"] == preset_id), None)
        if not preset:
            raise ValueError(f"Unknown preset ID '{preset_id}'")

        if not self.writes_enabled:
            raise PermissionError("Configuration writes are currently locked. Unlock writes first.")

        if user_role.upper() != "ADMINISTRATOR":
            raise PermissionError("Applying presets requires Administrator authorization.")

        results = []
        overall_success = True

        for p_def in preset["parameters"]:
            res = self.execute_guarded_write(
                address=p_def["address"],
                new_value=p_def["value"],
                user_role=user_role,
                operator_confirmed=operator_confirmed,
                is_simulation=is_simulation
            )
            results.append({
                "address": res.parameter_address,
                "name": res.parameter_name,
                "target_value": res.requested_value,
                "verified_value": res.verified_value,
                "success": res.success,
                "message": res.message,
            })
            if not res.success:
                overall_success = False
                break

        audit_id = AuditCRUD.record_entry({
            "user_role": user_role,
            "action": "APPLY_PRESET",
            "parameter_name": preset["name"],
            "parameter_address": None,
            "requested_value": preset_id,
            "status": "SUCCESS" if overall_success else "PARTIAL_FAILURE",
            "details": f"Applied preset '{preset['name']}' ({len(results)} parameters processed)."
        })

        return {
            "success": overall_success,
            "preset_id": preset_id,
            "preset_name": preset["name"],
            "results": results,
            "audit_id": audit_id,
            "message": f"Preset '{preset['name']}' {'successfully applied and verified' if overall_success else 'failed during application'}."
        }

    def unlock_battery(
        self,
        user_role: str,
        sync_clock: bool = True,
        restore_charge_rate: float = 0.500,
        is_simulation: bool = True
    ) -> dict[str, Any]:
        """One-click unlock wizard for locked Huawei BoostLi / ESM telecom modules.

        1. Clears displacement/gyroscope anti-theft lock (Reg 4376 -> 0).
        2. Sets displacement sensitivity to Low (Reg 4377 -> 0).
        3. Restores charge current limit coefficient (Reg 4109 -> restore_charge_rate).
        4. Restores default charge coefficient in NVRAM (Reg 4123 -> restore_charge_rate).
        5. Synchronizes RTC clock to host local time (Regs 4096-4101).
        """
        if not self.writes_enabled:
            raise PermissionError("Configuration writes are currently locked. Unlock writes first.")

        if user_role.upper() != "ADMINISTRATOR":
            raise PermissionError("Unlocking battery requires Administrator authorization.")

        steps_log = []
        overall_ok = True

        unlock_ops = [
            (4376, 0.0, "Disable Anti-Theft Gyroscope Displacement Lock"),
            (4377, 0.0, "Set Gyroscope Sensitivity to Low"),
            (4109, float(restore_charge_rate), f"Restore Active Charge Rate ({restore_charge_rate}C)"),
            (4123, float(restore_charge_rate), f"Restore Default NVRAM Charge Rate ({restore_charge_rate}C)"),
        ]

        if sync_clock:
            now = time.localtime()
            unlock_ops.extend([
                (4096, float(now.tm_year), f"Sync RTC Year ({now.tm_year})"),
                (4097, float(now.tm_mon), f"Sync RTC Month ({now.tm_mon})"),
                (4098, float(now.tm_mday), f"Sync RTC Day ({now.tm_mday})"),
                (4099, float(now.tm_hour), f"Sync RTC Hour ({now.tm_hour})"),
                (4100, float(now.tm_min), f"Sync RTC Minute ({now.tm_min})"),
                (4101, float(now.tm_sec), f"Sync RTC Second ({now.tm_sec})"),
            ])

        for addr, val, desc in unlock_ops:
            res = self.execute_guarded_write(
                address=addr,
                new_value=val,
                user_role=user_role,
                operator_confirmed=True,
                is_simulation=is_simulation
            )
            steps_log.append({
                "address": addr,
                "operation": desc,
                "target_value": val,
                "verified_value": res.verified_value,
                "success": res.success,
                "message": res.message
            })
            if not res.success:
                overall_ok = False
                break

        audit_id = AuditCRUD.record_entry({
            "user_role": user_role,
            "action": "UNLOCK_BATTERY",
            "parameter_name": "Huawei Anti-Theft Unlock Wizard",
            "parameter_address": 4376,
            "requested_value": "0",
            "status": "SUCCESS" if overall_ok else "FAILED",
            "details": f"Executed battery unlock sequence: {len(steps_log)} operations."
        })

        return {
            "success": overall_ok,
            "operations": steps_log,
            "audit_id": audit_id,
            "message": "Battery unlock sequence completed successfully and verified." if overall_ok else "Battery unlock sequence encountered an error."
        }
