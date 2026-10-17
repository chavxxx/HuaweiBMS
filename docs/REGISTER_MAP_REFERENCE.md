# Huawei ESM Telecom Series & EMS Battery Modbus Register Map Reference

## 1. Protocol Architecture & Device Distinction

> [!IMPORTANT]
> **CRITICAL PROTOCOL CLARIFICATION:**
> There are two completely distinct families of Huawei battery systems. They do **NOT** share register maps:
> 
> 1. **Huawei ESM Telecom Lithium Series (ESM-4805B1, ESM-48100B1, ESM-48150B1 BoostLi):**
>    - **Target Hardware for this Application.**
>    - **Physical Interface:** RS485 half-duplex (GND, A+, B−), typically via FTDI / USB-to-RS485 adapter.
>    - **Default Settings:** 9600 baud, 8 data bits, no parity, 1 stop bit (9600 8N1).
>    - **Slave Address:** Slave ID `214` (`0xD6`) for standalone/master, or IDs `1` to `16` for banked modules.
>    - **Register Layout:** Base addresses sit in **`0 – 74`**, **`257 – 278`**, **`513 – 540`**, and **`768 – 838`**.
>    - **Write Protection:** Strictly Read-Only on physical hardware. Writes to `47000` ranges are invalid and disabled.
> 
> 2. **Huawei Residential / Commercial Solar ESS (LUNA2000 / SUN2000 Inverter):**
>    - Telemetry sits at `37000 – 37708`, and writable inverter parameters sit at `47081 – 47086`.
>    - **These addresses belong exclusively to Solar Inverters and will return "Not Readable" / "Illegal Data Address" (Modbus Exception 0x02) on ESM Telecom modules.**
>    - The application maintains this map *only* for the optional virtual inverter simulator mode.

---

## 2. Huawei ESM Telecom Lithium Register Map (Verified Hardware)

### Module 1 / Master Battery Pack (Registers 0 – 74 / 0x0000 – 0x004A)

| Register Address | Hex | Parameter Name | Function Code | Data Type | Scaling | Unit | Description / Verified Telemetry |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **0** | `0x0000` | Busbar Voltage | `0x03` | uint16 | 0.01 | V | Total DC Busbar voltage measured at module terminals (e.g. `0x14EC` = 53.56 V) |
| **1** | `0x0001` | Battery Terminal Voltage | `0x03` | uint16 | 0.01 | V | Internal cell-string sum voltage (e.g. `0x14EB` = 53.55 V) |
| **2** | `0x0002` | Battery Current | `0x03` | int16 | 0.01 | A | Signed current: `+` = Charging, `-` = Discharging, `0` = Float/Idle |
| **3** | `0x0003` | State of Charge (SOC) | `0x03` | uint16 | 1.0 | % | Module State of Charge percentage (e.g. `0x0062` = 98%) |
| **4** | `0x0004` | State of Health (SOH) | `0x03` | uint16 | 1.0 | % | Module State of Health percentage (e.g. `0x0064` = 100%) |
| **5** | `0x0005` | Ambient Temperature | `0x03` | int16 | 1.0 | °C | External ambient temperature sensor |
| **6** | `0x0006` | BMS Board Temperature | `0x03` | int16 | 1.0 | °C | Internal BMS controller thermal sensor (e.g. `0x001B` = 27 °C) |
| **10** | `0x000A` | Online Module Status | `0x03` | uint16 | 1.0 | — | Online / Communication health status (1 = Normal) |
| **11** | `0x000B` | System Alarm Bitmask | `0x03` | uint16 | Bitfield | — | Hardware alarm flags (Overvoltage, Undervoltage, Overtemp, Faults) |
| **12** | `0x000C` | Operating Mode | `0x03` | uint16 | 1.0 | — | 0: Offline, 1: Running, 2: Standby/Float, 3: Fault |
| **14** | `0x000E` | Charge/Discharge Permission | `0x03` | uint16 | Bitfield | — | Bit 0: Charge Permitted, Bit 1: Discharge Permitted |
| **24 – 31** | `0x0018 – 0x001F` | Cell Temperature Sensors 1–8 | `0x03` | int16 | 1.0 | °C | Thermal sensors distributed across the 16 battery cells |
| **34** | `0x0022` | Cell 1 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 1 voltage (1 mV resolution, e.g. `0x0D0C` = 3.340 V) |
| **35** | `0x0023` | Cell 2 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 2 voltage (e.g. `0x0D0D` = 3.341 V) |
| **36** | `0x0024` | Cell 3 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 3 voltage (e.g. `0x0D0C` = 3.340 V) |
| **37** | `0x0025` | Cell 4 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 4 voltage (e.g. `0x0D0E` = 3.342 V) |
| **38** | `0x0026` | Cell 5 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 5 voltage (e.g. `0x0D0D` = 3.341 V) |
| **39** | `0x0027` | Cell 6 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 6 voltage (e.g. `0x0D0C` = 3.340 V) |
| **40** | `0x0028` | Cell 7 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 7 voltage (e.g. `0x0D0E` = 3.342 V) |
| **41** | `0x0029` | Cell 8 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 8 voltage (e.g. `0x0D0D` = 3.341 V) |
| **42** | `0x002A` | Cell 9 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 9 voltage (e.g. `0x0D0C` = 3.340 V) |
| **43** | `0x002B` | Cell 10 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 10 voltage (e.g. `0x0D0D` = 3.341 V) |
| **44** | `0x002C` | Cell 11 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 11 voltage (e.g. `0x0D0E` = 3.342 V) |
| **45** | `0x002D` | Cell 12 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 12 voltage (e.g. `0x0D0C` = 3.340 V) |
| **46** | `0x002E` | Cell 13 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 13 voltage (e.g. `0x0D0D` = 3.341 V) |
| **47** | `0x002F` | Cell 14 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 14 voltage (e.g. `0x0D0E` = 3.342 V) |
| **48** | `0x0030` | Cell 15 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 15 voltage (e.g. `0x0D0C` = 3.340 V) |
| **49** | `0x0031` | Cell 16 Voltage | `0x03` | uint16 | 0.001 | V | Individual Cell 16 voltage (e.g. `0x0D0D` = 3.341 V) |
| **70 – 74** | `0x0046 – 0x004A` | Energy & Lifetime Statistics | `0x03` | uint32 | 0.1 | kWh | Cumulative Charge and Discharge energy counters |

---

### Module 2, 3, and 4 Bank Ranges

When multiple ESM modules are connected in parallel or daisy-chained on the RS485 communication bus:
- **Module 2 Block (`257 – 278` / `0x0101 – 0x0116`):** Secondary module voltage, current, cell strings, and thermal array.
- **Module 3 Block (`513 – 540` / `0x0201 – 0x021C`):** Tertiary module pack telemetry and alarms.
- **Module 4 & System Parameters (`768 – 838` / `0x0300 – 0x0346`):** Bank aggregate parameters, busbar status, total capacity, and system alarm consolidation.

---

## 3. Write Safety Notice for Live Battery Banks

> [!CAUTION]
> **WRITE FUNCTIONS ARE LOCKED ON PHYSICAL ESM BATTERIES:**
> - Writing to registers in the `47000` range will either fail with `Modbus Exception 0x02 (Illegal Data Address)` or could potentially target undocumented vendor control registers.
> - **DO NOT ATTEMPT TO WRITE `47081 – 47086` TO A LIVE ESM BATTERY BANK.**
> - The application enforces a **Strict Read-Only Guard** on all physical serial connections to ensure battery safety.
