import React, { useEffect, useState } from 'react'
import {
  CheckCircle2,
  Download,
  Filter,
  RefreshCw,
  Search,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import { api } from '../services/api'
import type { AuditLogEntry } from '../types'

export const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')

  const loadLogs = async () => {
    setLoading(true)
    try {
      const data = await api.getAuditLogs(300)
      setLogs(data)
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [])

  const handleExportCsv = () => {
    window.open('/api/audit/export-csv?limit=2000', '_blank')
  }

  const filtered = logs.filter((l) => {
    const matchesSearch =
      (l.parameter_name && l.parameter_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (l.action && l.action.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (l.user_role && l.user_role.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (l.details && l.details.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesStatus = statusFilter === 'ALL' || l.status.toUpperCase() === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span>Immutable Security & Parameter Write Audit Log</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete tamper-evident audit records of all configuration changes, validation checks, and read-back verifications.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <button
            onClick={loadLogs}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by action, parameter name, user role..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none"
          >
            <option value="ALL">All Outcomes</option>
            <option value="SUCCESS">Success</option>
            <option value="REJECTED">Rejected</option>
            <option value="VERIFICATION_FAILED">Verification Failed</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden font-mono text-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">ID</th>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Parameter (Addr)</th>
                <th className="py-2.5 px-3">Previous → Requested</th>
                <th className="py-2.5 px-3">Read-Back Verified</th>
                <th className="py-2.5 px-3 text-right">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.map((l) => {
                const isSuccess = l.status === 'SUCCESS'
                const isFail = l.status === 'VERIFICATION_FAILED' || l.status === 'FAILED'
                return (
                  <tr key={l.id} className="hover:bg-slate-800/40 text-slate-300">
                    <td className="py-2.5 px-3 font-bold text-slate-500">#{l.id}</td>
                    <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                      {new Date(l.timestamp * 1000).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 font-bold text-cyan-400">{l.user_role}</td>
                    <td className="py-2.5 px-3 font-semibold text-slate-200">{l.action}</td>
                    <td className="py-2.5 px-3">
                      <div className="text-slate-100">{l.parameter_name || '—'}</div>
                      {l.parameter_address && (
                        <div className="text-[10px] text-slate-500">Addr: {l.parameter_address}</div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      <span className="text-slate-500">{l.previous_value || '—'}</span>
                      <span className="text-slate-600 mx-1">→</span>
                      <span className="text-slate-100 font-bold">{l.requested_value || '—'}</span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-emerald-400">
                      {l.read_back_value !== null ? l.read_back_value : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {isSuccess ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700/60 text-[10px] font-bold">
                          SUCCESS
                        </span>
                      ) : isFail ? (
                        <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-700/60 text-[10px] font-bold">
                          FAILED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-700/60 text-[10px] font-bold">
                          {l.status}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No audit records found matching criteria.
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
