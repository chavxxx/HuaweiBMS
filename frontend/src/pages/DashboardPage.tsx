import React from 'react'
import {
  Activity,
  AlertOctagon,
  ArrowDownRight,
  ArrowUpRight,
  Battery,
  BatteryCharging,
  CheckCircle2,
  Clock,
  Cpu,
  Layers,
  Power,
  Shield,
  Thermometer,
  Zap,
} from 'lucide-react'
import { api } from '../services/api'
import type { CellData, ElectricalData, FreshnessStatus, TelemetryData } from '../types'

interface DashboardPageProps {
  telemetry: TelemetryData | null
  electrical: ElectricalData | null
  cells: CellData | null
  freshness: FreshnessStatus | null
  onNavigate: (page: any) => void
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  telemetry,
  electrical,
  cells,
  freshness,
  onNavigate,
}) => {
  const soc = telemetry?.soc ?? null
  const soh = telemetry?.soh ?? null
  const voltage = telemetry?.total_voltage ?? null
  const current = telemetry?.current ?? null
  const power = telemetry?.power ?? null
  const temp = telemetry?.temperature ?? null
  const opState = telemetry?.operating_state ?? 'Disconnected'
  const isCharging = power !== null && power < -0.05
  const isDischarging = power !== null && power > 0.05

  return (
    <div className="space-y-6">
      {/* Top Banner: Device State & Freshness */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl ${
              isCharging
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 animate-pulse'
                : isDischarging
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}
          >
            <BatteryCharging className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-100">
                {telemetry?.device_model || 'Device Unconnected'}
              </h2>
              <span
                className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                  opState === 'Charging'
                    ? 'bg-emerald-950 text-emerald-400 border-emerald-700'
                    : opState === 'Discharging'
                    ? 'bg-amber-950 text-amber-400 border-amber-700'
                    : opState === 'Fault'
                    ? 'bg-rose-950 text-rose-400 border-rose-700 animate-bounce'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {opState.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              S/N: {telemetry?.serial_number || 'N/A'} · Mfg: {telemetry?.mfg_date || 'N/A'} · Cycles: {telemetry?.cycle_count !== null && telemetry?.cycle_count !== undefined ? telemetry.cycle_count : 'N/A'} · Rated: {telemetry?.rated_capacity_ah ? `${telemetry.rated_capacity_ah}Ah` : 'N/A'} ({telemetry?.max_current_limit_a ? `${telemetry.max_current_limit_a}A Max` : 'N/A'})
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right font-mono text-xs">
            <span className="text-slate-500 block">Telemetry Freshness:</span>
            <span
              className={`font-semibold ${
                freshness?.color === 'green'
                  ? 'text-emerald-400'
                  : freshness?.color === 'amber'
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {freshness?.label || 'Awaiting update'}
            </span>
          </div>
          <button
            onClick={() => onNavigate('connect')}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition"
          >
            Connection Settings
          </button>
        </div>
      </div>

      {/* Offline / Awaiting Telemetry Status Banner */}
      {soc === null && (
        <div className="bg-gradient-to-r from-amber-950/40 via-slate-900 to-slate-900 border border-amber-500/40 rounded-xl p-5 shadow-lg">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 bg-amber-500/20 border border-amber-500/40 rounded-lg text-amber-400 mt-0.5">
                <AlertOctagon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-amber-200">
                  {freshness?.status === 'DISCONNECTED'
                    ? 'Serial Port Disconnected'
                    : 'Awaiting Hardware Telemetry / Communication Verification'}
                </h3>
                <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                  The dashboard is currently awaiting valid Modbus RTU telemetry packets. If you are connected to physical hardware, verify:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 mt-2 text-xs text-slate-400 font-mono">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>Battery powered ON (RUN LED blinking green)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>RS485 A (D+) / B (D-) polarities match</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>Baud: 9600 8-E-1 or 8-N-1 (Slave ID 214 or 1)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>RJ45 Pins 1/2 (or 7/8 on secondary port)</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2.5 self-stretch md:self-auto flex-wrap">
              <button
                onClick={() => onNavigate('connect')}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs transition shadow-sm"
              >
                Configure Port / Auto-Detect
              </button>
              <button
                onClick={async () => {
                  try {
                    await api.toggleSimulation(true)
                    window.location.reload()
                  } catch (e) {
                    // ignore
                  }
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold rounded-lg text-xs transition"
              >
                Switch to Simulation Mode
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* SOC Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
          <div className="flex justify-between items-start">
            <span className="text-xs font-mono text-slate-400">State of Charge (SOC)</span>
            <Battery className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-slate-100">
              {soc !== null ? `${soc.toFixed(1)}` : 'N/A'}
            </span>
            <span className="text-sm font-mono text-slate-400">%</span>
          </div>
          {/* Progress bar */}
          <div className="mt-3 w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                soc !== null && soc < 20
                  ? 'bg-rose-500'
                  : soc !== null && soc > 90
                  ? 'bg-emerald-400'
                  : 'bg-cyan-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, soc ?? 0))}%` }}
            />
          </div>
          <div className="mt-2 text-[11px] font-mono text-slate-500 flex justify-between">
            <span>SOH: {soh !== null ? `${soh.toFixed(1)}%` : 'N/A'}</span>
            <span>Target: 100%</span>
          </div>
        </div>

        {/* Battery Voltage Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex justify-between items-start">
            <span className="text-xs font-mono text-slate-400">Pack Voltage</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-slate-100">
              {voltage !== null ? `${voltage.toFixed(1)}` : 'N/A'}
            </span>
            <span className="text-sm font-mono text-slate-400">V</span>
          </div>
          <div className="mt-3 text-[11px] font-mono text-slate-500 flex justify-between border-t border-slate-800/80 pt-2">
            <span>DC Bus: {electrical?.dc_bus_voltage ? `${electrical.dc_bus_voltage} V` : 'N/A'}</span>
            <span>Contactor: {electrical?.contactor_state || 'Open'}</span>
          </div>
        </div>

        {/* Battery Current & Power Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex justify-between items-start">
            <span className="text-xs font-mono text-slate-400">Pack Current & Power</span>
            {isCharging ? (
              <ArrowDownRight className="w-4 h-4 text-emerald-400" />
            ) : (
              <ArrowUpRight className="w-4 h-4 text-amber-400" />
            )}
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-slate-100">
              {current !== null ? `${current > 0 ? `+${current.toFixed(1)}` : current.toFixed(1)}` : 'N/A'}
            </span>
            <span className="text-sm font-mono text-slate-400">A</span>
          </div>
          <div className="mt-3 text-[11px] font-mono text-slate-500 flex justify-between border-t border-slate-800/80 pt-2">
            <span className="flex items-center gap-1">
              Power:{' '}
              <strong className="text-slate-200">
                {power !== null ? `${power.toFixed(3)} kW` : 'N/A'}
              </strong>
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">(P=V*I)</span>
          </div>
        </div>

        {/* Temperature & Delta V Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex justify-between items-start">
            <span className="text-xs font-mono text-slate-400">Temperature & Spread</span>
            <Thermometer className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-slate-100">
              {temp !== null ? `${temp.toFixed(1)}` : 'N/A'}
            </span>
            <span className="text-sm font-mono text-slate-400">°C</span>
          </div>
          <div className="mt-3 text-[11px] font-mono text-slate-500 flex justify-between border-t border-slate-800/80 pt-2">
            <span>
              ΔV Spread:{' '}
              <strong className="text-slate-200">
                {cells?.cell_voltage_delta_mv ? `${cells.cell_voltage_delta_mv} mV` : 'N/A'}
              </strong>
            </span>
            <span>Max T: {cells?.max_cell_temp ? `${cells.max_cell_temp}°C` : 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Secondary Dashboard Grid: Quick Cell View & Energy Counters */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cell Voltages Mini Distribution (First 16 cells) */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-slate-200 font-mono">
                Cell Voltage Distribution (16 Cells)
              </h3>
            </div>
            <button
              onClick={() => onNavigate('cells')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-mono underline"
            >
              Full Cell Details →
            </button>
          </div>

          <div className="grid grid-cols-8 gap-2 pt-2">
            {cells?.cell_voltages && cells.cell_voltages.length > 0 ? (
              cells.cell_voltages.map((v, i) => {
                const isMax = cells.max_cell_voltage === v
                const isMin = cells.min_cell_voltage === v
                const isBalancing = cells.balancing_active?.[i]
                return (
                  <div
                    key={i}
                    className={`p-2 rounded-lg border text-center transition font-mono ${
                      isMax
                        ? 'bg-amber-950/40 border-amber-600/60 text-amber-300'
                        : isMin
                        ? 'bg-blue-950/40 border-blue-600/60 text-blue-300'
                        : 'bg-slate-950 border-slate-800 text-slate-200'
                    }`}
                  >
                    <div className="text-[10px] text-slate-500 font-semibold flex items-center justify-center gap-0.5">
                      <span>C{i + 1}</span>
                      {isBalancing && (
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                      )}
                    </div>
                    <div className="text-xs font-bold mt-1">{v.toFixed(3)}</div>
                    <div className="text-[9px] text-slate-500">V</div>
                  </div>
                )
              })
            ) : (
              <div className="col-span-8 py-8 text-center text-slate-500 font-mono text-xs">
                No cell telemetry available. Connect BMS or start simulator.
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-4 text-xs font-mono text-slate-400 pt-2 border-t border-slate-800/80">
            <div>
              Min Cell:{' '}
              <strong className="text-blue-400">
                {cells?.min_cell_voltage ? `${cells.min_cell_voltage.toFixed(3)} V` : 'N/A'}
              </strong>
            </div>
            <div>
              Max Cell:{' '}
              <strong className="text-amber-400">
                {cells?.max_cell_voltage ? `${cells.max_cell_voltage.toFixed(3)} V` : 'N/A'}
              </strong>
            </div>
            <div>
              Average:{' '}
              <strong className="text-slate-200">
                {cells?.avg_cell_voltage ? `${cells.avg_cell_voltage.toFixed(3)} V` : 'N/A'}
              </strong>
            </div>
            <div>
              ΔV Spread:{' '}
              <strong className="text-cyan-400">
                {cells?.cell_voltage_delta_mv ? `${cells.cell_voltage_delta_mv} mV` : 'N/A'}
              </strong>
            </div>
          </div>
        </div>

        {/* Energy & Permissions Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Power className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-slate-200 font-mono">Energy & Safety Status</h3>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Cumulative Charged:</span>
              <span className="font-bold text-slate-100">
                {electrical?.charge_energy ? `${electrical.charge_energy} kWh` : 'N/A'}
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Cumulative Discharged:</span>
              <span className="font-bold text-slate-100">
                {electrical?.discharge_energy ? `${electrical.discharge_energy} kWh` : 'N/A'}
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Charge Permission:</span>
              <span
                className={`font-bold flex items-center gap-1 ${
                  telemetry?.charge_permission ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {telemetry?.charge_permission ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Granted
                  </>
                ) : (
                  'Restricted'
                )}
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Discharge Permission:</span>
              <span
                className={`font-bold flex items-center gap-1 ${
                  telemetry?.discharge_permission ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {telemetry?.discharge_permission ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Granted
                  </>
                ) : (
                  'Restricted'
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
