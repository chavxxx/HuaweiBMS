"""Register Map Definition and Dynamic Value Encoder/Decoder.

Supports uint16, int16, uint32, int32, string, bitfield, float32,
custom scaling, byte order conversion, validation bounds, and metadata.
"""

import csv
import json
import struct
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union


class DataType(str, Enum):
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    FLOAT32 = "float32"
    STRING = "string"
    BITFIELD = "bitfield"


class ByteOrder(str, Enum):
    BIG_ENDIAN = "BigEndian"          # Standard Modbus & Huawei (AB CD)
    LITTLE_ENDIAN = "LittleEndian"    # (DC BA)
    WORD_SWAP = "WordSwap"            # (CD AB)


class AccessMode(str, Enum):
    READ_ONLY = "read_only"
    WRITABLE = "writable"
    RESTRICTED = "restricted"


@dataclass
class RegisterDefinition:
    name: str
    address: int
    function_code: int = 3  # 3 = Holding, 4 = Input
    data_type: DataType = DataType.UINT16
    length_registers: int = 1
    byte_order: ByteOrder = ByteOrder.BIG_ENDIAN
    scaling_multiplier: float = 1.0
    scaling_divisor: float = 1.0
    unit: str = ""
    access_mode: AccessMode = AccessMode.READ_ONLY
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    source_doc: str = "Undocumented / User Imported"
    supported_models: list[str] = field(default_factory=lambda: ["Huawei EMS B1"])
    verification_procedure: str = "Read-back verification"
    category: str = "general"  # telemetry, electrical, cell, alarm, parameter
    is_undocumented: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["data_type"] = self.data_type.value
        d["byte_order"] = self.byte_order.value
        d["access_mode"] = self.access_mode.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisterDefinition":
        return cls(
            name=str(data.get("name", "Unknown")),
            address=int(data.get("address", 0)),
            function_code=int(data.get("function_code", 3)),
            data_type=DataType(data.get("data_type", "uint16")),
            length_registers=int(data.get("length_registers", 1)),
            byte_order=ByteOrder(data.get("byte_order", "BigEndian")),
            scaling_multiplier=float(data.get("scaling_multiplier", 1.0)),
            scaling_divisor=float(data.get("scaling_divisor", 1.0)),
            unit=str(data.get("unit", "")),
            access_mode=AccessMode(data.get("access_mode", "read_only")),
            min_value=float(data["min_value"]) if data.get("min_value") is not None else None,
            max_value=float(data["max_value"]) if data.get("max_value") is not None else None,
            description=str(data.get("description", "")),
            source_doc=str(data.get("source_doc", "Undocumented")),
            supported_models=list(data.get("supported_models", ["Huawei EMS B1"])),
            verification_procedure=str(data.get("verification_procedure", "Read-back verification")),
            category=str(data.get("category", "general")),
            is_undocumented=bool(data.get("is_undocumented", False)),
        )


