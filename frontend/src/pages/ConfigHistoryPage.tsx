import React, { useEffect, useState } from 'react'
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  Clock,
  Eye,
  History,
  RotateCcw,
  Sliders,
} from 'lucide-react'
import { api } from '../services/api'
import type { SnapshotItem, UserRole } from '../types'

interface ConfigHistoryPageProps {
  userRole: UserRole
  onNavigateConfig: () => void
}

export const ConfigHistoryPage: React.FC<ConfigHistoryPageProps> = ({
  userRole,
  onNavigateConfig,
}) => {
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedSnapshot, setSelectedSnapshot] = useState<number | null>(null)
  const [comparison, setComparison] = useState<any | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  const loadSnapshots = async () => {
    setLoading(true)
    try {
      const list = await api.listSnapshots()
      setSnapshots(list)
      if (list.length > 0 && selectedSnapshot === null) {
        handleCompare(list[0].id)
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSnapshots()
  }, [])

  const handleCompare = async (snapshotId: number) => {
    setSelectedSnapshot(snapshotId)
    try {
      const res = await api.compareSnapshot(snapshotId)
      setComparison(res)
    } catch (e: any) {
      setFeedback(e.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <History className="w-5 h-5 text-cyan-400" />
            <span>Configuration Snapshots & Version Comparison</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Compare previous configuration baselines against current live BMS parameter states.
          </p>
        </div>

        <button
          onClick={onNavigateConfig}
          className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
        >
          ← Return to Parameters
        </button>
      </div>

      {feedback && (
        <div className="p-3 bg-cyan-950/40 border border-cyan-800 rounded-lg text-cyan-300 text-xs font-mono">
          {feedback}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Saved Snapshots List */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs">
          <h3 className="font-bold text-slate-200 text-sm flex items-center justify-between">
            <span>Saved Snapshots ({snapshots.length})</span>
            <Camera className="w-4 h-4 text-slate-500" />
          </h3>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {snapshots.map((s) => {
              const isSelected = selectedSnapshot === s.id
              return (
                <div
                  key={s.id}
                  onClick={() => handleCompare(s.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-500/80 text-cyan-200 shadow'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-100 text-xs">{s.snapshot_name}</span>
                    <span className="text-[10px] text-slate-500">#{s.id}</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(s.timestamp * 1000).toLocaleString()}</span>
                  </div>
                  {s.notes && (
                    <div className="text-[10px] text-slate-500 mt-1.5 font-sans line-clamp-2">
                      {s.notes}
                    </div>
                  )}
                </div>
              )
            })}
            {snapshots.length === 0 && (
              <div className="py-8 text-center text-slate-500">
                No snapshots captured yet. Click "Save Snapshot" in Configuration page.
              </div>
            )}
          </div>
        </div>

        {/* Diff Comparison Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 lg:col-span-2 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="font-bold text-slate-200 text-sm">
                Snapshot Diff Comparison:{' '}
                <span className="text-cyan-400">{comparison?.snapshot_name || 'Select a snapshot'}</span>
              </h3>
              {comparison && (
                <p className="text-[10px] text-slate-500 mt-0.5">
                  Captured at: {new Date(comparison.timestamp * 1000).toLocaleString()}
                </p>
              )}
            </div>
          </div>

          {comparison ? (
            <div className="overflow-x-auto border border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Reg Address</th>
                    <th className="py-2.5 px-3">Parameter</th>
                    <th className="py-2.5 px-3 text-center">Snapshot Value</th>
                    <th className="py-2.5 px-3 text-center">Live Value</th>
                    <th className="py-2.5 px-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(comparison.comparisons || []).map((c: any) => (
                    <tr
                      key={c.address}
                      className={`hover:bg-slate-800/40 ${
                        c.has_changed ? 'bg-amber-950/20 text-amber-200' : 'text-slate-300'
                      }`}
                    >
                      <td className="py-2 px-3 font-bold text-slate-400">{c.address}</td>
                      <td className="py-2 px-3 font-semibold text-slate-100">{c.name}</td>
                      <td className="py-2 px-3 text-center font-bold text-slate-300">
                        {c.snapshot_value !== undefined ? `${c.snapshot_value} ${c.unit}` : 'N/A'}
                      </td>
                      <td className="py-2 px-3 text-center font-bold text-cyan-400">
                        {c.current_value !== undefined ? `${c.current_value} ${c.unit}` : 'N/A'}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {c.has_changed ? (
                          <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-700/60 text-[10px] font-bold">
                            MODIFIED
                          </span>
                        ) : (
                          <span className="text-emerald-400 text-[10px] font-bold">MATCH</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500">
              Select a snapshot from the left list to view differences against live telemetry.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
