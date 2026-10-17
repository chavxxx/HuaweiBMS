import React, { useEffect, useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Gauge,
  Info,
  Shield,
  Zap,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../services/api'
import type { ElectricalData, FreshnessStatus, TelemetryData } from '../types'

interface ElectricalMonitoringPageProps {
  telemetry: TelemetryData | null
  electrical: ElectricalData | null
  freshness: FreshnessStatus | null
}

export const ElectricalMonitoringPage: React.FC<ElectricalMonitoringPageProps> = ({
  telemetry,
  electrical,
  freshness,
}) => {
  const [historyPoints, setHistoryPoints] = useState<any[]>([])

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const pts = await api.queryHistory(undefined, undefined, 40)
        const mapped = pts.map((p) => ({
          time: new Date(p.timestamp * 1000).toLocaleTimeString(),
          voltage: p.total_voltage,
          current: p.current,
          power: p.power,
        }))
        setHistoryPoints(mapped)
      } catch (e) {
        // ignore
      }
    }
    fetchHistory()
    const timer = setInterval(fetchHistory, 3000)
    return () => clearInterval(timer)
  }, [])

  const v = electrical?.total_voltage ?? null
  const i = electrical?.current ?? null
  const p = telemetry?.power ?? null
  const chargeE = electrical?.charge_energy ?? null
  const dischE = electrical?.discharge_energy ?? null
  const efficiency =
    chargeE && dischE && chargeE > 0 ? ((dischE / chargeE) * 100).toFixed(1) : 'N/A'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            <span>Battery Electrical & DC Bus Monitoring</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time DC bus voltages, current flows, power envelopes, contactor switchgear, and energy counters.
          </p>
        </div>

        {/* Calculation Policy Badge */}
        <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400">
          <Info className="w-4 h-4 text-cyan-400" />
          <span>Formula: Instantaneous Power P = V × I (Signed)</span>
        </div>
      </div>

      {/* Electrical Measurement Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Total Pack Voltage</span>
          <div className="text-2xl font-black text-slate-100 mt-1">
            {v !== null ? `${v.toFixed(1)} V` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-2">Direct Hardware Telemetry</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">DC Bus Terminal Voltage</span>
          <div className="text-2xl font-black text-slate-100 mt-1">
            {electrical?.dc_bus_voltage ? `${electrical.dc_bus_voltage} V` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-2">After Main Precharge / Contactor</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Pack Current</span>
          <div className="text-2xl font-black text-slate-100 mt-1">
            {i !== null ? `${i > 0 ? `+${i.toFixed(1)}` : i.toFixed(1)} A` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-2">Positive: Discharge · Negative: Charge</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Instantaneous Power</span>
          <div className="text-2xl font-black text-cyan-400 mt-1">
            {p !== null ? `${p.toFixed(3)} kW` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-2">Calculated Metric (Labeled)</div>
        </div>
      </div>

      {/* Switchgear, Insulation, and Limits */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 font-mono text-xs">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
          <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
            <Gauge className="w-4 h-4 text-cyan-400" />
            <span>Switchgear & Isolation</span>
          </h3>

          <div className="space-y-2">
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Main DC Contactor:</span>
              <span
                className={`font-bold ${
                  electrical?.contactor_state === 'Closed' ? 'text-emerald-400' : 'text-slate-400'
                }`}
              >
                {electrical?.contactor_state || 'Open'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Precharge Circuit:</span>
              <span className="font-bold text-slate-200">{electrical?.precharge_state || 'N/A'}</span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Insulation Resistance:</span>
              <span className="font-bold text-emerald-400">
                {electrical?.insulation_resistance_kohm
                  ? `${electrical.insulation_resistance_kohm} kΩ`
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
          <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span>Hardware Operating Limits</span>
          </h3>

          <div className="space-y-2">
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Max Permitted Charge:</span>
              <span className="font-bold text-slate-200">
                {electrical?.max_charge_power_limit
                  ? `${(electrical.max_charge_power_limit / 1000).toFixed(1)} kW`
                  : '5.0 kW'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Max Permitted Discharge:</span>
              <span className="font-bold text-slate-200">
                {electrical?.max_discharge_power_limit
                  ? `${(electrical.max_discharge_power_limit / 1000).toFixed(1)} kW`
                  : '5.0 kW'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Overvoltage Safety Cutoff:</span>
              <span className="font-bold text-rose-400">435.0 V</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
          <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
            <Activity className="w-4 h-4 text-amber-400" />
            <span>Cumulative Energy Counters</span>
          </h3>

          <div className="space-y-2">
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Total Lifetime Charge:</span>
              <span className="font-bold text-slate-100">
                {chargeE ? `${chargeE} kWh` : 'N/A'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Total Lifetime Discharge:</span>
              <span className="font-bold text-slate-100">
                {dischE ? `${dischE} kWh` : 'N/A'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex justify-between">
              <span className="text-slate-400">Round-Trip Efficiency:</span>
              <span className="font-bold text-emerald-400">
                {efficiency !== 'N/A' ? `${efficiency}%` : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Trend Charts */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="font-bold text-slate-200 text-sm font-mono flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span>Real-time Electrical Trend (Voltage & Power)</span>
        </h3>

        <div className="h-64 w-full">
          {historyPoints.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historyPoints}>
                <defs>
                  <linearGradient id="voltGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} fontStyle="mono" />
                <YAxis stroke="#64748b" fontSize={10} fontStyle="mono" domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#020617',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="voltage"
                  name="Pack Voltage (V)"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#voltGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
              Recording live electrical data points...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
