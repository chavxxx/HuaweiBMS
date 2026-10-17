import React, { useEffect, useState } from 'react'
import {
  BookOpen,
  Database,
  Download,
  FileCode,
  Filter,
  RefreshCw,
  Search,
  Upload,
} from 'lucide-react'
import { api } from '../services/api'

export const RegisterDatabasePage: React.FC = () => {
  const [registers, setRegisters] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [importStatus, setImportStatus] = useState<string | null>(null)

  const loadRegisters = async () => {
    setLoading(true)
    try {
      const list = await api.listRegisters(categoryFilter === 'ALL' ? undefined : categoryFilter)
      setRegisters(list)
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRegisters()
  }, [categoryFilter])

  const handleExportJson = () => {
    window.open('/api/registers/export-json', '_blank')
  }

  const handleExportCsv = () => {
    window.open('/api/registers/export-csv', '_blank')
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, isCsv: boolean) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImportStatus(`Importing ${file.name}...`)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const endpoint = isCsv ? '/api/registers/import-csv' : '/api/registers/import-json'
      const res = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (res.ok) {
        setImportStatus(`Success: ${data.message}`)
        await loadRegisters()
      } else {
        setImportStatus(`Error: ${data.detail || 'Failed to import register file'}`)
      }
    } catch (err: any) {
      setImportStatus(`Import error: ${err.message}`)
    }
  }

  const filtered = registers.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.address.toString().includes(searchQuery) ||
      r.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <span>Modbus Register Definition Database</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Browse verified register maps, scale multipliers, byte orders, and official manufacturer citations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          <label className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg cursor-pointer transition">
            <Upload className="w-3.5 h-3.5 text-cyan-400" />
            <span>Import JSON</span>
            <input
              type="file"
              accept=".json"
              className="hidden"
              onChange={(e) => handleFileUpload(e, false)}
            />
          </label>

          <label className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg cursor-pointer transition">
            <Upload className="w-3.5 h-3.5 text-cyan-400" />
            <span>Import CSV</span>
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => handleFileUpload(e, true)}
            />
          </label>

          <button
            onClick={handleExportJson}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export JSON</span>
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

      {importStatus && (
        <div className="p-3 bg-cyan-950/40 border border-cyan-800 rounded-lg text-cyan-300 text-xs font-mono">
          {importStatus}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search register by address, name, or description..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400">Category:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none"
          >
            <option value="ALL">All Categories</option>
            <option value="identification">Identification</option>
            <option value="telemetry">Telemetry</option>
            <option value="electrical">Electrical</option>
            <option value="cell">Cell & Module</option>
            <option value="parameter">Parameters</option>
            <option value="alarm">Alarms</option>
          </select>
        </div>
      </div>

      {/* Registers Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden font-mono text-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Address</th>
                <th className="py-2.5 px-3">Register Name</th>
                <th className="py-2.5 px-3">Data Type</th>
                <th className="py-2.5 px-3">Scaling</th>
                <th className="py-2.5 px-3">Unit</th>
                <th className="py-2.5 px-3">Access</th>
                <th className="py-2.5 px-3">Source Citation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.map((r) => (
                <tr key={r.address} className="hover:bg-slate-800/40 text-slate-300">
                  <td className="py-2.5 px-3 font-bold text-cyan-400">
                    {r.address}
                    <span className="text-[10px] text-slate-500 ml-1">
                      (0x{r.address.toString(16).toUpperCase()})
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-slate-100">{r.name}</div>
                    <div className="text-[10px] text-slate-500 font-sans truncate max-w-sm">
                      {r.description}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">
                    {r.data_type} ({r.length_registers}w)
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">
                    {r.scaling_divisor !== 1.0 ? `÷ ${r.scaling_divisor}` : `× ${r.scaling_multiplier}`}
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-200">{r.unit || '—'}</td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        r.access_mode === 'writable'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-700/60'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {r.access_mode}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-slate-400 truncate max-w-xs font-sans">
                    {r.source_doc}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No registers found in database.
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
