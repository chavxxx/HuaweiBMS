export type UserRole = 'VIEWER' | 'OPERATOR' | 'ADMINISTRATOR'

export type PageId =
  | 'dashboard'
  | 'connect'
  | 'electrical'
  | 'cells'
  | 'alarms'
  | 'configuration'
  | 'config_history'
  | 'trends'
  | 'reports'
  | 'diagnostics'
  | 'registers'
  | 'settings'
  | 'audit'

export interface FreshnessStatus {
  status: 'FRESH' | 'STALE_WARNING' | 'CRITICAL_STALE' | 'DISCONNECTED' | 'AWAITING_DATA'
  label: string
  color: 'green' | 'amber' | 'red' | 'gray' | 'yellow'
  age_seconds: number | null
  is_stale: boolean
}

export interface TelemetryData {
  timestamp: number
  device_model: string
  serial_number: string
  firmware_version: string
  hardware_rev?: string
  mfg_date?: string
  is_simulation: boolean
  identification_verified: boolean
  soc: number | null
  soh: number | null
  total_voltage: number | null
  current: number | null
  power: number | null
  temperature: number | null
  bms_status: number
  operating_state: string
  working_mode: number
  online_modules_count: number
  charge_permission: boolean
  discharge_permission: boolean
  active_alarm_codes: (number | string)[]
  cycle_count?: number | null
  rated_capacity_ah?: number | null
  max_current_limit_a?: number | null
}

export interface ElectricalData {
  timestamp: number
  total_voltage: number | null
  current: number | null
  charge_power: number | null
  discharge_power: number | null
  dc_bus_voltage: number | null
  charge_energy: number | null
  discharge_energy: number | null
  max_charge_power_limit: number | null
  max_discharge_power_limit: number | null
  contactor_state: string
  precharge_state: string
  insulation_resistance_kohm: number | null
  calculated_metrics?: {
    power_is_calculated: boolean
    power_formula: string
  }
}

export interface CellData {
  timestamp: number
  cell_voltages: number[]
  cell_count: number
  min_cell_voltage: number | null
  max_cell_voltage: number | null
  avg_cell_voltage: number | null
  cell_voltage_delta: number | null
  cell_voltage_delta_mv: number | null
  temperatures: number[]
  min_cell_temp: number | null
  max_cell_temp: number | null
  temperature_spread: number | null
  balancing_active: boolean[]
  module_status: string
  module_voltage: number | null
  module_current: number | null
}

export interface AlarmItem {
  code: number
  name: string
  severity: 'Critical' | 'Major' | 'Minor' | 'Warning' | 'Info'
  subsystem: string
  description: string
  corrective_action: string
  first_seen?: number
  last_seen?: number
  is_active?: boolean
}

export interface ParameterItem {
  address: number
  name: string
  access_mode: 'read_only' | 'writable' | 'restricted'
  is_allowlisted: boolean
  data_type: string
  unit: string
  min_value: number | null
  max_value: number | null
  current_raw: any
  current_formatted: string
  description: string
  source_doc: string
  verification_procedure: string
  can_write: boolean
}

export interface SerialPortInfo {
  device: string
  name: string
  description: string
  hwid: string
  vid_hex: string | null
  pid_hex: string | null
  manufacturer: string | null
  is_rs485_candidate: boolean
}

export interface CommStatistics {
  total_requests: number
  total_responses: number
  total_timeouts: number
  total_crc_errors: number
  total_retries: number
  last_latency_ms: number
  average_latency_ms: number
  last_error: string | null
  last_error_time: number | null
  last_success_time: number | null
  bytes_sent: number
  bytes_received: number
}

export interface ProtocolFrame {
  timestamp: number
  direction: 'TX' | 'RX'
  raw_hex: string
  slave_id: number
  function_code: number
  function_name: string
  is_exception: boolean
  exception_code: number | null
  exception_message: string | null
  register_address: number | null
  register_count: number | null
  values: number[]
  crc_valid: boolean
  error: string | null
}

export interface AuditLogEntry {
  id: number
  timestamp: number
  user_role: string
  action: string
  parameter_name: string | null
  parameter_address: number | null
  previous_value: string | null
  requested_value: string | null
  validation_result: string | null
  device_response: string | null
  read_back_value: string | null
  status: string
  details: string | null
}

export interface SnapshotItem {
  id: number
  timestamp: number
  snapshot_name: string
  device_id: string
  author_role: string
  notes: string
  parameters?: Record<string, any>
}
