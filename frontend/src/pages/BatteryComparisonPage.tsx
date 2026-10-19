import React, { useEffect, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownToLine,
  BarChart3,
  Battery,
  BatteryCharging,
  CheckCircle2,
  Clock,
  Columns3,
  Database,
  ExternalLink,
  Eye,
  FileSpreadsheet,
  FileText,
  History,
  Layers,
  Lock,
  Plus,
  Radio,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Trash2,
  Unlock,
  Zap,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../services/api'
import type {
  BatteryDetailItem,
  FleetOutlier,
  FleetSummary,
  MultiBatteryAuditResponse,
  PageId,
  SavedAuditItem,
  UserRole,
} from '../types'

interface BatteryComparisonPageProps {
  userRole: UserRole
  activeSlaveId: number
  onSelectBattery: (slaveId: number) => void
  onNavigatePage: (page: PageId) => void
}

export const BatteryComparisonPage: React.FC<BatteryComparisonPageProps> = ({
  userRole,
  activeSlaveId,
  onSelectBattery,
  onNavigatePage,
}) => {
  const [loading, setLoading] = useState(false)
  const [auditData, setAuditData] = useState<MultiBatteryAuditResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards')

  // Scanner modal state
  const [scannerOpen, setScannerOpen] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState<any | null>(null)
  const [candidateInput, setCandidateInput] = useState('1, 2, 3, 4, 214, 215')
  const [newSlaveId, setNewSlaveId] = useState<number>(5)
  const [newBatteryName, setNewBatteryName] = useState<string>('')

  // History modal state
  const [historyOpen, setHistoryOpen] = useState(false)
  const [savedAudits, setSavedAudits] = useState<SavedAuditItem[]>([])
  const [loadingAudits, setLoadingAudits] = useState(false)

  const fetchFleetReadout = async () => {
    setLoading(true)
    setError(null)
    setSaveSuccessMsg(null)
    try {
      const data = await api.readAllBatteries()
      setAuditData(data)
    } catch (err: any) {
      setError(err.message || 'Failed to read all batteries from bus')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFleetReadout()
  }, [])

  const handleSaveAudit = async () => {
    try {
      const res = await api.saveFleetAudit(userRole, 'Operator manual comparison snapshot')
      setSaveSuccessMsg(res.message)
      setTimeout(() => setSaveSuccessMsg(null), 5000)
    } catch (err: any) {
      setError(err.message || 'Failed to save fleet audit snapshot')
    }
  }

  const handleOpenScanner = () => {
    setScannerOpen(true)
    setScanResult(null)
  }

  const handleRunScan = async () => {
    setScanning(true)
    try {
      const ids = candidateInput
        .split(',')
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => !isNaN(n) && n > 0 && n <= 247)
      const res = await api.scanBus(ids.length > 0 ? ids : undefined)
      setScanResult(res)
      // Refresh fleet
      fetchFleetReadout()
    } catch (err: any) {
      setError(err.message || 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const handleAddManualBattery = async () => {
    if (!newSlaveId || newSlaveId <= 0 || newSlaveId > 247) return
    try {
      await api.addBattery(newSlaveId, newBatteryName || `Battery #${newSlaveId}`)
      setNewBatteryName('')
      setNewSlaveId((prev) => prev + 1)
      await fetchFleetReadout()
    } catch (err: any) {
      setError(err.message || 'Failed to add battery')
    }
  }

  const handleRemoveBattery = async (slaveId: number) => {
    if (!window.confirm(`Remove Battery #${slaveId} from the monitoring list?`)) return
    try {
      await api.removeBattery(slaveId)
      await fetchFleetReadout()
    } catch (err: any) {
      setError(err.message || 'Failed to remove battery')
    }
  }

  const handleOpenHistory = async () => {
    setHistoryOpen(true)
    setLoadingAudits(true)
    try {
      const res = await api.listSavedAudits(30)
      setSavedAudits(res.audits || [])
    } catch {
      // ignore
    } finally {
      setLoadingAudits(false)
    }
  }

  const handleLoadAudit = async (auditId: number) => {
    try {
      setLoading(true)
      const audit = await api.getSavedAudit(auditId)
      if (audit && audit.audit_data) {
        setAuditData({
          timestamp: audit.timestamp,
          summary: audit.summary,
          batteries: audit.audit_data,
          is_simulation: false,
          active_slave_id: activeSlaveId,
        })
        setHistoryOpen(false)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load audit snapshot')
    } finally {
      setLoading(false)
    }
  }

  const summary: FleetSummary | undefined = auditData?.summary
  const batteries: BatteryDetailItem[] = auditData?.batteries || []

  // Prepare chart datasets
  const chartData = batteries.map((b) => ({
    name: b.name.replace('Battery #', 'B#'),
    soc: b.soc,
    soh: b.soh,
    delta_mv: b.cell_voltage_delta_mv,
    current: Math.abs(b.current),
    voltage: b.total_voltage,
  }))

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono text-xs">
      {/* Top Banner / Actions Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2.5">
            <Columns3 className="w-5 h-5 text-cyan-400" />
            <span>Battery Fleet Comparison & Capability Matrix</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
              Multi-Battery RS485
            </span>
          </h2>
          <p className="text-xs text-slate-400 font-sans mt-1">
            Compare voltages, current sharing, cell delta V, SOC/SOH, and writeable capabilities across all connected Huawei battery packs.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={fetchFleetReadout}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white rounded-lg font-bold transition flex items-center gap-2 border border-cyan-800/60"
            title="Perform fresh readout of all connected batteries"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Reading Fleet...' : 'Read All Batteries'}</span>
          </button>

          <button
            onClick={handleSaveAudit}
            disabled={loading || batteries.length === 0}
            className="px-3.5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-bold transition flex items-center gap-2 shadow-lg shadow-cyan-900/20"
            title="Save full audit snapshot to SQLite database"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Snapshot</span>
          </button>

          <div className="flex items-center bg-slate-800 border border-slate-700 rounded-lg p-0.5">
            <a
              href="/api/batteries/export/csv"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 hover:bg-slate-700 text-slate-300 hover:text-white rounded flex items-center gap-1.5 transition"
              title="Download fleet comparison as CSV"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span>CSV</span>
            </a>
            <span className="text-slate-600">|</span>
            <a
              href="/api/batteries/export/json"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 hover:bg-slate-700 text-slate-300 hover:text-white rounded flex items-center gap-1.5 transition"
              title="Download fleet comparison as JSON"
            >
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>JSON</span>
            </a>
          </div>

          <button
            onClick={handleOpenScanner}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-medium transition flex items-center gap-1.5 border border-slate-700"
            title="Scan RS485 bus or add battery address"
          >
            <Search className="w-3.5 h-3.5 text-cyan-400" />
            <span>Bus Scanner</span>
          </button>

          <button
            onClick={handleOpenHistory}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg font-medium transition flex items-center gap-1.5 border border-slate-700"
            title="View saved past fleet audit snapshots"
          >
            <History className="w-3.5 h-3.5 text-amber-400" />
            <span>Saved Audits</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {saveSuccessMsg && (
        <div className="p-3 bg-emerald-950/70 border border-emerald-600 rounded-xl text-emerald-300 text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-950/70 border border-rose-600 rounded-xl text-rose-300 text-xs font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Fleet Outlier Alerts Banner */}
      {summary?.outliers && summary.outliers.length > 0 && (
        <div className="p-4 bg-amber-950/40 border border-amber-600/60 rounded-2xl space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Fleet Imbalance & Outlier Detection ({summary.outliers.length} Noticed)</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono">
            {summary.outliers.map((o: FleetOutlier, idx: number) => (
              <div
                key={idx}
                className="bg-slate-900/80 p-2.5 rounded-lg border border-amber-800/60 flex items-start justify-between gap-2"
              >
                <div>
                  <span className="font-bold text-slate-200">{o.battery_name}: </span>
                  <span className="text-amber-200/90">{o.message}</span>
                </div>
                <button
                  onClick={() => {
                    onSelectBattery(o.slave_id)
                    onNavigatePage('dashboard')
                  }}
                  className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded text-[10px] shrink-0 font-bold"
                >
                  Inspect
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fleet Aggregate Metrics Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1">
            <span className="text-slate-400 text-[11px] block">Total Bank Energy</span>
            <div className="text-lg font-bold text-slate-100 flex items-baseline gap-1">
              <span>{summary.total_energy_kwh}</span>
              <span className="text-xs text-slate-400 font-normal">kWh</span>
            </div>
            <span className="text-[10px] text-cyan-400 block font-mono">
              {summary.total_capacity_ah} Ah ({summary.online_count} packs)
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1">
            <span className="text-slate-400 text-[11px] block">Net Bank Current</span>
            <div className={`text-lg font-bold flex items-baseline gap-1 ${
              summary.total_current_a < 0 ? 'text-emerald-400' : (summary.total_current_a > 0 ? 'text-amber-400' : 'text-slate-200')
            }`}>
              <span>{summary.total_current_a}</span>
              <span className="text-xs font-normal">A</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-mono">
              Net: {summary.total_power_kw} kW
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1">
            <span className="text-slate-400 text-[11px] block">Average Bank SOC</span>
            <div className="text-lg font-bold text-cyan-400 flex items-baseline gap-1">
              <span>{summary.avg_soc}</span>
              <span className="text-xs font-normal">%</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-mono">
              Spread: {summary.soc_divergence}% ({summary.min_soc}% - {summary.max_soc}%)
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1">
            <span className="text-slate-400 text-[11px] block">Bank Health (SOH)</span>
            <div className="text-lg font-bold text-slate-100 flex items-baseline gap-1">
              <span>{summary.avg_soh}</span>
              <span className="text-xs text-slate-400 font-normal">%</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-mono">
              Lowest Pack: {summary.min_soh}%
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1">
            <span className="text-slate-400 text-[11px] block">Max Cell Delta V</span>
            <div className={`text-lg font-bold flex items-baseline gap-1 ${
              summary.max_cell_delta_mv > 30.0 ? 'text-amber-400' : 'text-emerald-400'
            }`}>
              <span>{summary.max_cell_delta_mv}</span>
              <span className="text-xs font-normal">mV</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-mono">
              {summary.max_cell_delta_mv <= 30.0 ? 'Balanced (<30mV)' : 'Elevated Spread'}
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1">
            <span className="text-slate-400 text-[11px] block">Bank Temperature</span>
            <div className="text-lg font-bold text-slate-100 flex items-baseline gap-1">
              <span>{summary.max_temperature_c}</span>
              <span className="text-xs text-slate-400 font-normal">°C</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-mono">
              Alarms: {summary.total_alarms} Active
            </span>
          </div>
        </div>
      )}

      {/* Visual Comparison Charts */}
      {batteries.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Chart 1: SOC and SOH Comparison */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-slate-200 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                <span>SOC (%) & SOH (%) Comparison</span>
              </span>
              <span className="text-[11px] text-slate-400">Parallel Bank</span>
            </div>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                  <YAxis domain={[50, 100]} stroke="#94a3b8" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                  <Bar dataKey="soc" name="State of Charge (%)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="soh" name="State of Health (%)" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Cell Delta V & Current Sharing */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-slate-200 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Cell Delta V (mV) & String Current (A)</span>
              </span>
              <span className="text-[11px] text-slate-400">Balance & Sharing</span>
            </div>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                  <Bar dataKey="delta_mv" name="Cell Delta (mV)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="current" name="Magnitude Current |A|" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* View Mode Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-300 font-bold">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Connected Batteries ({batteries.length} Packs)</span>
        </div>

        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode('cards')}
            className={`px-3 py-1 rounded text-xs font-mono font-medium transition ${
              viewMode === 'cards'
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Comparative Cards
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1 rounded text-xs font-mono font-medium transition ${
              viewMode === 'table'
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Detailed Matrix Table
          </button>
        </div>
      </div>

      {/* Comparative Cards View */}
      {viewMode === 'cards' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {batteries.map((b) => {
            const isCurrentActive = b.slave_id === activeSlaveId
            const isLocked = b.parameters?.gyroscope_anti_theft_locked
            const isImbalanced = b.cell_voltage_delta_mv > 30.0

            return (
              <div
                key={b.slave_id}
                className={`bg-slate-900 border rounded-2xl p-5 space-y-4 shadow-xl transition relative flex flex-col justify-between ${
                  isCurrentActive
                    ? 'border-cyan-400 ring-1 ring-cyan-500/40 shadow-cyan-950/40'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                {/* Card Header */}
                <div>
                  <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-100 text-sm">{b.name}</span>
                        {isCurrentActive && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-700 font-bold">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {b.model} · <span className="text-slate-300">{b.serial_number}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        FW: {b.firmware_version ?? '—'} · BL: {b.bootloader_version ?? '—'} · {b.mfg_date ?? '—'}
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800 font-bold">
                        ID: {b.slave_id}
                      </span>
                    </div>
                  </div>

                  {/* SOC & SOH Hero */}
                  <div className="pt-3 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">State of Charge (SOC):</span>
                      <span className="font-bold text-cyan-400 text-sm">{b.soc}%</span>
                    </div>
                    {/* SOC progress bar */}
                    <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                      <div
                        className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(0, b.soc))}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <span className="text-slate-400">Health (SOH):</span>
                      <span className="font-bold text-emerald-400">{b.soh}%</span>
                    </div>
                  </div>

                  {/* Electrical Metrics Grid */}
                  <div className="grid grid-cols-2 gap-2 pt-3 text-xs border-t border-slate-800/80 mt-3 font-mono">
                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/60">
                      <span className="text-[10px] text-slate-400 block">Pack Voltage</span>
                      <span className="font-bold text-slate-100">
                        {b.total_voltage} V
                        {b.bus_delta_v !== undefined && (
                          <span className="text-[9px] text-cyan-400 ml-1">
                            ({b.bus_delta_v > 0 ? '+' : ''}{b.bus_delta_v}V)
                          </span>
                        )}
                      </span>
                    </div>

                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/60">
                      <span className="text-[10px] text-slate-400 block">String Current</span>
                      <span className={`font-bold ${b.current < 0 ? 'text-emerald-400' : 'text-slate-100'}`}>
                        {b.current} A
                      </span>
                    </div>

                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/60">
                      <span className="text-[10px] text-slate-400 block">Cell Delta V</span>
                      <span className={`font-bold ${isImbalanced ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {b.cell_voltage_delta_mv} mV
                      </span>
                    </div>

                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/60">
                      <span className="text-[10px] text-slate-400 block">Max Temp</span>
                      <span className="font-bold text-slate-100">{b.max_cell_temp ?? b.temperature} °C</span>
                    </div>
                  </div>

                  {/* Capability & Lock Badges */}
                  <div className="pt-3 space-y-1.5 text-[11px] font-mono">
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Anti-Theft Lock:</span>
                      {isLocked ? (
                        <span className="flex items-center gap-1 text-rose-400 font-bold">
                          <Lock className="w-3 h-3" />
                          <span>LOCKED</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-emerald-400">
                          <Unlock className="w-3 h-3" />
                          <span>UNLOCKED</span>
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-slate-400">
                      <span>Rated Capacity:</span>
                      <span className="text-slate-200 font-bold">
                        {b.rated_capacity_ah ?? 150} Ah
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-400">
                      <span>Lifetime Discharged:</span>
                      <span className="text-cyan-300 font-bold">
                        {b.discharged_capacity_ah !== undefined ? `${b.discharged_capacity_ah.toLocaleString()} Ah` : '—'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-400">
                      <span>Equiv Full Cycles:</span>
                      <span className="text-slate-200 font-bold">
                        {b.equivalent_full_cycles !== undefined ? `${b.equivalent_full_cycles} cyc` : `${b.cycle_count} ev`}
                        <span className="text-[10px] text-slate-500 font-normal ml-1">({b.cycle_count} ev)</span>
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-400">
                      <span>Charge Limit:</span>
                      <span className="text-slate-200 font-bold">
                        {b.parameters?.charge_limit_a ?? 50.0} A ({b.parameters?.charge_limit_c ?? 0.5}C)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <button
                    onClick={() => {
                      onSelectBattery(b.slave_id)
                      onNavigatePage('dashboard')
                    }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                      isCurrentActive
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/60'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>{isCurrentActive ? 'Active View' : 'Focus Battery'}</span>
                  </button>

                  <button
                    onClick={() => {
                      onSelectBattery(b.slave_id)
                      onNavigatePage('cells')
                    }}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
                    title="View 16 individual cells"
                  >
                    <BatteryCharging className="w-3.5 h-3.5 text-cyan-400" />
                  </button>

                  <button
                    onClick={() => {
                      onSelectBattery(b.slave_id)
                      onNavigatePage('configuration')
                    }}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
                    title="Configure battery parameters & unlock wizard"
                  >
                    <Sliders className="w-3.5 h-3.5 text-blue-400" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Detailed Multi-Battery Matrix Table View */}
      {viewMode === 'table' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">Battery</th>
                  <th className="py-3 px-3">Slave ID</th>
                  <th className="py-3 px-3">Model / Version</th>
                  <th className="py-3 px-3">Serial / Barcode</th>
                  <th className="py-3 px-3 text-right">SOC (%)</th>
                  <th className="py-3 px-3 text-right">SOH (%)</th>
                  <th className="py-3 px-3 text-right">Rated Cap</th>
                  <th className="py-3 px-3 text-right">Pack V (Δ Bus)</th>
                  <th className="py-3 px-3 text-right">Current</th>
                  <th className="py-3 px-3 text-right">Power</th>
                  <th className="py-3 px-3 text-right">Delta V</th>
                  <th className="py-3 px-3 text-right">Min/Max Cell</th>
                  <th className="py-3 px-3 text-right">Max Temp</th>
                  <th className="py-3 px-3 text-right">Discharged Ah</th>
                  <th className="py-3 px-3 text-right">Equiv Cycles</th>
                  <th className="py-3 px-3">Lock Status</th>
                  <th className="py-3 px-3 text-right">Charge Limit</th>
                  <th className="py-3 px-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {batteries.map((b) => {
                  const isCurrentActive = b.slave_id === activeSlaveId
                  const isLocked = b.parameters?.gyroscope_anti_theft_locked

                  return (
                    <tr
                      key={b.slave_id}
                      className={`hover:bg-slate-800/40 transition ${
                        isCurrentActive ? 'bg-cyan-950/20 font-semibold' : ''
                      }`}
                    >
                      <td className="py-3 px-4 flex items-center gap-2">
                        <span className="text-slate-100 font-bold">{b.name}</span>
                        {isCurrentActive && (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-700">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-300 font-bold">{b.slave_id}</td>
                      <td className="py-3 px-3 text-slate-300">
                        <div>{b.model}</div>
                        <div className="text-[9px] text-slate-500">
                          FW: {b.firmware_version ?? '—'} · BL: {b.bootloader_version ?? '—'}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-400">{b.serial_number}</td>
                      <td className="py-3 px-3 text-right text-cyan-400 font-bold">{b.soc}%</td>
                      <td className="py-3 px-3 text-right text-emerald-400 font-bold">{b.soh}%</td>
                      <td className="py-3 px-3 text-right text-slate-200 font-bold">{b.rated_capacity_ah ?? 150} Ah</td>
                      <td className="py-3 px-3 text-right text-slate-200">
                        {b.total_voltage} V
                        {b.bus_delta_v !== undefined && (
                          <span className="text-[9px] text-cyan-400 ml-1">
                            ({b.bus_delta_v > 0 ? '+' : ''}{b.bus_delta_v}V)
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right text-slate-200">{b.current} A</td>
                      <td className="py-3 px-3 text-right text-slate-400">{b.power} kW</td>
                      <td className={`py-3 px-3 text-right font-bold ${
                        b.cell_voltage_delta_mv > 30.0 ? 'text-amber-400' : 'text-emerald-400'
                      }`}>
                        {b.cell_voltage_delta_mv} mV
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        {b.min_cell_voltage} - {b.max_cell_voltage} V
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        {b.max_cell_temp ?? b.temperature} °C
                      </td>
                      <td className="py-3 px-3 text-right text-cyan-300 font-bold">
                        {b.discharged_capacity_ah !== undefined ? `${b.discharged_capacity_ah.toLocaleString()} Ah` : '—'}
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        {b.equivalent_full_cycles !== undefined ? (
                          <span>
                            {b.equivalent_full_cycles} cyc
                            <span className="text-[9px] text-slate-500 block">({b.cycle_count} ev)</span>
                          </span>
                        ) : (
                          `${b.cycle_count} ev`
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {isLocked ? (
                          <span className="text-rose-400 font-bold flex items-center gap-1">
                            <Lock className="w-3 h-3" /> Locked
                          </span>
                        ) : (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <Unlock className="w-3 h-3" /> Unlocked
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        {b.parameters?.charge_limit_a ?? 50.0} A
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => {
                            onSelectBattery(b.slave_id)
                            onNavigatePage('dashboard')
                          }}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded font-bold text-xs"
                        >
                          Focus
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bus Scanner & Add Battery Modal */}
      {scannerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden font-mono text-xs">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
              <div className="flex items-center gap-2.5 font-bold text-slate-100 text-sm">
                <Search className="w-4 h-4 text-cyan-400" />
                <span>RS485 Modbus Bus Scanner & Address Manager</span>
              </div>
              <button
                onClick={() => setScannerOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Scan Candidates Box */}
              <div className="space-y-2">
                <label className="text-slate-300 font-bold block">
                  Scan Candidate Slave IDs (Comma-separated):
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={candidateInput}
                    onChange={(e) => setCandidateInput(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                    placeholder="e.g. 1, 2, 3, 4, 214, 215"
                  />
                  <button
                    onClick={handleRunScan}
                    disabled={scanning}
                    className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-bold flex items-center gap-2 transition"
                  >
                    <Search className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
                    <span>{scanning ? 'Scanning...' : 'Scan Bus'}</span>
                  </button>
                </div>
                <span className="text-[10px] text-slate-500">
                  Default presets: Slave IDs 1-16 (standard daisy-chain) or 214-220 (Huawei factory DIP defaults).
                </span>
              </div>

              {/* Scan Results */}
              {scanResult && (
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex justify-between items-center text-slate-300 font-bold">
                    <span>Scan Completed</span>
                    <span className="text-cyan-400 font-bold">
                      {scanResult.discovered_count} Batteries Detected
                    </span>
                  </div>
                  <div className="space-y-1 max-h-36 overflow-y-auto">
                    {scanResult.discovered?.map((d: any) => (
                      <div
                        key={d.slave_id}
                        className="flex items-center justify-between p-2 rounded bg-slate-900 text-slate-200 border border-slate-800/80"
                      >
                        <span className="font-bold">Slave ID: {d.slave_id}</span>
                        <span className="text-slate-400">{d.model}</span>
                        <span className="text-emerald-400">{d.latency_ms} ms</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Manual Add Battery Section */}
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <span className="text-slate-300 font-bold block">Add Battery Address Manually:</span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-500 block mb-1">Slave ID (1-247)</label>
                    <input
                      type="number"
                      min={1}
                      max={247}
                      value={newSlaveId}
                      onChange={(e) => setNewSlaveId(parseInt(e.target.value, 10))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 block mb-1">Battery Label / Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Battery #5 (Backup)"
                      value={newBatteryName}
                      onChange={(e) => setNewBatteryName(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-100"
                    />
                  </div>
                </div>
                <button
                  onClick={handleAddManualBattery}
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg font-bold transition flex items-center justify-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Battery to Fleet</span>
                </button>
              </div>
            </div>

            <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end">
              <button
                onClick={() => setScannerOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Saved Audits History Modal */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden font-mono text-xs max-h-[85vh] flex flex-col">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
              <div className="flex items-center gap-2.5 font-bold text-slate-100 text-sm">
                <History className="w-4 h-4 text-amber-400" />
                <span>Historical Fleet Audit Snapshots</span>
              </div>
              <button
                onClick={() => setHistoryOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-3 flex-1">
              {loadingAudits ? (
                <div className="text-center py-8 text-slate-400">Loading saved snapshots...</div>
              ) : savedAudits.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  No saved fleet audit snapshots found in database.
                </div>
              ) : (
                savedAudits.map((a) => (
                  <div
                    key={a.id}
                    className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-3 hover:border-slate-700 transition"
                  >
                    <div>
                      <div className="flex items-center gap-2 font-bold text-slate-200">
                        <span>Audit #{a.id}</span>
                        <span className="text-[10px] text-cyan-400 font-mono">
                          {a.battery_count} Batteries
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{new Date(a.timestamp * 1000).toLocaleString()}</span>
                        <span className="ml-2 text-slate-500">· {a.operator}</span>
                      </div>
                      {a.notes && <div className="text-[10px] text-slate-400 italic mt-1">{a.notes}</div>}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleLoadAudit(a.id)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg font-bold"
                      >
                        Load
                      </button>
                      <button
                        onClick={async () => {
                          if (window.confirm(`Delete audit snapshot #${a.id}?`)) {
                            await api.deleteSavedAudit(a.id)
                            handleOpenHistory()
                          }
                        }}
                        className="p-1.5 text-slate-500 hover:text-rose-400 rounded transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end">
              <button
                onClick={() => setHistoryOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
