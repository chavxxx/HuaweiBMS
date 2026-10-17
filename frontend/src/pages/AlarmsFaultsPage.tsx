import React, { useEffect, useState } from 'react'
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Download,
  Filter,
  Info,
  RefreshCw,
  Search,
  ShieldAlert,
  Wrench,
} from 'lucide-react'
import { api } from '../services/api'
import type { AlarmItem } from '../types'

export const AlarmsFaultsPage: React.FC = () => {
  const [activeAlarms, setActiveAlarms] = useState<AlarmItem[]>([])
  const [historyAlarms, setHistoryAlarms] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)

  const loadAlarms = async () => {
    setLoading(true)
    try {
      const active = await api.getActiveAlarms()
      const history = await api.getAlarmHistory()
      setActiveAlarms(active)
      setHistoryAlarms(history)
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlarms()
    const timer = setInterval(loadAlarms, 4000)
    return () => clearInterval(timer)
  }, [])

  const handleInjectAlarm = async (code: number) => {
    try {
      await api.simulateInjectAlarm(code)
      setFeedback(`Injected simulated alarm code ${code}.`)
      await loadAlarms()
    } catch (e: any) {
      setFeedback(e.message)
    }
  }

  const handleClearAlarm = async (code: number) => {
    try {
      await api.simulateClearAlarm(code)
      setFeedback(`Cleared simulated alarm code ${code}.`)
      await loadAlarms()
    } catch (e: any) {
      setFeedback(e.message)
    }
  }

  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify({ active: activeAlarms, history: historyAlarms }, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `huawei_bms_alarms_${Date.now()}.json`
    a.click()
  }

  const filteredActive = activeAlarms.filter((a) => {
    const matchesSearch =
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.code.toString().includes(searchQuery) ||
      a.subsystem.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesSev = severityFilter === 'ALL' || a.severity.toUpperCase() === severityFilter
    return matchesSearch && matchesSev
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-rose-400" />
            <span>Alarm & Fault Management</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time active alarm diagnostics and manufacturer corrective action procedures.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadAlarms}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportJson}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Simulator Test Alarm Injection Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <Wrench className="w-4 h-4 text-cyan-400" />
          <span>Diagnostic Simulator Fault Injection:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleInjectAlarm(3000)}
            className="px-2.5 py-1 bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-600 rounded"
          >
            + Test Alarm 3000 (High Temp)
          </button>
          <button
            onClick={() => handleInjectAlarm(3006)}
            className="px-2.5 py-1 bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-600 rounded"
          >
            + Test Alarm 3006 (Cell Spread)
          </button>
          <button
            onClick={() => handleInjectAlarm(3002)}
            className="px-2.5 py-1 bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-600 rounded"
          >
            + Test Alarm 3002 (Overvoltage)
          </button>
          {activeAlarms.length > 0 && (
            <button
              onClick={() => {
                activeAlarms.forEach((a) => handleClearAlarm(a.code))
              }}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded"
            >
              Clear All Simulated Alarms
            </button>
          )}
        </div>
      </div>

      {feedback && (
        <div className="p-3 bg-cyan-950/40 border border-cyan-800 rounded-lg text-cyan-300 text-xs font-mono">
          {feedback}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by alarm code, name, or subsystem..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="MAJOR">Major</option>
            <option value="WARNING">Warning</option>
          </select>
        </div>
      </div>

      {/* Active Alarms List */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-200 font-mono flex items-center justify-between">
          <span>Active Hardware Alarms ({filteredActive.length})</span>
          {activeAlarms.length === 0 && (
            <span className="text-emerald-400 font-normal flex items-center gap-1 text-xs">
              <CheckCircle2 className="w-3.5 h-3.5" /> All systems nominal
            </span>
          )}
        </h3>

        {filteredActive.length > 0 ? (
          <div className="space-y-3">
            {filteredActive.map((alarm) => {
              const isCrit = alarm.severity.toLowerCase() === 'critical'
              const isMaj = alarm.severity.toLowerCase() === 'major'
              return (
                <div
                  key={alarm.code}
                  className={`p-4 rounded-xl border font-mono transition ${
                    isCrit
                      ? 'bg-rose-950/30 border-rose-600/70 shadow-lg shadow-rose-950/40'
                      : isMaj
                      ? 'bg-amber-950/30 border-amber-600/70'
                      : 'bg-slate-900 border-slate-800'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          isCrit
                            ? 'bg-rose-950 text-rose-400 border-rose-600 animate-pulse'
                            : isMaj
                            ? 'bg-amber-950 text-amber-400 border-amber-600'
                            : 'bg-yellow-950 text-yellow-400 border-yellow-600'
                        }`}
                      >
                        {alarm.severity}
                      </span>
                      <span className="font-bold text-slate-100 text-sm">{alarm.name}</span>
                      <span className="text-xs text-cyan-400 font-semibold">
                        [Code: {alarm.code} / 0x{alarm.code.toString(16).toUpperCase()}]
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-500 font-semibold">
                      Subsystem: {alarm.subsystem}
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 font-sans mt-2">{alarm.description}</p>

                  <div className="mt-3 p-3 bg-slate-950/80 rounded-lg border border-slate-800/80 text-xs">
                    <div className="text-[11px] text-cyan-400 font-bold uppercase flex items-center gap-1">
                      <Wrench className="w-3 h-3" />
                      <span>Manufacturer Documented Corrective Action:</span>
                    </div>
                    <div className="text-slate-300 font-sans mt-1 leading-relaxed">
                      {alarm.corrective_action}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="p-8 bg-slate-900 border border-slate-800 rounded-xl text-center text-slate-500 font-mono text-xs">
            No active alarms found matching criteria.
          </div>
        )}
      </div>

      {/* Historical Fault Events */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-200 font-mono">
          Historical Alarm Log ({historyAlarms.length})
        </h3>

        <div className="overflow-x-auto border border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Code</th>
                <th className="py-2.5 px-3">Alarm Description</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Subsystem</th>
                <th className="py-2.5 px-3">First Seen</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {historyAlarms.slice(0, 30).map((h) => (
                <tr key={h.id} className="hover:bg-slate-800/40 text-slate-300">
                  <td className="py-2 px-3 font-bold text-cyan-400">{h.alarm_code}</td>
                  <td className="py-2 px-3 text-slate-200 font-semibold">{h.name}</td>
                  <td className="py-2 px-3">{h.severity}</td>
                  <td className="py-2 px-3 text-slate-400">{h.subsystem}</td>
                  <td className="py-2 px-3 text-slate-500">
                    {new Date(h.first_seen * 1000).toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {h.is_active ? (
                      <span className="text-rose-400 font-bold">Active</span>
                    ) : (
                      <span className="text-slate-500">Cleared</span>
                    )}
                  </td>
                </tr>
              ))}
              {historyAlarms.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500">
                    No historical alarms recorded in database.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
