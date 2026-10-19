import React, { useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowUpDown,
  BatteryCharging,
  Layers,
  Sparkles,
  Thermometer,
  Zap,
} from 'lucide-react'
import type { CellData } from '../types'

interface CellModuleMonitoringPageProps {
  cells: CellData | null
}

export const CellModuleMonitoringPage: React.FC<CellModuleMonitoringPageProps> = ({ cells }) => {
  const [sortField, setSortField] = useState<'id' | 'voltage'>('id')
  const [sortAsc, setSortAsc] = useState(true)
  const [outlierThresholdMv, setOutlierThresholdMv] = useState(30.0)

  const voltages = cells?.cell_voltages || []
  const minV = cells?.min_cell_voltage ?? 0
  const maxV = cells?.max_cell_voltage ?? 0
  const avgV = cells?.avg_cell_voltage ?? 0
  const deltaMv = cells?.cell_voltage_delta_mv ?? 0

  const cellList = voltages.map((v, i) => {
    const deltaFromAvgMv = Math.abs(v - avgV) * 1000.0
    const isOutlier = deltaFromAvgMv > outlierThresholdMv
    const isBalancing = cells?.balancing_active?.[i] ?? false
    return {
      id: i + 1,
      voltage: v,
      deltaFromAvgMv,
      isOutlier,
      isBalancing,
      isMax: v === maxV,
      isMin: v === minV,
    }
  })

  const sortedCells = [...cellList].sort((a, b) => {
    if (sortField === 'id') {
      return sortAsc ? a.id - b.id : b.id - a.id
    } else {
      return sortAsc ? a.voltage - b.voltage : b.voltage - a.voltage
    }
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            <span>Cell & Module Level Telemetry</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Individual series cell voltage distribution, passive balancing indicators, and temperature sensors.
          </p>
        </div>

        {/* Delta V Alert Banner */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold border ${
            deltaMv > 50
              ? 'bg-rose-950/80 text-rose-300 border-rose-600 animate-pulse'
              : 'bg-slate-950 text-cyan-400 border-slate-800'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Voltage Spread ΔV: {deltaMv} mV</span>
        </div>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Min Cell Voltage</span>
          <div className="text-2xl font-black text-blue-400 mt-1">
            {minV ? `${minV.toFixed(3)} V` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Lowest potential cell</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Max Cell Voltage</span>
          <div className="text-2xl font-black text-amber-400 mt-1">
            {maxV ? `${maxV.toFixed(3)} V` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Highest potential cell</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Mean Pack Cell Voltage</span>
          <div className="text-2xl font-black text-slate-100 mt-1">
            {avgV ? `${avgV.toFixed(3)} V` : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Arithmetic average</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 uppercase text-[10px]">Active Balancing</span>
          <div className="text-2xl font-black text-cyan-400 mt-1 flex items-center gap-2">
            <span>{cells?.balancing_active?.filter(Boolean).length ?? 0}</span>
            <span className="text-xs text-slate-400">/ {voltages.length || 16} Cells</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Passive bleed resistors</div>
        </div>
      </div>

      {/* Visual Cell Voltage Distribution Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold text-slate-200 text-sm font-mono flex items-center gap-2">
            <BatteryCharging className="w-4 h-4 text-cyan-400" />
            <span>{voltages.length || 16}-Cell Series Topology Visualizer</span>
          </h3>

          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-slate-400">Outlier Threshold:</span>
            <select
              value={outlierThresholdMv}
              onChange={(e) => setOutlierThresholdMv(Number(e.target.value))}
              className="bg-slate-950 border border-slate-800 text-slate-200 px-2 py-1 rounded focus:outline-none"
            >
              <option value={20}>20 mV</option>
              <option value={30}>30 mV (Default)</option>
              <option value={50}>50 mV (Warning)</option>
              <option value={80}>80 mV (Critical)</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-3 pt-2">
          {cellList.map((c) => {
            return (
              <div
                key={c.id}
                className={`p-3 rounded-xl border flex flex-col items-center justify-between transition-all font-mono relative overflow-hidden ${
                  c.isOutlier
                    ? 'bg-rose-950/40 border-rose-500/80 shadow-lg shadow-rose-950/50'
                    : c.isMax
                    ? 'bg-amber-950/30 border-amber-500/60'
                    : c.isMin
                    ? 'bg-blue-950/30 border-blue-500/60'
                    : 'bg-slate-950 border-slate-800'
                }`}
              >
                {/* Balancing Glow indicator */}
                {c.isBalancing && (
                  <div className="absolute top-1 right-1.5 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  </div>
                )}

                <div className="text-[11px] text-slate-400 font-bold">Cell #{c.id}</div>
                <div className="text-sm font-black text-slate-100 my-2">
                  {c.voltage.toFixed(3)}
                  <span className="text-[10px] text-slate-500 font-normal ml-0.5">V</span>
                </div>

                <div className="text-[9px] text-slate-400">
                  {c.isMax ? (
                    <span className="text-amber-400 font-bold uppercase">MAX</span>
                  ) : c.isMin ? (
                    <span className="text-blue-400 font-bold uppercase">MIN</span>
                  ) : (
                    <span>Δ {c.deltaFromAvgMv.toFixed(1)}mV</span>
                  )}
                </div>

                {c.isBalancing && (
                  <div className="text-[9px] text-cyan-400 font-bold mt-1 uppercase">Bleeding</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Individual Temperature Sensors */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="font-bold text-slate-200 text-sm font-mono flex items-center gap-2">
          <Thermometer className="w-4 h-4 text-rose-400" />
          <span>Module Temperature Sensors ({cells?.temperatures?.length || 16} Probes)</span>
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-3 font-mono text-xs">
          {(cells?.temperatures || []).map((t, idx) => (
            <div key={idx} className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
              <span className="text-[10px] text-slate-500 block">Sensor T{idx + 1}</span>
              <span className="text-base font-bold text-slate-100 mt-1 block">{t.toFixed(1)}°C</span>
            </div>
          ))}
        </div>
      </div>

      {/* Sortable Detailed Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 className="font-bold text-slate-200 text-sm font-mono">Individual Cell Detail Table</h3>

        <div className="overflow-x-auto border border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th
                  onClick={() => {
                    setSortField('id')
                    setSortAsc(!sortAsc)
                  }}
                  className="py-2.5 px-3 cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    <span>Cell Index</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => {
                    setSortField('voltage')
                    setSortAsc(!sortAsc)
                  }}
                  className="py-2.5 px-3 cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    <span>Voltage (V)</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3">Deviation from Mean</th>
                <th className="py-2.5 px-3">Balancing State</th>
                <th className="py-2.5 px-3 text-right">Status Flag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {sortedCells.map((c) => (
                <tr key={c.id} className="hover:bg-slate-800/40 text-slate-300">
                  <td className="py-2 px-3 font-bold text-slate-200">Cell #{c.id}</td>
                  <td className="py-2 px-3 font-bold text-slate-100">{c.voltage.toFixed(3)} V</td>
                  <td className="py-2 px-3 text-slate-400">{c.deltaFromAvgMv.toFixed(1)} mV</td>
                  <td className="py-2 px-3">
                    {c.isBalancing ? (
                      <span className="text-cyan-400 font-bold">Active Passive Bleed</span>
                    ) : (
                      <span className="text-slate-500">Idle</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {c.isOutlier ? (
                      <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-700/60 text-[10px] font-bold">
                        Outlier Delta
                      </span>
                    ) : c.isMax ? (
                      <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-700/60 text-[10px] font-bold">
                        Pack Max
                      </span>
                    ) : c.isMin ? (
                      <span className="px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-700/60 text-[10px] font-bold">
                        Pack Min
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[10px]">Normal</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
