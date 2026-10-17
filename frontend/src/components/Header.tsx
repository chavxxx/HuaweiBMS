import React from 'react'
import {
  Activity,
  AlertTriangle,
  BatteryCharging,
  Cpu,
  Layers,
  Radio,
  Shield,
  Wifi,
  WifiOff,
} from 'lucide-react'
import type { FreshnessStatus, TelemetryData, UserRole } from '../types'

interface HeaderProps {
  telemetry: TelemetryData | null
  freshness: FreshnessStatus | null
  userRole: UserRole
  onRoleChange: (role: UserRole) => void
  onToggleSimulation: (enabled: boolean) => void
  onNavigateAlarms: () => void
}

export const Header: React.FC<HeaderProps> = ({
  telemetry,
  freshness,
  userRole,
  onRoleChange,
  onToggleSimulation,
  onNavigateAlarms,
}) => {
  const isSim = telemetry?.is_simulation ?? true
  const activeAlarmCount = telemetry?.active_alarm_codes?.length ?? 0

  const getFreshnessBadge = () => {
    if (!freshness) return null
    const colorClasses = {
      green: 'bg-emerald-950/80 text-emerald-400 border-emerald-600/50',
      amber: 'bg-amber-950/80 text-amber-400 border-amber-600/50 animate-pulse',
      red: 'bg-rose-950/80 text-rose-400 border-rose-600/50 animate-bounce',
      gray: 'bg-slate-900 text-slate-400 border-slate-700',
      yellow: 'bg-yellow-950/80 text-yellow-400 border-yellow-600/50',
    }
    const cls = colorClasses[freshness.color] || colorClasses.gray

    return (
      <div className={`px-2.5 py-1 rounded border text-xs font-mono font-medium flex items-center gap-1.5 ${cls}`}>
        <span className={`w-2 h-2 rounded-full ${freshness.color === 'green' ? 'bg-emerald-400' : 'bg-current'}`} />
        <span>{freshness.label}</span>
      </div>
    )
  }

  return (
    <header className="h-16 bg-slate-900/90 border-b border-slate-800 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Brand & Hardware Identity */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 text-white font-black text-sm tracking-tighter">
            HW
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <span>Huawei EMS B1 Battery Manager</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-cyan-800/60 font-semibold">
                RS485 Pro
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 font-mono">
              {telemetry?.device_model || 'Device Unverified'} · {telemetry?.firmware_version || 'FW: V100'}
            </p>
          </div>
        </div>

        {/* Simulation Banner / Physical Port Indicator */}
        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-800">
          {isSim ? (
            <div className="flex items-center gap-2 bg-amber-950/70 text-amber-300 border border-amber-600/60 px-3 py-1 rounded-md text-xs font-mono font-semibold">
              <Cpu className="w-3.5 h-3.5 text-amber-400 animate-spin" />
              <span>SIMULATED BMS (VIRTUAL)</span>
              <button
                onClick={() => onToggleSimulation(false)}
                className="ml-1 text-[10px] underline hover:text-white transition-colors"
              >
                Switch to Serial
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-emerald-950/70 text-emerald-300 border border-emerald-600/60 px-3 py-1 rounded-md text-xs font-mono font-semibold">
              <Radio className="w-3.5 h-3.5 text-emerald-400" />
              <span>PHYSICAL RS485 HARDWARE</span>
              <button
                onClick={() => onToggleSimulation(true)}
                className="ml-1 text-[10px] underline hover:text-white transition-colors"
              >
                Simulate
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Freshness, Alarms, and Role Controls */}
      <div className="flex items-center gap-3">
        {/* Freshness Badge */}
        {getFreshnessBadge()}

        {/* Active Alarms Pill */}
        {activeAlarmCount > 0 ? (
          <button
            onClick={onNavigateAlarms}
            className="flex items-center gap-1.5 px-3 py-1 bg-rose-950/90 hover:bg-rose-900 border border-rose-500/80 text-rose-300 rounded-md text-xs font-mono font-bold animate-pulse transition"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>{activeAlarmCount} ACTIVE ALARMS</span>
          </button>
        ) : (
          <div className="hidden lg:flex items-center gap-1 px-2.5 py-1 bg-slate-800/80 text-slate-400 border border-slate-700/60 rounded text-xs font-mono">
            <span>Alarms Clear</span>
          </div>
        )}

        {/* Role Selector */}
        <div className="flex items-center gap-2 bg-slate-800/90 border border-slate-700/80 rounded-md px-2.5 py-1">
          <Shield className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] text-slate-400 font-mono">Role:</span>
          <select
            value={userRole}
            onChange={(e) => onRoleChange(e.target.value as UserRole)}
            className="bg-transparent text-xs font-semibold text-slate-100 focus:outline-none cursor-pointer"
          >
            <option value="VIEWER" className="bg-slate-900 text-slate-200">
              Viewer (Read-Only)
            </option>
            <option value="OPERATOR" className="bg-slate-900 text-slate-200">
              Operator
            </option>
            <option value="ADMINISTRATOR" className="bg-slate-900 text-cyan-300 font-bold">
              Administrator (Writes Allowed)
            </option>
          </select>
        </div>
      </div>
    </header>
  )
}
