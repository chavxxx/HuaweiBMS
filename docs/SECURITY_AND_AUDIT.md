# Security, Guarded Parameter Writes, and Audit Policy

## 1. Safety Principles for Battery Energy Storage Systems (BESS)

High-voltage battery energy storage systems (BESS) pose significant arc-flash, fire, and thermal runaway hazards if misconfigured. This application is architected around strict safety defenses:

1. **Default Read-Only Mode:**
   - On startup, the application always initializes in **Read-Only Mode**.
   - No write command can be dispatched over the RS485 serial bus without explicit operator authentication.
2. **Strict Parameter Allowlist:**
   - Only parameters that have been verified in official documentation and verified safe for user tuning are included on the write allowlist.
   - Any write request directed at undocumented or unverified register addresses is blocked at the core protocol layer.
3. **No Automatic Fault Clearing:**
   - The application **never** automatically resets BMS faults or alarm flags. In a physical battery, faults often indicate dangerous conditions (overvoltage, overtemperature, cell leakage, insulation failure).
4. **Prohibition of Blind Scanning / Command Fuzzing:**
   - The application blocks unrestricted Modbus address scanning and fuzzing loops against live battery hardware.

---

## 2. The 10-Step Guarded Write Workflow

Whenever an authorized Administrator modifies a writable parameter, the system enforces the following sequential steps:

```
[1. Read Current Value]
        │
[2. Range & Rules Verification]
        │
[3. Operator Enters Target Value]
        │
[4. Bounds Validation & Conversion] ──> (Fails if out of range)
        │
[5. Before-and-After Diff Review]
        │
[6. Operational Impact Review]
        │
[7. Operator Explicit Confirmation]
        │
[8. Dispatch Write Frame (0x06 / 0x10)]
        │
[9. Read-Back Verification] ──────────> (Fails if read-back != target)
        │
[10. Record in SQLite Audit Trail]
```

If read-back verification fails, the application flags a **VERIFICATION_FAILED** state and alerts the operator immediately.

---

## 3. Role-Based Access Control (RBAC)

The application provides three operational roles:

| Role | Telemetry Monitoring | View Alarms | Export Reports | Enable Writes | Raw Frame Diagnostics |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Viewer** | Yes | Yes | Yes | No | No |
| **Operator** | Yes | Yes | Yes | No | No |
| **Administrator** | Yes | Yes | Yes | **Yes (Guarded)** | **Yes (Gated)** |

---

## 4. Tamper-Evident Audit Logging

Every write attempt, configuration snapshot, and administrative action is written to the SQLite `audit_log` table:

- **Timestamp:** High-resolution Unix timestamp and ISO-8601 representation.
- **User Role:** Active authenticated role.
- **Action:** e.g., `WRITE_PARAMETER_SUCCESS`, `WRITE_PARAMETER_REJECTED`, `WRITE_VERIFICATION_FAILED`.
- **Parameter Address & Name:** Target Modbus register.
- **Previous Value & Requested Target Value.**
- **Device Response:** Exact response frame or timeout status.
- **Read-Back Verified Value:** Hardware reported confirmation.
- **Final Outcome Status.**

No sensitive passwords or system credentials are ever recorded in the audit trail.
