# Huawei EMS B1 & ESS Modbus Register Map Reference

## 1. Authoritative Specification Background
This application adheres strictly to the documented **Huawei Solar Inverter & Residential Energy Storage System (ESS) Modbus Interface Definitions** (V3.0 & V5.0) and documented Huawei SmartLogger Modbus specifications.

> [!CAUTION]
> **Zero Fabrication Policy:**
> This software does NOT fabricate or guess register addresses, commands, or scaling factors. Any register not present in the verified database is treated as unverified and is strictly blocked from write access.

---

## 2. Huawei Modbus Conventions

1. **Byte and Word Ordering:**
   - Standard Modbus Big-Endian: Most Significant Byte (MSB) first, followed by Least Significant Byte (LSB).
   - 32-bit registers (e.g., Power in W, Cumulative Energy in kWh) are stored in two contiguous 16-bit registers:
     - Word 1 (lower address) = High 16 bits
     - Word 2 (higher address) = Low 16 bits
2. **Sentinel Values (Unavailable / Unmeasured Telemetry):**
   - `0xFFFF` (16-bit unsigned) = Invalid / Sensor Disconnected
   - `0x7FFF` / `-32768` (16-bit signed) = Invalid / Unmeasured
   - `0xFFFFFFFF` (32-bit unsigned) = Invalid / Counter Reset
   - `0x7FFFFFFF` / `-2147483648` (32-bit signed) = Invalid
   - The application parses these sentinels as `N/A` rather than falsely displaying zero or arbitrary measurements.
3. **Signed Current Convention:**
   - **Positive values (+):** Battery is **discharging** (power flowing out of the battery to inverter/loads).
   - **Negative values (-):** Battery is **charging** (power flowing from grid/PV into the battery).

---

## 3. Core Documented Telemetry Registers

| Register Address | Name | Function Code | Data Type | Scaling | Unit | Access Mode | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **30000** | Device Model | 0x03 | String (15 reg) | 1.0 | — | Read-Only | BMS Model ASCII string |
| **30015** | Serial Number | 0x03 | String (10 reg) | 1.0 | — | Read-Only | Hardware serial number |
| **30025** | Firmware Version | 0x03 | String (10 reg) | 1.0 | — | Read-Only | Master BMS software version |
| **37000** | BMS Running Status | 0x03 | uint16 | 1.0 | — | Read-Only | 0: Offline, 1: Standby, 2: Running, 3: Fault, 4: Sleep |
| **37001** | Working Mode | 0x03 | uint16 | 1.0 | — | Read-Only | 0: None, 1: Forced, 2: TOU, 3: Fixed, 4: Self-consumption |
| **37002** | Battery Bus Voltage | 0x03 | uint16 | ÷ 10.0 | V | Read-Only | Total pack terminal DC voltage |
| **37003** | Battery Bus Current | 0x03 | int16 | ÷ 10.0 | A | Read-Only | Signed current (+ discharge, - charge) |
| **37004** | Charge/Discharge Power | 0x03 | int32 | ÷ 1000.0 | kW | Read-Only | Total active DC power |
| **37007** | Max Charge Power Limit | 0x03 | uint32 | ÷ 1000.0 | kW | Read-Only | Hardware maximum charging limit |
| **37009** | Max Discharge Power Limit | 0x03 | uint32 | ÷ 1000.0 | kW | Read-Only | Hardware maximum discharging limit |
| **37014** | State of Charge (SOC) | 0x03 | uint16 | ÷ 10.0 | % | Read-Only | Overall battery percentage (0.0% - 100.0%) |
| **37015** | State of Health (SOH) | 0x03 | uint16 | ÷ 10.0 | % | Read-Only | Battery cell health percentage |
| **37022** | Cumulative Charge Energy | 0x03 | uint32 | ÷ 100.0 | kWh | Read-Only | Total lifetime charged kWh |
| **37024** | Cumulative Discharge Energy | 0x03 | uint32 | ÷ 100.0 | kWh | Read-Only | Total lifetime discharged kWh |
| **37026** | Battery Temperature | 0x03 | int16 | ÷ 10.0 | °C | Read-Only | BMS pack thermal sensor |
| **37027** | Online Modules Count | 0x03 | uint16 | 1.0 | modules | Read-Only | Connected subordinate battery packs |
| **37705** | Module 1 Max Cell Voltage | 0x03 | uint16 | ÷ 1000.0 | V | Read-Only | Highest cell voltage (1 mV resolution) |
| **37706** | Module 1 Min Cell Voltage | 0x03 | uint16 | ÷ 1000.0 | V | Read-Only | Lowest cell voltage (1 mV resolution) |
| **37707** | Module 1 Max Cell Temp | 0x03 | int16 | ÷ 10.0 | °C | Read-Only | Highest measured cell temperature |
| **37708** | Module 1 Min Cell Temp | 0x03 | int16 | ÷ 10.0 | °C | Read-Only | Lowest measured cell temperature |

---

## 4. Allowlisted Writable Configuration Parameters

| Address | Parameter Name | Function Code | Data Type | Range | Unit | Safety Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **47081** | Grid Max Charge Power Setting | 0x06 / 0x10 | uint32 | [0 .. 10000] | W | Read-back verify holding 47081 |
| **47083** | Grid Max Discharge Power Setting | 0x06 / 0x10 | uint32 | [0 .. 10000] | W | Read-back verify holding 47083 |
| **47085** | End-of-Discharge SOC Cutoff | 0x06 | uint16 (0.1%) | [0.0 .. 20.0] | % | Read-back verify holding 47085 |
| **47086** | End-of-Charge SOC Cutoff | 0x06 | uint16 (0.1%) | [90.0 .. 100.0] | % | Read-back verify holding 47086 |

All other addresses are strictly read-only or restricted from write commands.
