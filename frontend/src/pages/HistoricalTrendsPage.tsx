import React, { useEffect, useState } from 'react'
import {
  Activity,
  Battery,
  Calendar,
  Clock,
  Download,
  RefreshCw,
  Thermometer,
  Zap,
} from 'lucide-react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../services/api'

export const HistoricalTrendsPage: React.FC = () => {
  const [dataPoints, setDataPoints] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [timeRangeHours, setTimeRangeHours] = useState(6)

  const loadData = async () => {
    setLoading(true)
    const startTime = Date.now() / 1000 - timeRangeHours * 3600
    try {
      const points = await api.queryHistory(startTime, undefined, 400)
      const formatted = points.map((p) => ({
        timestamp: p.timestamp,
        time: new Date(p.timestamp * 1000).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
        soc: p.soc,
        voltage: p.total_voltage,
        current: p.current,
        power: p.power,
        temp: p.temperature,
        deltaMv: p.cell_voltage_delta ? p.cell_voltage_delta * 1000 : null,
      }))
      setDataPoints(formatted)
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const timer = setInterval(loadData, 5000)
    return () => clearInterval(timer)
  }, [timeRangeHours])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            <span>Historical Telemetry & Multi-Parameter Trends</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Analyze battery electrochemistry behavior, thermal envelopes, and charge/discharge curves over time.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400">Time Range:</span>
          <div className="flex bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            {[1, 6, 24, 72].map((hrs) => (
              <button
                key={hrs}
                onClick={() => setTimeRangeHours(hrs)}
                className={`px-3 py-1 rounded text-xs transition ${
                  timeRangeHours === hrs
                    ? 'bg-cyan-500 text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {hrs === 72 ? '3 Days' : `${hrs}h`}
              </button>
            ))}
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 ml-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Chart 1: State of Charge (SOC) & Pack Voltage */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
            <Battery className="w-4 h-4 text-cyan-400" />
            <span>State of Charge (SOC %) and Pack Voltage (V)</span>
          </h3>
          <span className="text-[11px] text-slate-500">{dataPoints.length} points plotted</span>
        </div>

        <div className="h-64 w-full pt-2">
          {dataPoints.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dataPoints}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis
                  yAxisId="left"
                  stroke="#06b6d4"
                  fontSize={10}
                  domain={[0, 100]}
                  unit="%"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#f59e0b"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  unit="V"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#020617',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="soc"
                  name="State of Charge (%)"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="voltage"
                  name="Pack Voltage (V)"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500">
              Gathering historical records...
            </div>
          )}
        </div>
      </div>

      {/* Chart 2: Power (kW) and Current (A) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs">
        <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Battery Current (A) & Instantaneous Power (kW)</span>
        </h3>

        <div className="h-64 w-full pt-2">
          {dataPoints.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dataPoints}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis
                  yAxisId="left"
                  stroke="#10b981"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  unit="A"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#ec4899"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  unit="kW"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#020617',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="current"
                  name="Pack Current (A)"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="power"
                  name="Power (kW)"
                  stroke="#ec4899"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500">
              Gathering historical records...
            </div>
          )}
        </div>
      </div>

      {/* Chart 3: Temperature (°C) & Cell Voltage Delta (mV) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 font-mono text-xs">
        <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
          <Thermometer className="w-4 h-4 text-rose-400" />
          <span>Thermal Profile (°C) & Cell Voltage Spread ΔV (mV)</span>
        </h3>

        <div className="h-64 w-full pt-2">
          {dataPoints.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dataPoints}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis
                  yAxisId="left"
                  stroke="#f43f5e"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  unit="°C"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#8b5cf6"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  unit="mV"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#020617',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="temp"
                  name="Temperature (°C)"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="deltaMv"
                  name="Cell Spread ΔV (mV)"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500">
              Gathering historical records...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
