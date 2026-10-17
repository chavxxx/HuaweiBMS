import React, { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Download,
  Lock,
  Radio,
  RefreshCw,
  Send,
  ShieldAlert,
  Terminal,
  Zap,
} from 'lucide-react'
import { api } from '../services/api'
import type { CommStatistics, ProtocolFrame, UserRole } from '../types'

interface DiagnosticsPageProps {
  userRole: UserRole
}

export const DiagnosticsPage: React.FC<DiagnosticsPageProps> = ({ userRole }) => {
  const [commStats, setCommStats] = useState<CommStatistics | null>(null)
  const [frames, setFrames] = useState<ProtocolFrame[]>([])
  const [loading, setLoading] = useState(false)

  // Raw Frame Transmitter
  const [rawHexInput, setRawHexInput] = useState('')
  const [safetyOverride, setSafetyOverride] = useState(false)
  const [transmitting, setTransmitting] = useState(false)
  const [rawTxResult, setRawTxResult] = useState<any | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const loadDiagnostics = async () => {
    try {
      const diag = await api.getCommDiagnostics()
      setCommStats(diag.stats)
      const trace = await api.getProtocolTrace()
      setFrames(trace.reverse())
    } catch (e) {
      // ignore
    }
  }

  useEffect(() => {
    loadDiagnostics()
    const timer = setInterval(loadDiagnostics, 2500)
    return () => clearInterval(timer)
  }, [])

  const handleTransmitRaw = async () => {
    if (!rawHexInput.trim() || !safetyOverride) return
    setTransmitting(true)
    setErrorMsg(null)
    setRawTxResult(null)
    try {
      const res = await api.transmitRawFrame({
        raw_hex: rawHexInput,
        safety_override: true,
        operator_confirmed: true,
        user_role: userRole,
      })
      setRawTxResult(res)
      await loadDiagnostics()
    } catch (e: any) {
      setErrorMsg(e.message || 'Raw transmission failed')
    } finally {
      setTransmitting(false)
    }
  }

  const handleExportTrace = () => {
    const blob = new Blob([JSON.stringify(frames, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `protocol_trace_${Date.now()}.json`
    a.click()
  }

  const totalReq = commStats?.total_requests ?? 0
  const totalResp = commStats?.total_responses ?? 0
  const reliability =
    totalReq > 0 ? ((totalResp / totalReq) * 100).toFixed(1) : '100.0'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-cyan-400" />
            <span>Communication Diagnostics & Live Protocol Analyzer</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time RS485 bus statistics, Modbus RTU byte framing inspector, and engineering trace tools.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <button
            onClick={loadDiagnostics}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportTrace}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Trace JSON</span>
          </button>
        </div>
      </div>

      {/* Serial Health & Communication Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 font-mono text-xs">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <span className="text-slate-500 uppercase text-[10px]">Bus Reliability</span>
          <div className="text-xl font-black text-emerald-400 mt-1">{reliability}%</div>
          <div className="text-[10px] text-slate-500 mt-1">{totalResp}/{totalReq} Packets</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <span className="text-slate-500 uppercase text-[10px]">Mean Latency</span>
          <div className="text-xl font-black text-slate-100 mt-1">
            {commStats?.average_latency_ms ? `${commStats.average_latency_ms.toFixed(1)} ms` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">
            Last: {commStats?.last_latency_ms ? `${commStats.last_latency_ms.toFixed(1)}ms` : 'N/A'}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <span className="text-slate-500 uppercase text-[10px]">Timeouts</span>
          <div className="text-xl font-black text-amber-400 mt-1">
            {commStats?.total_timeouts ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Unanswered frames</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <span className="text-slate-500 uppercase text-[10px]">CRC-16 Errors</span>
          <div className="text-xl font-black text-rose-400 mt-1">
            {commStats?.total_crc_errors ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Corrupted checksums</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <span className="text-slate-500 uppercase text-[10px]">Retries</span>
          <div className="text-xl font-black text-slate-100 mt-1">
            {commStats?.total_retries ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Bounded retry attempts</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
          <span className="text-slate-500 uppercase text-[10px]">Data Volume</span>
          <div className="text-xl font-black text-cyan-400 mt-1">
            {commStats?.bytes_received ? `${(commStats.bytes_received / 1024).toFixed(1)} KB` : '0 KB'}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">TX: {(commStats?.bytes_sent ?? 0) / 1024 | 0} KB</div>
        </div>
      </div>

      {/* Protocol Analyzer Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            <span>Live Modbus RTU Frame Stream (Recent {frames.length})</span>
          </h3>
          <span className="text-slate-500 text-[11px]">Decoded with CRC16 Verification</span>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-96 overflow-y-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
              <tr>
                <th className="py-2 px-3">Time</th>
                <th className="py-2 px-3">Dir</th>
                <th className="py-2 px-3">Slave</th>
                <th className="py-2 px-3">Function</th>
                <th className="py-2 px-3">Raw Hex Bytes</th>
                <th className="py-2 px-3">Decoded Registers / Details</th>
                <th className="py-2 px-3 text-right">CRC Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {frames.map((f, i) => {
                const isTx = f.direction === 'TX'
                return (
                  <tr key={i} className="hover:bg-slate-800/40 text-slate-300">
                    <td className="py-2 px-3 text-slate-500 whitespace-nowrap">
                      {new Date(f.timestamp * 1000).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          isTx
                            ? 'bg-blue-950 text-blue-400 border border-blue-800'
                            : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        }`}
                      >
                        {f.direction}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-bold text-slate-200">{f.slave_id}</td>
                    <td className="py-2 px-3">
                      <span className="font-semibold text-cyan-300">{f.function_name}</span>
                      {f.is_exception && (
                        <span className="text-rose-400 font-bold ml-1.5">[EXCEPTION]</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-[11px] font-mono text-slate-400 truncate max-w-xs">
                      {f.raw_hex}
                    </td>
                    <td className="py-2 px-3 text-slate-300">
                      {f.is_exception ? (
                        <span className="text-rose-400 font-semibold">{f.exception_message}</span>
                      ) : f.register_address !== null ? (
                        <span>
                          Addr: {f.register_address} (Count: {f.register_count ?? 1})
                        </span>
                      ) : f.values && f.values.length > 0 ? (
                        <span className="text-slate-400">
                          Values: [{f.values.slice(0, 5).join(', ')}
                          {f.values.length > 5 ? '...' : ''}]
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {f.crc_valid ? (
                        <span className="text-emerald-400 font-bold text-[10px]">CRC OK</span>
                      ) : (
                        <span className="text-rose-400 font-bold text-[10px] animate-pulse">
                          CRC FAIL
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {frames.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No frames captured yet. Connect to RS485 or toggle simulator.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Raw Frame Transmitter (Strictly Gated Engineering Tool) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 font-mono text-xs">
        <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
          <ShieldAlert className="w-4 h-4" />
          <span>Advanced Raw Frame Transmitter (Engineering Mode)</span>
        </div>

        <p className="text-slate-400 font-sans text-xs">
          Direct byte transmission is disabled by default to prevent bus contention or unintended register writes.
          Command filter automatically rejects contactor coil actuation and dangerous unprotected state modifications.
        </p>

        <div className="space-y-3 pt-2">
          <div className="flex gap-3">
            <input
              type="text"
              value={rawHexInput}
              onChange={(e) => setRawHexInput(e.target.value)}
              placeholder="e.g. 01 03 90 88 00 02 4A 38"
              disabled={userRole !== 'ADMINISTRATOR'}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
            />
            <button
              onClick={handleTransmitRaw}
              disabled={
                !rawHexInput.trim() ||
                !safetyOverride ||
                userRole !== 'ADMINISTRATOR' ||
                transmitting
              }
              className={`px-5 py-2 rounded-lg font-bold flex items-center gap-2 transition ${
                safetyOverride && userRole === 'ADMINISTRATOR'
                  ? 'bg-rose-600 hover:bg-rose-500 text-white'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed'
              }`}
            >
              <Send className="w-3.5 h-3.5" />
              <span>Transmit Raw Frame</span>
            </button>
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-slate-400">
            <input
              type="checkbox"
              checked={safetyOverride}
              onChange={(e) => setSafetyOverride(e.target.checked)}
              disabled={userRole !== 'ADMINISTRATOR'}
              className="rounded bg-slate-950 border-slate-800 text-rose-600 focus:ring-0"
            />
            <span className="text-[11px]">
              Safety Override Acknowledged: I understand transmitting arbitrary frames may alter device state.
            </span>
          </label>
        </div>

        {rawTxResult && (
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1">
            <div className="font-bold text-emerald-400">Response Received:</div>
            <div className="text-slate-200">{rawTxResult.response_hex || 'No response bytes'}</div>
            {rawTxResult.message && <div className="text-slate-400 text-[11px]">{rawTxResult.message}</div>}
          </div>
        )}

        {errorMsg && (
          <div className="p-3 bg-rose-950/40 border border-rose-600/60 rounded-lg text-rose-300">
            {errorMsg}
          </div>
        )}
      </div>
    </div>
  )
}