class RegisterDatabase:
    """In-memory searchable registry with import/export capabilities."""

    def __init__(self):
        self._registers: dict[int, RegisterDefinition] = {}

    def register(self, reg: RegisterDefinition) -> None:
        self._registers[reg.address] = reg

    def get(self, address: int) -> Optional[RegisterDefinition]:
        return self._registers.get(address)

    def list_all(self) -> list[RegisterDefinition]:
        return sorted(self._registers.values(), key=lambda r: r.address)

    def count(self) -> int:
        return len(self._registers)

    def clear(self) -> None:
        self._registers.clear()

    def filter(self, category: Optional[str] = None, access_mode: Optional[AccessMode] = None) -> list[RegisterDefinition]:
        results = self.list_all()
        if category:
            results = [r for r in results if r.category.lower() == category.lower()]
        if access_mode:
            results = [r for r in results if r.access_mode == access_mode]
        return results

    def import_from_json(self, json_data: Union[str, bytes, list[dict[str, Any]]]) -> int:
        """Import registers from JSON string or list."""
        if isinstance(json_data, (str, bytes)):
            items = json.loads(json_data)
        else:
            items = json_data
        count = 0
        for item in items:
            reg = RegisterDefinition.from_dict(item)
            self.register(reg)
            count += 1
        return count

    def import_from_csv(self, csv_content: str) -> int:
        """Import registers from CSV formatted text."""
        reader = csv.DictReader(csv_content.splitlines())
        count = 0
        for row in reader:
            if not row.get("address"):
                continue
            # Parse address (supports decimal and hex like 0x7530)
            raw_addr = row["address"].strip()
            address = int(raw_addr, 16) if raw_addr.lower().startswith("0x") else int(raw_addr)
            reg = RegisterDefinition(
                name=row.get("name", f"Reg_{address}"),
                address=address,
                function_code=int(row.get("function_code", 3)),
                data_type=DataType(row.get("data_type", "uint16").strip().lower()),
                length_registers=int(row.get("length_registers", 1)),
                byte_order=ByteOrder(row.get("byte_order", "BigEndian")),
                scaling_multiplier=float(row.get("scaling_multiplier", 1.0)),
                scaling_divisor=float(row.get("scaling_divisor", 1.0)),
                unit=row.get("unit", ""),
                access_mode=AccessMode(row.get("access_mode", "read_only").strip().lower()),
                min_value=float(row["min_value"]) if row.get("min_value") else None,
                max_value=float(row["max_value"]) if row.get("max_value") else None,
                description=row.get("description", ""),
                source_doc=row.get("source_doc", "CSV Import"),
                category=row.get("category", "general"),
                is_undocumented=bool(row.get("is_undocumented", False) in ("true", "1", True)),
            )
            self.register(reg)
            count += 1
        return count

    def export_to_json(self) -> str:
        return json.dumps([r.to_dict() for r in self.list_all()], indent=2)

    def export_to_csv(self) -> str:
        fields = [
            "name", "address", "function_code", "data_type", "length_registers",
            "byte_order", "scaling_multiplier", "scaling_divisor", "unit",
            "access_mode", "min_value", "max_value", "category", "description",
            "source_doc", "verification_procedure"
        ]
        lines = [",".join(fields)]
        for r in self.list_all():
            vals = [
                f'"{r.name}"',
                str(r.address),
                str(r.function_code),
                r.data_type.value,
                str(r.length_registers),
                r.byte_order.value,
                str(r.scaling_multiplier),
                str(r.scaling_divisor),
                f'"{r.unit}"',
                r.access_mode.value,
                str(r.min_value or ""),
                str(r.max_value or ""),
                r.category,
                f'"{r.description.replace(chr(34), chr(39))}"',
                f'"{r.source_doc.replace(chr(34), chr(39))}"',
                f'"{r.verification_procedure}"',
            ]
            lines.append(",".join(vals))
        return "\n".join(lines)


# --- Decoding and Encoding Engine ---

def decode_register_value(
    raw_registers: list[int],
    definition: RegisterDefinition
) -> tuple[Any, str]:
    """Decode raw 16-bit register words into an engineering value and formatted string."""
    if not raw_registers:
        return None, "N/A"

    data_type = definition.data_type
    byte_order = definition.byte_order
    raw_bytes = bytearray()

    for word in raw_registers:
        raw_bytes.extend(struct.pack(">H", word & 0xFFFF))

    # Handle byte / word reordering
    if len(raw_registers) == 2 and byte_order == ByteOrder.WORD_SWAP:
        # Swap high word and low word
        raw_bytes = raw_bytes[2:4] + raw_bytes[0:2]
    elif byte_order == ByteOrder.LITTLE_ENDIAN:
        raw_bytes.reverse()

    raw_val: Any = None

    if data_type == DataType.UINT16:
        raw_val = struct.unpack(">H", raw_bytes[:2])[0]
        # Check for Huawei special "Unavailable" or "Invalid" sentinel values (0xFFFF)
        if raw_val == 0xFFFF:
            return None, "N/A"
        scaled = (raw_val * definition.scaling_multiplier) / definition.scaling_divisor
        val_str = f"{scaled:.2f}".rstrip("0").rstrip(".") if isinstance(scaled, float) else str(scaled)
        return scaled, f"{val_str} {definition.unit}".strip()

    elif data_type == DataType.INT16:
        raw_val = struct.unpack(">h", raw_bytes[:2])[0]
        # Check sentinel (0x7FFF or -32768)
        if raw_val in (-32768, 0x7FFF):
            return None, "N/A"
        scaled = (raw_val * definition.scaling_multiplier) / definition.scaling_divisor
        val_str = f"{scaled:.2f}".rstrip("0").rstrip(".") if isinstance(scaled, float) else str(scaled)
        return scaled, f"{val_str} {definition.unit}".strip()

    elif data_type == DataType.UINT32:
        if len(raw_bytes) < 4:
            return None, "N/A"
        raw_val = struct.unpack(">I", raw_bytes[:4])[0]
        if raw_val == 0xFFFFFFFF:
            return None, "N/A"
        scaled = (raw_val * definition.scaling_multiplier) / definition.scaling_divisor
        val_str = f"{scaled:.3f}".rstrip("0").rstrip(".") if isinstance(scaled, float) else str(scaled)
        return scaled, f"{val_str} {definition.unit}".strip()

    elif data_type == DataType.INT32:
        if len(raw_bytes) < 4:
            return None, "N/A"
        raw_val = struct.unpack(">i", raw_bytes[:4])[0]
        if raw_val in (-2147483648, 0x7FFFFFFF):
            return None, "N/A"
        scaled = (raw_val * definition.scaling_multiplier) / definition.scaling_divisor
        val_str = f"{scaled:.3f}".rstrip("0").rstrip(".") if isinstance(scaled, float) else str(scaled)
        return scaled, f"{val_str} {definition.unit}".strip()

    elif data_type == DataType.FLOAT32:
        if len(raw_bytes) < 4:
            return None, "N/A"
        raw_val = struct.unpack(">f", raw_bytes[:4])[0]
        scaled = (raw_val * definition.scaling_multiplier) / definition.scaling_divisor
        return scaled, f"{scaled:.2f} {definition.unit}".strip()

    elif data_type == DataType.STRING:
        # Filter printable ASCII bytes, strip null terminators
        chars = []
        for b in raw_bytes:
            if b == 0:
                break
            if 32 <= b <= 126:
                chars.append(chr(b))
        text = "".join(chars).strip()
        return text, text or "N/A"

    elif data_type == DataType.BITFIELD:
        raw_val = struct.unpack(">H", raw_bytes[:2])[0]
        bits = [bool(raw_val & (1 << i)) for i in range(16)]
        return bits, f"0x{raw_val:04X}"

    return None, "N/A"


