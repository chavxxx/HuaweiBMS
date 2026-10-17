import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Edit3,
  Lock,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sliders,
  Unlock,
} from 'lucide-react'
import { GuardedWriteModal } from '../components/GuardedWriteModal'
import { api } from '../services/api'
import type { ParameterItem, UserRole } from '../types'

interface ConfigurationPageProps {
  userRole: UserRole
  onNavigateSnapshots: () => void
}

export const ConfigurationPage: React.FC<ConfigurationPageProps> = ({
  userRole,
  onNavigateSnapshots,
}) => {
  const [parameters, setParameters] = useState<ParameterItem[]>([])
  const [writesEnabled, setWritesEnabled] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedParam, setSelectedParam] = useState<ParameterItem | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [snapshotModalOpen, setSnapshotModalOpen] = useState(false)
  const [snapshotName, setSnapshotName] = useState('')
  const [snapshotNotes, setSnapshotNotes] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)

  const loadParameters = async () => {
    setLoading(true)
    try {
      const data = await api.getParameters()
      setParameters(data.parameters || [])
      setWritesEnabled(data.writes_enabled)
    } catch (e: any) {
      setFeedback(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadParameters()
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
      await loadParameters()
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

  const filtered = parameters.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.address.toString().includes(searchQuery) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <span>BMS Configuration & Parameter Management</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Read verified hardware parameters, save configuration snapshots, and execute guarded writes.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
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

      {/* Safety Policy Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-start gap-3 text-xs font-mono">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-slate-300 space-y-1">
          <span className="font-bold text-slate-200">Strict Safety Safeguards Enforced:</span>
          <p className="text-slate-400 font-sans text-[11px] leading-relaxed">
            By default, the application operates in <strong>Read-Only Mode</strong>. Modifying parameters
            requires an explicit Administrator role unlock and must satisfy the verified allowlist. Every write
            undergoes the mandatory <strong>10-Step Guarded Workflow</strong> with instant hardware read-back
            verification and permanent audit logging. Undocumented registers cannot be written.
          </p>
        </div>
      </div>

      {feedback && (
        <div className="p-3 bg-cyan-950/40 border border-cyan-800 rounded-lg text-cyan-300 text-xs font-mono">
          {feedback}
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search parameter name, register address, description..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <button
          onClick={loadParameters}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Values</span>
        </button>
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
              {filtered.map((p) => {
                const isWritable = p.access_mode === 'writable'
                const canModify = writesEnabled && p.is_allowlisted && isWritable && userRole === 'ADMINISTRATOR'

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
                    <td className="py-2.5 px-3 font-bold text-slate-100">
                      {p.current_formatted || 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {p.min_value !== null ? `[${p.min_value} .. ${p.max_value}] ${p.unit}` : 'N/A'}
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
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No configuration parameters match query.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

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

      {/* 10-Step Guarded Write Modal */}
      {selectedParam && (
        <GuardedWriteModal
          parameter={selectedParam}
          userRole={userRole}
          onClose={() => setSelectedParam(null)}
          onSuccess={() => {
            setSelectedParam(null)
            loadParameters()
          }}
        />
      )}
    </div>
  )
}
