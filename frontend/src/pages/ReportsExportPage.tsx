import React, { useEffect, useState } from 'react'
import {
  Archive,
  BarChart3,
  Calendar,
  CheckCircle2,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { api } from '../services/api'

export const ReportsExportPage: React.FC = () => {
  const [report, setReport] = useState<any | null>(null)
  const [periodDays, setPeriodDays] = useState(7)
  const [loadingReport, setLoadingReport] = useState(false)
  const [backupStatus, setBackupStatus] = useState<string | null>(null)

  const loadReport = async () => {
    setLoadingReport(true)
    try {
      const rep = await api.getReport(periodDays)
      setReport(rep)
    } catch (e) {
      // ignore
    } finally {
      setLoadingReport(false)
    }
  }

  useEffect(() => {
    loadReport()
  }, [periodDays])

  const handleDownloadTelemetryCsv = () => {
    window.open('/api/history/export-csv?limit=5000', '_blank')
  }

  const handleDownloadAuditCsv = () => {
    window.open('/api/audit/export-csv?limit=2000', '_blank')
  }

  const handleBackupDatabase = async () => {
    setBackupStatus('Creating SQLite backup...')
    try {
      const res = await api.triggerBackup()
      setBackupStatus(`Backup saved successfully at: ${res.backup_path}`)
    } catch (e: any) {
      setBackupStatus(`Backup failed: ${e.message}`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-cyan-400" />
            <span>Operational Reports & Data Export</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Generate aggregate battery health reports, export historical logs to CSV, and perform database backups.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">Period:</span>
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="bg-slate-950 border border-slate-800 text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none"
          >
            <option value={1}>Last 24 Hours</option>
            <option value={7}>Last 7 Days (Weekly)</option>
            <option value={30}>Last 30 Days (Monthly)</option>
          </select>
          <button
            onClick={loadReport}
            disabled={loadingReport}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingReport ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Aggregate Report Summary Cards */}
      {report && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          {/* Energy & Efficiency */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
              <Zap className="w-4 h-4" />
              <span>Energy & Efficiency</span>
            </div>
            <div className="space-y-2 pt-1">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Energy Charged:</span>
                <span className="text-slate-100 font-bold">{report.energy?.charged_kwh} kWh</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Energy Discharged:</span>
                <span className="text-slate-100 font-bold">{report.energy?.discharged_kwh} kWh</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Round-Trip Efficiency:</span>
                <span className="text-emerald-400 font-bold">
                  {report.energy?.round_trip_efficiency_pct
                    ? `${report.energy.round_trip_efficiency_pct}%`
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Operating Envelope */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-amber-400 font-bold text-sm">
              <BarChart3 className="w-4 h-4" />
              <span>Operating Envelopes</span>
            </div>
            <div className="space-y-2 pt-1">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Voltage [Min / Max]:</span>
                <span className="text-slate-100 font-bold">
                  {report.voltage?.min ?? 'N/A'}V / {report.voltage?.max ?? 'N/A'}V
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Temp [Min / Max]:</span>
                <span className="text-slate-100 font-bold">
                  {report.temperature?.min ?? 'N/A'}°C / {report.temperature?.max ?? 'N/A'}°C
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Mean SOC:</span>
                <span className="text-slate-100 font-bold">
                  {report.soc?.avg ? `${report.soc.avg}%` : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Alarm Frequencies */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
              <CheckCircle2 className="w-4 h-4" />
              <span>Fault Events & Reliability</span>
            </div>
            <div className="space-y-2 pt-1">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Total Alarm Events:</span>
                <span className="text-slate-100 font-bold">{report.alarms?.total_events ?? 0}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Critical Alarms:</span>
                <span className="text-rose-400 font-bold">{report.alarms?.critical_count ?? 0}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Data Points Logged:</span>
                <span className="text-slate-100 font-bold">{report.data_points ?? 0}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Export Actions Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 font-mono text-xs">
        <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
          <Download className="w-4 h-4 text-cyan-400" />
          <span>Raw Data Exports & Database Maintenance</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* Telemetry CSV */}
          <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex flex-col justify-between space-y-3">
            <div>
              <div className="font-bold text-slate-100">Telemetry History CSV</div>
              <p className="text-[11px] text-slate-400 font-sans mt-1">
                Download timestamped time-series records of voltage, current, power, temperatures, and SOC.
              </p>
            </div>
            <button
              onClick={handleDownloadTelemetryCsv}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 rounded-lg font-bold flex items-center justify-center gap-2 transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Telemetry CSV</span>
            </button>
          </div>

          {/* Audit Log CSV */}
          <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex flex-col justify-between space-y-3">
            <div>
              <div className="font-bold text-slate-100">Audit Trail CSV</div>
              <p className="text-[11px] text-slate-400 font-sans mt-1">
                Export complete security audit logs of all parameter modifications and administrative operations.
              </p>
            </div>
            <button
              onClick={handleDownloadAuditCsv}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 rounded-lg font-bold flex items-center justify-center gap-2 transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Audit Log CSV</span>
            </button>
          </div>

          {/* Database Backup */}
          <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex flex-col justify-between space-y-3">
            <div>
              <div className="font-bold text-slate-100">SQLite Database Backup</div>
              <p className="text-[11px] text-slate-400 font-sans mt-1">
                Create a point-in-time snapshot of the entire local SQLite database with write-ahead log consistency.
              </p>
            </div>
            <button
              onClick={handleBackupDatabase}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 rounded-lg font-bold flex items-center justify-center gap-2 transition"
            >
              <Archive className="w-3.5 h-3.5" />
              <span>Create Online Backup</span>
            </button>
          </div>
        </div>

        {backupStatus && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-700/60 rounded-lg text-emerald-300 text-xs">
            {backupStatus}
          </div>
        )}
      </div>
    </div>
  )
}
