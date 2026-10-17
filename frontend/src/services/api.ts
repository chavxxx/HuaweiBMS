import type {
  AlarmItem,
  AuditLogEntry,
  CellData,
  ElectricalData,
  FreshnessStatus,
  ParameterItem,
  ProtocolFrame,
  SerialPortInfo,
  SnapshotItem,
  TelemetryData,
} from '../types'

const BASE_URL = ''

export const api = {
  // Ports & Connection
  async listPorts(): Promise<SerialPortInfo[]> {
    const res = await fetch(`${BASE_URL}/api/ports`)
    const data = await res.json()
    return data.ports || []
  },

  async getConnectionStatus(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/ports/status`)
    return res.json()
  },

  async connectPort(config: any): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/ports/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Connection failed')
    }
    return res.json()
  },

  async disconnectPort(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/ports/disconnect`, { method: 'POST' })
    return res.json()
  },

  async toggleSimulation(enabled: boolean): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/ports/toggle-simulation?enabled=${enabled}`, {
      method: 'POST',
    })
    return res.json()
  },

  // Telemetry
  async getLatestTelemetry(): Promise<{
    freshness: FreshnessStatus
    telemetry: TelemetryData
    electrical: ElectricalData
    cells: CellData
  }> {
    const res = await fetch(`${BASE_URL}/api/telemetry/latest`)
    return res.json()
  },

  // Parameters & Configuration
  async getParameters(): Promise<{ writes_enabled: boolean; parameters: ParameterItem[] }> {
    const res = await fetch(`${BASE_URL}/api/config/parameters`)
    return res.json()
  },

  async enableWrites(userRole: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/config/enable-writes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_role: userRole }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to enable writes')
    }
    return res.json()
  },

  async disableWrites(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/config/disable-writes`, { method: 'POST' })
    return res.json()
  },

  async writeParameter(payload: {
    address: number
    new_value: number
    user_role: string
    operator_confirmed: boolean
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/config/write`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Write execution rejected')
    }
    return res.json()
  },

  async listSnapshots(): Promise<SnapshotItem[]> {
    const res = await fetch(`${BASE_URL}/api/config/snapshots`)
    const data = await res.json()
    return data.snapshots || []
  },

  async createSnapshot(name: string, notes: string, authorRole: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/config/snapshots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ snapshot_name: name, notes, author_role: authorRole }),
    })
    return res.json()
  },

  async compareSnapshot(snapshotId: number): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/config/snapshots/compare?snapshot_id=${snapshotId}`, {
      method: 'POST',
    })
    return res.json()
  },

  // Alarms
  async getActiveAlarms(): Promise<AlarmItem[]> {
    const res = await fetch(`${BASE_URL}/api/alarms/active`)
    const data = await res.json()
    return data.active_alarms || []
  },

  async getAlarmHistory(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/api/alarms/history`)
    const data = await res.json()
    return data.history || []
  },

  async simulateInjectAlarm(code: number): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/alarms/simulate-inject?alarm_code=${code}`, {
      method: 'POST',
    })
    return res.json()
  },

  async simulateClearAlarm(code: number): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/alarms/simulate-clear?alarm_code=${code}`, {
      method: 'POST',
    })
    return res.json()
  },

  // Diagnostics
  async getCommDiagnostics(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/diagnostics/comm`)
    return res.json()
  },

  async getProtocolTrace(): Promise<ProtocolFrame[]> {
    const res = await fetch(`${BASE_URL}/api/diagnostics/trace`)
    const data = await res.json()
    return data.trace || []
  },

  async transmitRawFrame(payload: {
    raw_hex: string
    safety_override: boolean
    operator_confirmed: boolean
    user_role: string
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/diagnostics/transmit-raw`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Raw transmission rejected')
    }
    return res.json()
  },

  // History & Reports
  async queryHistory(startTime?: number, endTime?: number, limit = 300): Promise<any[]> {
    let url = `${BASE_URL}/api/history/query?limit=${limit}`
    if (startTime) url += `&start_time=${startTime}`
    if (endTime) url += `&end_time=${endTime}`
    const res = await fetch(url)
    const data = await res.json()
    return data.points || []
  },

  async getReport(days = 7): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/history/report?days=${days}`)
    return res.json()
  },

  async triggerBackup(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/history/backup`, { method: 'POST' })
    return res.json()
  },

  // Registers
  async listRegisters(category?: string): Promise<any[]> {
    const url = category ? `${BASE_URL}/api/registers?category=${category}` : `${BASE_URL}/api/registers`
    const res = await fetch(url)
    const data = await res.json()
    return data.registers || []
  },

  // Audit Logs
  async getAuditLogs(limit = 100): Promise<AuditLogEntry[]> {
    const res = await fetch(`${BASE_URL}/api/audit/logs?limit=${limit}`)
    const data = await res.json()
    return data.logs || []
  },

  // Settings
  async getSettings(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/settings`)
    const data = await res.json()
    return data.settings || {}
  },

  async updateSettings(settings: any): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    })
    return res.json()
  },
}
