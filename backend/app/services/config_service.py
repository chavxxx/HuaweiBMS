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

# Strict Allowlist of Verified Modbus Writable Parameters (Huawei ESS / LUNA2000 / EMS B1)
ALLOWLIST_WRITABLE_ADDRESSES = {
    47081: "Grid Max Charge Power Setting",
    47083: "Grid Max Discharge Power Setting",
    47085: "End-of-Discharge SOC Cutoff",
    47086: "End-of-Charge SOC Cutoff",
}


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
            # Strictly protect physical hardware
            msg = (
                "Hardware Safety Lockout: Parameter writes are permanently disabled on physical Huawei ESM Telecom batteries. "
                "The 47000-range registers belong to residential solar inverters (SUN2000/LUNA2000) and are invalid on ESM telecom modules. "
                "Physical hardware operates strictly in Read-Only mode to protect live battery cells."
            )
            add_step(8, "Hardware Safety Lockout", "FAILED", msg)
            AuditCRUD.record_entry({
                "user_role": user_role,
                "action": "HARDWARE_WRITE_BLOCKED",
                "parameter_name": reg.name,
                "parameter_address": address,
                "previous_value": prev_val,
                "requested_value": new_value,
                "status": "REJECTED",
                "details": msg
            })
            return GuardedWriteResult(False, address, reg.name, prev_val, new_value, None, msg, steps)

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
