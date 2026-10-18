import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Clock,
  Edit3,
  Key,
  Lock,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sliders,
  Sparkles,
  Sun,
  Unlock,
  X,
  Zap,
} from 'lucide-react'
import { GuardedWriteModal } from '../components/GuardedWriteModal'
import { api } from '../services/api'
import type { ParameterItem, PresetItem, UnlockBatteryResult, UserRole } from '../types'

interface ConfigurationPageProps {
  userRole: UserRole
  onNavigateSnapshots: () => void
}

export const ConfigurationPage: React.FC<ConfigurationPageProps> = ({
  userRole,
  onNavigateSnapshots,
}) => {
  const [parameters, setParameters] = useState<ParameterItem[]>([])
  const [presets, setPresets] = useState<PresetItem[]>([])
  const [writesEnabled, setWritesEnabled] = useState(false)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'presets' | 'parameters'>('presets')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Modals state
  const [selectedParam, setSelectedParam] = useState<ParameterItem | null>(null)
  const [snapshotModalOpen, setSnapshotModalOpen] = useState(false)
  const [snapshotName, setSnapshotName] = useState('')
  const [snapshotNotes, setSnapshotNotes] = useState('')

  // Unlock Wizard state
  const [unlockModalOpen, setUnlockModalOpen] = useState(false)
  const [unlockSyncClock, setUnlockSyncClock] = useState(true)
  const [unlockChargeRate, setUnlockChargeRate] = useState(0.500)
  const [unlockConfirmed, setUnlockConfirmed] = useState(false)
  const [unlocking, setUnlocking] = useState(false)
  const [unlockResult, setUnlockResult] = useState<UnlockBatteryResult | null>(null)

  // Preset Apply state
  const [selectedPreset, setSelectedPreset] = useState<PresetItem | null>(null)
  const [presetConfirmed, setPresetConfirmed] = useState(false)
  const [applyingPreset, setApplyingPreset] = useState(false)
  const [presetResult, setPresetResult] = useState<any | null>(null)

  const [feedback, setFeedback] = useState<string | null>(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const [paramData, presetData] = await Promise.all([
        api.getParameters(),
        api.getPresets().catch(() => []),
      ])
      setParameters(paramData.parameters || [])
      setWritesEnabled(paramData.writes_enabled)
      setPresets(presetData || [])
    } catch (e: any) {
      setFeedback(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleToggleWrites = async () => {
    try {
      if (writesEnabled) {
        await api.disableWrites()
        setWritesEnabled(false)
        setFeedback('Configuration writes have been LOCKED. System in Read-Only mode.')
      } else {
        if (userRole !== 'ADMINISTRATOR') {
          setFeedback('Write permission denied: Only Administrator role can enable parameter writes.')
          return
        }
        await api.enableWrites(userRole)
        setWritesEnabled(true)
        setFeedback('Configuration writes are now UNLOCKED for Administrator.')
      }
      await loadData()
    } catch (e: any) {
      setFeedback(e.message)
    }
  }

  const handleSaveSnapshot = async () => {
    if (!snapshotName.trim()) return
    try {
      await api.createSnapshot(snapshotName, snapshotNotes, userRole)
      setFeedback(`Snapshot '${snapshotName}' saved successfully.`)
      setSnapshotModalOpen(false)
      setSnapshotName('')
      setSnapshotNotes('')
    } catch (e: any) {
      setFeedback(e.message)
    }
  }

  const handleExecuteUnlock = async () => {
    if (!unlockConfirmed || unlocking) return
    setUnlocking(true)
    setUnlockResult(null)
    setFeedback(null)
    try {
      const res = await api.unlockBattery({
        user_role: userRole,
        sync_clock: unlockSyncClock,
        restore_charge_rate: unlockChargeRate,
      })
      setUnlockResult(res)
      if (res.success) {
        setFeedback('Battery unlock sequence successfully executed and read-back verified.')
        await loadData()
      } else {
        setFeedback(res.message || 'Battery unlock encountered issues.')
      }
    } catch (e: any) {
      setFeedback(`Battery unlock error: ${e.message}`)
    } finally {
      setUnlocking(false)
    }
  }

  const handleExecutePreset = async () => {
    if (!selectedPreset || !presetConfirmed || applyingPreset) return
    setApplyingPreset(true)
    setPresetResult(null)
    setFeedback(null)
    try {
      const res = await api.applyPreset(selectedPreset.id, userRole)
      setPresetResult(res)
      if (res.success) {
        setFeedback(`Preset '${selectedPreset.name}' applied and verified successfully.`)
        await loadData()
      } else {
        setFeedback(res.message || 'Preset application encountered an error.')
      }
    } catch (e: any) {
      setFeedback(`Preset error: ${e.message}`)
    } finally {
      setApplyingPreset(false)
    }
  }

  const filteredParameters = parameters.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.address.toString().includes(searchQuery) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())

    if (!matchesSearch) return false

    if (categoryFilter === 'anti_theft') {
      return p.address === 4376 || p.address === 4377
    } else if (categoryFilter === 'rates') {
      return p.address === 4109 || p.address === 4123 || p.address === 4107
    } else if (categoryFilter === 'clock') {
      return p.address >= 4096 && p.address <= 4101
    } else if (categoryFilter === 'ess') {
      return p.address >= 47000
    }
    return true
  })

  return (
    <div className="space-y-6">
      {/* Top Header Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <span>Huawei BMS Configuration, Unlock & Presets</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Unlock second-hand modules, apply tailored inverter presets, edit parameters, and record snapshots.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Unlock Wizard Button */}
          <button
            onClick={() => {
              setUnlockResult(null)
              setUnlockConfirmed(false)
              setUnlockModalOpen(true)
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-slate-950 font-bold rounded-lg text-xs font-mono shadow-md transition"
          >
            <Key className="w-3.5 h-3.5" />
            <span>Unlock Battery Wizard</span>
          </button>

          <button
            onClick={() => setSnapshotModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
          >
            <Camera className="w-3.5 h-3.5 text-cyan-400" />
            <span>Save Snapshot</span>
          </button>

          <button
            onClick={onNavigateSnapshots}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
          >
            Snapshot History →
          </button>

          {/* Mode Unlock Button */}
          <button
            onClick={handleToggleWrites}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold font-mono transition border ${
              writesEnabled
                ? 'bg-amber-950/80 hover:bg-amber-900 text-amber-300 border-amber-600 animate-pulse'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
            }`}
          >
            {writesEnabled ? (
              <>
                <Unlock className="w-3.5 h-3.5 text-amber-400" />
                <span>Writes Unlocked</span>
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                <span>Read-Only Mode</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Safety Policy Alert */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-start gap-3 text-xs font-mono">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-slate-300 space-y-1">
          <span className="font-bold text-slate-200">Guarded Modbus RTU Safety Active:</span>
          <p className="text-slate-400 font-sans text-[11px] leading-relaxed">
            All configuration updates execute with strict bounds checking, operator verification, and immediate physical read-back verification (FC 0x03). Unverified or undocumented registers cannot be modified. Writes require Administrator authorization.
          </p>
        </div>
      </div>

      {feedback && (
        <div className="p-3 bg-cyan-950/50 border border-cyan-800 rounded-lg text-cyan-300 text-xs font-mono flex items-center justify-between">
          <span>{feedback}</span>
          <button onClick={() => setFeedback(null)} className="text-cyan-500 hover:text-cyan-300">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Tab Switcher: Presets vs Parameters */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('presets')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-bold transition border-b-2 -mb-px ${
            activeTab === 'presets'
              ? 'border-cyan-400 text-cyan-400 bg-slate-900/60'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Battery Presets ({presets.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('parameters')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-bold transition border-b-2 -mb-px ${
            activeTab === 'parameters'
              ? 'border-cyan-400 text-cyan-400 bg-slate-900/60'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Live Parameters Table ({parameters.length})</span>
        </button>
      </div>

      {/* SECTION 1: PRESETS TAB */}
      {activeTab === 'presets' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400 font-mono">
              Apply pre-validated configurations tailored for off-grid inverters, rapid charging, or second-hand base station restoration.
            </p>
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-xs font-mono transition"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {presets.map((preset) => {
              const isSolar = preset.id === 'solar_offgrid_standalone'
              const isUnlock = preset.id === 'second_hand_restore'
              return (
                <div
                  key={preset.id}
                  className={`bg-slate-900 border rounded-xl p-5 flex flex-col justify-between transition ${
                    isSolar
                      ? 'border-cyan-700/60 shadow-lg shadow-cyan-950/20'
                      : isUnlock
                      ? 'border-amber-700/60 shadow-lg shadow-amber-950/20'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
                        {isSolar ? (
                          <Sun className="w-4 h-4 text-cyan-400" />
                        ) : isUnlock ? (
                          <Key className="w-4 h-4 text-amber-400" />
                        ) : (
                          <Zap className="w-4 h-4 text-emerald-400" />
                        )}
                        <span>{preset.name}</span>
                      </h3>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 shrink-0">
                        {preset.badge}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 leading-relaxed">
                      {preset.description}
                    </p>

                    <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5 space-y-1.5 font-mono text-[11px]">
                      <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                        Configured Parameters ({preset.parameters.length})
                      </div>
                      {preset.parameters.slice(0, 3).map((p) => (
                        <div key={p.address} className="flex justify-between text-slate-300">
                          <span className="truncate max-w-[180px]">{p.name}</span>
                          <span className="font-bold text-cyan-400">
                            {p.value} {p.unit}
                          </span>
                        </div>
                      ))}
                      {preset.parameters.length > 3 && (
                        <div className="text-[10px] text-slate-500 italic">
                          +{preset.parameters.length - 3} more parameters...
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="pt-4 mt-2 border-t border-slate-800 flex items-center justify-between">
                    <div className="text-[10px] text-slate-500 font-mono">
                      Target: ESM / EMS 48V
                    </div>
                    <button
                      onClick={() => {
                        setSelectedPreset(preset)
                        setPresetConfirmed(false)
                        setPresetResult(null)
                      }}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 rounded-lg text-xs font-mono font-semibold transition"
                    >
                      Preview & Apply →
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* SECTION 2: LIVE PARAMETERS TABLE TAB */}
      {activeTab === 'parameters' && (
        <div className="space-y-4">
          {/* Search and Category Filters */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search parameter, address, description..."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center gap-1.5 font-mono text-xs">
              <span className="text-slate-500 text-[11px] mr-1">Filter:</span>
              {[
                { id: 'all', label: 'All' },
                { id: 'anti_theft', label: 'Anti-Theft' },
                { id: 'rates', label: 'Charge/Discharge' },
                { id: 'clock', label: 'RTC Clock' },
                { id: 'ess', label: 'ESS Settings' },
              ].map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setCategoryFilter(cat.id)}
                  className={`px-2.5 py-1 rounded text-[11px] transition ${
                    categoryFilter === cat.id
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-bold'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
                  }`}
                >
                  {cat.label}
                </button>
              ))}

              <button
                onClick={loadData}
                disabled={loading}
                className="flex items-center gap-1 ml-2 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-semibold font-mono transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {/* Parameters Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Address</th>
                    <th className="py-2.5 px-3">Parameter Name</th>
                    <th className="py-2.5 px-3">Current Value</th>
                    <th className="py-2.5 px-3">Allowed Range</th>
                    <th className="py-2.5 px-3">Access Mode</th>
                    <th className="py-2.5 px-3">Allowlist Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredParameters.map((p) => {
                    const isWritable = p.access_mode === 'writable'
                    const canModify =
                      writesEnabled && p.is_allowlisted && isWritable && userRole === 'ADMINISTRATOR'

                    return (
                      <tr key={p.address} className="hover:bg-slate-800/40 text-slate-300">
                        <td className="py-2.5 px-3 font-bold text-cyan-400">
                          {p.address}
                          <span className="text-[10px] text-slate-500 ml-1">
                            (0x{p.address.toString(16).toUpperCase()})
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-semibold text-slate-100">{p.name}</div>
                          <div className="text-[10px] text-slate-500 font-sans truncate max-w-sm">
                            {p.description}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-bold">
                          {p.current_formatted === 'Read Error' ? (
                            <span className="text-rose-400 bg-rose-950/60 border border-rose-800 rounded px-1.5 py-0.5 text-xs">
                              Read Error
                            </span>
                          ) : p.current_formatted?.includes('live') ? (
                            <span className="text-cyan-300">
                              {p.current_formatted}
                            </span>
                          ) : (
                            <span className="text-slate-100">
                              {p.current_formatted || 'N/A'}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">
                          {p.min_value !== null
                            ? `[${p.min_value} .. ${p.max_value}] ${p.unit}`
                            : 'N/A'}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              isWritable
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-700/60'
                                : 'bg-slate-800 text-slate-400 border border-slate-700'
                            }`}
                          >
                            {p.access_mode}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {p.is_allowlisted ? (
                            <span className="text-emerald-400 flex items-center gap-1 font-semibold text-[11px]">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Verified Allowlist
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[10px]">Restricted</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          {isWritable ? (
                            <button
                              onClick={() => setSelectedParam(p)}
                              disabled={!canModify}
                              className={`px-3 py-1 rounded text-xs font-semibold font-mono transition flex items-center gap-1 ml-auto ${
                                canModify
                                  ? 'bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-600 shadow'
                                  : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                              }`}
                            >
                              <Edit3 className="w-3 h-3" />
                              <span>Modify</span>
                            </button>
                          ) : (
                            <span className="text-slate-500 text-[10px] italic">Read-Only</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                  {filteredParameters.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-6 text-center text-slate-500 font-mono">
                        No configuration parameters match the active filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: BATTERY UNLOCK WIZARD */}
      {unlockModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-amber-600/60 rounded-xl shadow-2xl max-w-xl w-full overflow-hidden flex flex-col max-h-[90vh] font-mono text-xs">
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Key className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">
                    Huawei BoostLi / ESM Battery Unlock Wizard
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Clear anti-theft displacement locks, restore throttled charging rates, & sync RTC
                  </p>
                </div>
              </div>
              <button
                onClick={() => setUnlockModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 space-y-4 overflow-y-auto">
              {!writesEnabled && (
                <div className="p-3 bg-amber-950/40 border border-amber-700/60 rounded-lg text-amber-300 text-[11px]">
                  <strong>Notice:</strong> Configuration writes are currently in Read-Only Mode. Please toggle "Writes Unlocked" in the top bar using Administrator credentials before proceeding.
                </div>
              )}

              <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
                <div className="font-bold text-slate-200 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Planned Hardware Unlock Sequence</span>
                </div>
                <div className="text-[11px] text-slate-400 space-y-1 font-sans">
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400 font-mono font-bold">1. Reg 4376 (0x1118):</span>
                    <span>Set Gyroscope Anti-Theft Lock to 0 (Disabled / Unlocked)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400 font-mono font-bold">2. Reg 4377 (0x1119):</span>
                    <span>Set Gyroscope Sensitivity to 0 (Low sensitivity)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400 font-mono font-bold">3. Reg 4109 (0x100D):</span>
                    <span>Restore Active Charge Current Coefficient to {unlockChargeRate}C</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400 font-mono font-bold">4. Reg 4123 (0x101B):</span>
                    <span>Restore Default NVRAM Charge Current Coefficient to {unlockChargeRate}C</span>
                  </div>
                  {unlockSyncClock && (
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-mono font-bold">5. Regs 4096-4101:</span>
                      <span>Synchronize BMS Internal RTC clock to system timestamp</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Options */}
              <div className="space-y-3 pt-1">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">
                    Restored Charge Current Rate:
                  </label>
                  <select
                    value={unlockChargeRate}
                    onChange={(e) => setUnlockChargeRate(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  >
                    <option value={0.200}>0.200 C — Gentle Eco Charge (20A for 100Ah / 30A for 150Ah)</option>
                    <option value={0.500}>0.500 C — Standard Nominal Rate (50A for 100Ah / 75A for 150Ah) [Recommended]</option>
                    <option value={1.000}>1.000 C — Fast Charge Maximum (100A for 100Ah / 150A for 150Ah)</option>
                  </select>
                </div>

                <label className="flex items-center gap-2 text-slate-300 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={unlockSyncClock}
                    onChange={(e) => setUnlockSyncClock(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Synchronize BMS Real-Time Clock (RTC) with host system time</span>
                </label>

                <label className="flex items-center gap-2 text-amber-300 cursor-pointer p-2 bg-amber-950/20 border border-amber-900/60 rounded">
                  <input
                    type="checkbox"
                    checked={unlockConfirmed}
                    onChange={(e) => setUnlockConfirmed(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-amber-500 focus:ring-0"
                  />
                  <span>I confirm this battery is standalone/decommissioned and authorized for unlock</span>
                </label>
              </div>

              {/* Execution Results View */}
              {unlockResult && (
                <div className="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                  <div className="font-bold flex items-center gap-2 text-slate-200">
                    {unlockResult.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                    )}
                    <span>{unlockResult.message}</span>
                  </div>
                  <div className="space-y-1 text-[11px] divide-y divide-slate-800/40">
                    {unlockResult.operations.map((op) => (
                      <div key={op.address} className="pt-1 flex items-center justify-between">
                        <span className="text-slate-400 truncate max-w-xs">{op.operation}</span>
                        <span className={op.success ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                          {op.success ? `Verified (${op.verified_value})` : 'Failed'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="px-5 py-3 border-t border-slate-800 bg-slate-950 flex justify-end gap-2">
              <button
                onClick={() => setUnlockModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
              >
                Close
              </button>
              <button
                onClick={handleExecuteUnlock}
                disabled={!writesEnabled || !unlockConfirmed || unlocking || userRole !== 'ADMINISTRATOR'}
                className="px-4 py-1.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 disabled:opacity-40 text-slate-950 font-bold rounded-lg transition"
              >
                {unlocking ? 'Executing Unlock...' : 'Execute Battery Unlock'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: PRESET PREVIEW & APPLY */}
      {selectedPreset && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-cyan-600/60 rounded-xl shadow-2xl max-w-xl w-full overflow-hidden flex flex-col max-h-[90vh] font-mono text-xs">
            {/* Header */}
            <div className="px-5 py-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <span>Apply Preset: {selectedPreset.name}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                    {selectedPreset.badge}
                  </span>
                </h3>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Review parameter modifications before applying to battery
                </p>
              </div>
              <button
                onClick={() => setSelectedPreset(null)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Comparison Table */}
            <div className="p-5 space-y-4 overflow-y-auto">
              {!writesEnabled && (
                <div className="p-3 bg-amber-950/40 border border-amber-700/60 rounded-lg text-amber-300 text-[11px]">
                  <strong>Notice:</strong> Configuration writes are currently in Read-Only Mode. Please toggle "Writes Unlocked" in the top bar with Administrator role.
                </div>
              )}

              <table className="w-full text-left divide-y divide-slate-800">
                <thead className="text-slate-400 text-[11px]">
                  <tr>
                    <th className="pb-2">Parameter</th>
                    <th className="pb-2">Current Value</th>
                    <th className="pb-2 text-right">Proposed Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-[11px]">
                  {selectedPreset.parameters.map((p) => {
                    const current = parameters.find((x) => x.address === p.address)
                    return (
                      <tr key={p.address}>
                        <td className="py-2 text-slate-300">
                          <div className="font-semibold text-slate-100">{p.name}</div>
                          <div className="text-[10px] text-slate-500">Reg: {p.address}</div>
                        </td>
                        <td className="py-2 text-slate-400">
                          {current?.current_formatted || 'N/A'}
                        </td>
                        <td className="py-2 text-right font-bold text-cyan-400">
                          {p.value} {p.unit}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              <label className="flex items-center gap-2 text-slate-300 cursor-pointer p-2 bg-slate-950 border border-slate-800 rounded">
                <input
                  type="checkbox"
                  checked={presetConfirmed}
                  onChange={(e) => setPresetConfirmed(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                />
                <span>I confirm modifying these {selectedPreset.parameters.length} registers on the battery module</span>
              </label>

              {/* Preset Results View */}
              {presetResult && (
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                  <div className="font-bold flex items-center gap-2 text-slate-200">
                    {presetResult.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                    )}
                    <span>{presetResult.message}</span>
                  </div>
                  {presetResult.results && (
                    <div className="space-y-1 text-[11px] divide-y divide-slate-800/40">
                      {presetResult.results.map((r: any) => (
                        <div key={r.address} className="pt-1 flex items-center justify-between">
                          <span className="text-slate-400">{r.name}</span>
                          <span className={r.success ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                            {r.success ? `Verified (${r.verified_value})` : 'Failed'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="px-5 py-3 border-t border-slate-800 bg-slate-950 flex justify-end gap-2">
              <button
                onClick={() => setSelectedPreset(null)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
              >
                Close
              </button>
              <button
                onClick={handleExecutePreset}
                disabled={!writesEnabled || !presetConfirmed || applyingPreset || userRole !== 'ADMINISTRATOR'}
                className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white font-bold rounded-lg transition"
              >
                {applyingPreset ? 'Applying Preset...' : 'Apply Preset'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Snapshot Save Modal */}
      {snapshotModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 max-w-md w-full space-y-4 font-mono text-xs">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Camera className="w-4 h-4 text-cyan-400" />
              <span>Capture Configuration Snapshot</span>
            </h3>

            <div>
              <label className="text-slate-400 block mb-1">Snapshot Label / Name</label>
              <input
                type="text"
                value={snapshotName}
                onChange={(e) => setSnapshotName(e.target.value)}
                placeholder="e.g. Factory Baseline or Post-Commissioning"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Notes (Optional)</label>
              <textarea
                value={snapshotNotes}
                onChange={(e) => setSnapshotNotes(e.target.value)}
                placeholder="Reason for snapshot or firmware version..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setSnapshotModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveSnapshot}
                disabled={!snapshotName.trim()}
                className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-bold"
              >
                Save Snapshot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 10-Step Guarded Write Modal for Individual Parameters */}
      {selectedParam && (
        <GuardedWriteModal
          parameter={selectedParam}
          userRole={userRole}
          onClose={() => setSelectedParam(null)}
          onSuccess={() => {
            setSelectedParam(null)
            loadData()
          }}
        />
      )}
    </div>
  )
}
