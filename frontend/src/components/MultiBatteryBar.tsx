import React, { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Battery,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Layers,
  Pause,
  Play,
  RefreshCw,
} from 'lucide-react'
import { api } from '../services/api'
import type { BatterySummaryItem, PageId } from '../types'

interface MultiBatteryBarProps {
  onSelectBattery?: (slaveId: number) => void
  onNavigateCompare?: () => void
  activeSlaveId: number
}

export const MultiBatteryBar: React.FC<MultiBatteryBarProps> = ({
  onSelectBattery,
  onNavigateCompare,
  activeSlaveId,
}) => {
  const [batteries, setBatteries] = useState<BatterySummaryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [autoCycle, setAutoCycle] = useState(false)
  const [cycleProgress, setCycleProgress] = useState(0)

  const cycleTimerRef = useRef<any>(null)
  const progressTimerRef = useRef<any>(null)

  const fetchBatteries = async () => {
    try {
      setLoading(true)
      const res = await api.listBatteries()
      if (res && res.batteries) {
        setBatteries(res.batteries)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBatteries()
    const interval = setInterval(fetchBatteries, 5000)
    return () => clearInterval(interval)
  }, [])

  // Auto-cycle effect: advances every 6 seconds when active
  useEffect(() => {
    if (!autoCycle || batteries.length <= 1) {
      if (cycleTimerRef.current) clearInterval(cycleTimerRef.current)
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
      setCycleProgress(0)
      return
    }

    const CYCLE_DURATION_MS = 6000
    const INTERVAL_MS = 100
    let elapsed = 0

    progressTimerRef.current = setInterval(() => {
      elapsed += INTERVAL_MS
      setCycleProgress(Math.min(100, Math.round((elapsed / CYCLE_DURATION_MS) * 100)))
      if (elapsed >= CYCLE_DURATION_MS) {
        elapsed = 0
        setCycleProgress(0)
        // Advance to next battery
        handleNext()
      }
    }, INTERVAL_MS)

    return () => {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
    }
  }, [autoCycle, activeSlaveId, batteries])

  const handleSelect = async (slaveId: number) => {
    try {
      await api.selectBattery(slaveId)
      if (onSelectBattery) onSelectBattery(slaveId)
      fetchBatteries()
    } catch {
      // ignore
    }
  }

  const handlePrev = () => {
    if (batteries.length === 0) return
    const idx = batteries.findIndex((b) => b.slave_id === activeSlaveId)
    const prevIdx = idx <= 0 ? batteries.length - 1 : idx - 1
    handleSelect(batteries[prevIdx].slave_id)
  }

  const handleNext = () => {
    if (batteries.length === 0) return
    const idx = batteries.findIndex((b) => b.slave_id === activeSlaveId)
    const nextIdx = idx >= batteries.length - 1 ? 0 : idx + 1
    handleSelect(batteries[nextIdx].slave_id)
  }

  const currentBattery = batteries.find((b) => b.slave_id === activeSlaveId) || batteries[0]

  return (
    <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
      {/* Left: Active Battery Stepper ("View one by one") */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-slate-400 font-bold uppercase text-[11px] tracking-wider mr-1">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Battery Fleet ({batteries.length} Packs):</span>
        </div>

        {/* Stepper controls */}
        <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 shadow-inner">
          <button
            onClick={handlePrev}
            title="View Previous Battery"
            className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <div className="px-2.5 py-0.5 flex items-center gap-2">
            <span className="font-bold text-slate-100">
              {currentBattery ? currentBattery.name : `Battery #${activeSlaveId}`}
            </span>
            {currentBattery && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
                ID: {currentBattery.slave_id}
              </span>
            )}
            {currentBattery?.soc !== undefined && (
              <span className="text-slate-300">
                · {currentBattery.soc}% SOC · {currentBattery.total_voltage}V
              </span>
            )}
          </div>

          <button
            onClick={handleNext}
            title="View Next Battery"
            className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Auto-Cycle Slideshow Button */}
        <button
          onClick={() => setAutoCycle(!autoCycle)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition ${
            autoCycle
              ? 'bg-cyan-950 text-cyan-300 border-cyan-500 shadow-sm shadow-cyan-950'
              : 'bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border-slate-700'
          }`}
          title={
            autoCycle
              ? 'Pause auto-cycling between batteries'
              : 'Auto-cycle and view all batteries one by one (every 6 seconds)'
          }
        >
          {autoCycle ? (
            <>
              <Pause className="w-3 h-3 text-cyan-400" />
              <span>Auto-Cycle ON ({Math.round(cycleProgress)}%)</span>
            </>
          ) : (
            <>
              <Play className="w-3 h-3 text-slate-400" />
              <span>Auto-Cycle</span>
            </>
          )}
        </button>
      </div>

      {/* Center / Right: Quick Pack Pills & Fleet Comparison Jump */}
      <div className="flex items-center gap-2 overflow-x-auto py-0.5">
        {batteries.map((b) => {
          const isActive = b.slave_id === activeSlaveId
          const hasAlarms = (b.alarm_count ?? 0) > 0 || (b.cell_voltage_delta_mv ?? 0) > 30.0

          return (
            <button
              key={b.slave_id}
              onClick={() => handleSelect(b.slave_id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono transition border ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 font-bold shadow-sm shadow-cyan-950'
                  : 'bg-slate-950/80 hover:bg-slate-800 text-slate-400 border-slate-800'
              }`}
            >
              <Battery className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>#{b.slave_id}</span>
              <span className="text-[10px] opacity-80">{b.soc}%</span>
              {hasAlarms && (
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              )}
            </button>
          )
        })}

        {onNavigateCompare && (
          <button
            onClick={onNavigateCompare}
            className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-bold font-mono transition ml-2 shadow-sm shadow-cyan-900/30"
          >
            <Columns3 className="w-3.5 h-3.5" />
            <span>Compare Tab</span>
          </button>
        )}
      </div>
    </div>
  )
}