def encode_register_value(
    engineering_value: Union[int, float, str],
    definition: RegisterDefinition
) -> list[int]:
    """Convert an engineering value into raw 16-bit register words according to definition.

    Enforces min/max boundaries and data type constraints.
    """
    if definition.access_mode != AccessMode.WRITABLE:
        raise PermissionError(f"Register '{definition.name}' ({definition.address}) is not writable (mode: {definition.access_mode.value})")

    if definition.is_undocumented:
        raise PermissionError(f"Cannot write to undocumented register '{definition.name}' ({definition.address})")

    data_type = definition.data_type

    if data_type in (DataType.UINT16, DataType.INT16, DataType.UINT32, DataType.INT32, DataType.FLOAT32):
        num_val = float(engineering_value)
        # Bounds validation
        if definition.min_value is not None and num_val < definition.min_value:
            raise ValueError(f"Value {num_val} is below allowed minimum {definition.min_value} {definition.unit}")
        if definition.max_value is not None and num_val > definition.max_value:
            raise ValueError(f"Value {num_val} is above allowed maximum {definition.max_value} {definition.unit}")

        # Reverse scaling: raw = (val * divisor) / multiplier
        raw_num = (num_val * definition.scaling_divisor) / definition.scaling_multiplier

        if data_type == DataType.UINT16:
            int_val = int(round(raw_num))
            if not (0 <= int_val <= 0xFFFF):
                raise ValueError(f"Calculated raw value {int_val} out of 16-bit range")
            return [int_val]

        elif data_type == DataType.INT16:
            int_val = int(round(raw_num))
            if not (-32768 <= int_val <= 32767):
                raise ValueError(f"Calculated raw value {int_val} out of signed 16-bit range")
            packed = struct.pack(">h", int_val)
            return list(struct.unpack(">H", packed))

        elif data_type == DataType.UINT32:
            int_val = int(round(raw_num))
            if not (0 <= int_val <= 0xFFFFFFFF):
                raise ValueError(f"Calculated raw value {int_val} out of 32-bit range")
            packed = struct.pack(">I", int_val)
            w1, w2 = struct.unpack(">HH", packed)
            if definition.byte_order == ByteOrder.WORD_SWAP:
                return [w2, w1]
            return [w1, w2]

        elif data_type == DataType.INT32:
            int_val = int(round(raw_num))
            packed = struct.pack(">i", int_val)
            w1, w2 = struct.unpack(">HH", packed)
            if definition.byte_order == ByteOrder.WORD_SWAP:
                return [w2, w1]
            return [w1, w2]

    raise NotImplementedError(f"Encoding not supported for data type {data_type.value}")
