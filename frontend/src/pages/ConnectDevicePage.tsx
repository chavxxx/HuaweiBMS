import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Layers,
  Radio,
  RefreshCw,
  RotateCw,
  Server,
  Settings,
  ShieldCheck,
  Usb,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { api } from '../services/api'
import type { SerialPortInfo } from '../types'

interface ConnectDevicePageProps {
  onRefreshTelemetry: () => void
}

export const ConnectDevicePage: React.FC<ConnectDevicePageProps> = ({ onRefreshTelemetry }) => {
  const [ports, setPorts] = useState<SerialPortInfo[]>([])
  const [loadingPorts, setLoadingPorts] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [status, setStatus] = useState<any>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Form State
  const [selectedPort, setSelectedPort] = useState('')
  const [baudrate, setBaudrate] = useState<number>(9600)
  const [bytesize, setBytesize] = useState<number>(8)
  const [parity, setParity] = useState<string>('E')
  const [stopbits, setStopbits] = useState<number>(1)
  const [slaveId, setSlaveId] = useState<number>(214)
  const [timeout, setTimeoutVal] = useState<number>(1.0)
  const [interFrameDelay, setInterFrameDelay] = useState<number>(0.02)
  const [rs485Rts, setRs485Rts] = useState<boolean>(false)
  const [autoReconnect, setAutoReconnect] = useState<boolean>(true)

  const loadPorts = async () => {
    setLoadingPorts(true)
    setErrorMsg(null)
    try {
      const list = await api.listPorts()
      setPorts(list)
      if (list.length > 0 && !selectedPort) {
        setSelectedPort(list[0].device)
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to enumerate serial ports')
    } finally {
      setLoadingPorts(false)
    }
  }

  const loadStatus = async () => {
    try {
      const s = await api.getConnectionStatus()
      setStatus(s)
    } catch (e) {
      // ignore
    }
  }

  useEffect(() => {
    loadPorts()
    loadStatus()
    const timer = setInterval(loadStatus, 3000)
    return () => clearInterval(timer)
  }, [])

  const handleApplyEMS4805Preset = () => {
    setBaudrate(9600)
    setBytesize(8)
    setParity('E')
    setStopbits(1)
    setSlaveId(214)
    setTimeoutVal(1.0)
    setInterFrameDelay(0.035)
    setSuccessMsg('Applied Huawei ESM Standalone Preset: 9600 8-E-1, Slave ID 214 (0xD6)')
  }

  const handleApplyCascadePreset = () => {
    setBaudrate(9600)
    setBytesize(8)
    setParity('E')
    setStopbits(1)
    setSlaveId(1)
    setTimeoutVal(1.0)
    setInterFrameDelay(0.035)
    setSuccessMsg('Applied Huawei ESM Cascade Bank Preset: 9600 8-E-1, Slave ID 1 (DIP #1)')
  }

  const handleApplyResidentialPreset = () => {
    setBaudrate(9600)
    setBytesize(8)
    setParity('N')
    setStopbits(1)
    setSlaveId(1)
    setTimeoutVal(1.0)
    setInterFrameDelay(0.035)
    setSuccessMsg('Applied Huawei Residential LUNA2000 Preset: 9600 8-N-1, Slave ID 1')
  }

  const handleConnect = async () => {
    if (!selectedPort) {
      setErrorMsg('Please select a serial port device path.')
      return
    }
    setConnecting(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const res = await api.connectPort({
        port: selectedPort,
        baudrate,
        bytesize,
        parity,
        stopbits,
        timeout,
        inter_frame_delay: interFrameDelay,
        slave_id: slaveId,
        rs485_rts_control: rs485Rts,
        auto_reconnect: autoReconnect,
        use_simulation: false,
      })
      if (res.active_slave_id && res.active_slave_id !== slaveId) {
        setSlaveId(res.active_slave_id)
      }
      setSuccessMsg(res.message)
      await loadStatus()
      onRefreshTelemetry()
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to connect to serial port')
    } finally {
      setConnecting(false)
    }
  }

  const handleDisconnect = async () => {
    try {
      await api.disconnectPort()
      setSuccessMsg('Disconnected from serial port.')
      await loadStatus()
      onRefreshTelemetry()
    } catch (err: any) {
      setErrorMsg(err.message)
    }
  }

  const handleToggleSim = async (enable: boolean) => {
    try {
      const res = await api.toggleSimulation(enable)
      setSuccessMsg(res.message)
      await loadStatus()
      onRefreshTelemetry()
    } catch (err: any) {
      setErrorMsg(err.message)
    }
  }

  const isSim = status?.is_simulation ?? true
  const isConn = status?.is_connected ?? false

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Top Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400" />
            <span>Serial Connection & Port Discovery</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure direct USB-to-RS485 serial communication with Huawei EMS B1 BMS.
          </p>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-3">
          {isSim ? (
            <div className="bg-amber-950/80 border border-amber-600/60 text-amber-300 px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2">
              <Cpu className="w-4 h-4 animate-spin text-amber-400" />
              <span>SIMULATED BMS ACTIVE</span>
            </div>
          ) : isConn ? (
            <div className="bg-emerald-950/80 border border-emerald-600/60 text-emerald-300 px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>
                CONNECTED ({status?.port} · Slave {status?.slave_id ?? slaveId} · {status?.baudrate ?? baudrate} 8{status?.parity ?? parity}{status?.stopbits ?? stopbits})
              </span>
            </div>
          ) : (
            <div className="bg-slate-800 border border-slate-700 text-slate-400 px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2">
              <WifiOff className="w-4 h-4" />
              <span>DISCONNECTED</span>
            </div>
          )}
        </div>
      </div>

      {/* Discovered Serial Ports Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Usb className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-slate-200 font-mono">
              Available System Serial Ports ({ports.length})
            </h3>
          </div>
          <button
            onClick={loadPorts}
            disabled={loadingPorts}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold font-mono transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingPorts ? 'animate-spin' : ''}`} />
            <span>Refresh Ports</span>
          </button>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Select</th>
                <th className="py-2.5 px-3">Device Path</th>
                <th className="py-2.5 px-3">Manufacturer / Description</th>
                <th className="py-2.5 px-3">Hardware ID</th>
                <th className="py-2.5 px-3 text-right">RS485 Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {ports.map((p) => {
                const isSelected = selectedPort === p.device
                return (
                  <tr
                    key={p.device}
                    onClick={() => setSelectedPort(p.device)}
                    className={`cursor-pointer transition ${
                      isSelected
                        ? 'bg-cyan-950/40 text-cyan-200'
                        : 'hover:bg-slate-800/50 text-slate-300'
                    }`}
                  >
                    <td className="py-2 px-3">
                      <input
                        type="radio"
                        name="portSelection"
                        checked={isSelected}
                        onChange={() => setSelectedPort(p.device)}
                        className="text-cyan-500 bg-slate-900 border-slate-700 focus:ring-0"
                      />
                    </td>
                    <td className="py-2 px-3 font-bold text-slate-100">{p.device}</td>
                    <td className="py-2 px-3 text-slate-300">{p.description}</td>
                    <td className="py-2 px-3 text-slate-500 text-[11px] truncate max-w-xs">
                      {p.hwid || 'N/A'}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {p.is_rs485_candidate ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700/60 text-[10px] font-bold">
                          RS485 Adapter
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[10px]">Serial Port</span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {ports.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-500 text-xs">
                    No physical serial ports detected. Plug in USB-to-RS485 adapter or use Simulator below.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Serial Communication Settings Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Settings className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-slate-200 font-mono">
              Communication Parameters (Modbus RTU / RS485)
            </h3>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleApplyEMS4805Preset}
              className="px-2.5 py-1 bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-600/60 rounded text-xs text-cyan-300 font-mono font-bold transition flex items-center gap-1.5"
              title="Factory standalone configuration without DIP address"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>ESM Standalone (Slave 214, 8-E-1)</span>
            </button>
            <button
              onClick={handleApplyCascadePreset}
              className="px-2.5 py-1 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-600/60 rounded text-xs text-emerald-300 font-mono font-bold transition flex items-center gap-1.5"
              title="Multi-battery cascade daisy chain with DIP switches set"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>ESM Cascade Bank (Slave 1, 8-E-1)</span>
            </button>
            <button
              onClick={handleApplyResidentialPreset}
              className="text-xs text-slate-400 hover:text-slate-300 underline font-mono"
            >
              Residential LUNA (Slave 1, 8-N-1)
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div>
            <label className="text-slate-400 block mb-1">Target Port Path</label>
            <input
              type="text"
              value={selectedPort}
              onChange={(e) => setSelectedPort(e.target.value)}
              placeholder="/dev/ttyUSB0 or COM3"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Baud Rate</label>
            <select
              value={baudrate}
              onChange={(e) => setBaudrate(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value={9600}>9600 (Huawei Standard)</option>
              <option value={19200}>19200</option>
              <option value={38400}>38400</option>
              <option value={57600}>57600</option>
              <option value={115200}>115200</option>
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Modbus Slave ID (Device Address)</label>
            <input
              type="number"
              min={1}
              max={247}
              value={slaveId}
              onChange={(e) => setSlaveId(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Parity</label>
            <select
              value={parity}
              onChange={(e) => setParity(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="E">Even (E) - Huawei ESM-48150B1 / 4805B1 Verified</option>
              <option value="N">None (N) - LUNA2000 Standard</option>
              <option value="O">Odd (O)</option>
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Data Bits / Stop Bits</label>
            <div className="flex gap-2">
              <select
                value={bytesize}
                onChange={(e) => setBytesize(Number(e.target.value))}
                className="w-1/2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value={8}>8 Bits</option>
                <option value={7}>7 Bits</option>
              </select>
              <select
                value={stopbits}
                onChange={(e) => setStopbits(Number(e.target.value))}
                className="w-1/2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value={1}>1 Stop Bit</option>
                <option value={2}>2 Stop Bits</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Response Timeout (seconds)</label>
            <input
              type="number"
              step={0.1}
              min={0.2}
              max={10.0}
              value={timeout}
              onChange={(e) => setTimeoutVal(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="rs485Rts"
              checked={rs485Rts}
              onChange={(e) => setRs485Rts(e.target.checked)}
              className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-0"
            />
            <label htmlFor="rs485Rts" className="text-slate-300 cursor-pointer">
              RS485 Half-Duplex RTS Direction Control
            </label>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="autoReconnect"
              checked={autoReconnect}
              onChange={(e) => setAutoReconnect(e.target.checked)}
              className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-0"
            />
            <label htmlFor="autoReconnect" className="text-slate-300 cursor-pointer">
              Auto-reconnect with exponential backoff
            </label>
          </div>
        </div>

        {/* Feedback Messages */}
        {errorMsg && (
          <div className="p-3 bg-rose-950/50 border border-rose-600/60 rounded-lg text-rose-300 text-xs font-mono flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-3 bg-emerald-950/50 border border-emerald-600/60 rounded-lg text-emerald-300 text-xs font-mono flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Actions Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <button
              onClick={handleConnect}
              disabled={connecting || !selectedPort}
              className={`px-5 py-2 rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 ${
                selectedPort && !connecting
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed'
              }`}
            >
              {connecting ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : (
                <>
                  <Radio className="w-4 h-4" />
                  <span>Connect to Hardware RS485</span>
                </>
              )}
            </button>

            {isConn && (
              <button
                onClick={handleDisconnect}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold font-mono transition"
              >
                Disconnect
              </button>
            )}
          </div>

          {/* Simulator Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-xs font-mono">No hardware connected?</span>
            <button
              onClick={() => handleToggleSim(!isSim)}
              className={`px-4 py-2 rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 ${
                isSim
                  ? 'bg-amber-950 border border-amber-600 text-amber-300'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
              }`}
            >
              <Cpu className="w-4 h-4 text-amber-400" />
              <span>{isSim ? 'Using Virtual Simulator' : 'Switch to Virtual Simulator'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Verified Hardware Wiring & Connection Guide */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-bold text-slate-100 font-mono">
            Huawei EMS-4805B1 Physical Hardware Specifications & Wiring Guide
          </h3>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed font-sans">
          The Huawei EMS-4805B1 / ESM-4805B1 BoostLi battery pack communicates over half-duplex RS485 via RJ45 COM ports (<span className="text-cyan-300 font-mono">COM_IN</span> and <span className="text-cyan-300 font-mono">COM_OUT</span>).
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
            <h4 className="font-bold text-cyan-300 text-[11px] uppercase tracking-wider">RJ45 Pinout Configuration</h4>
            <ul className="space-y-1.5 text-slate-300">
              <li className="flex items-center justify-between border-b border-slate-900 pb-1">
                <span>Pins 1 &amp; 4:</span>
                <span className="text-emerald-400 font-bold">RS485+ (A+) &rarr; Connect to Adapter A+</span>
              </li>
              <li className="flex items-center justify-between border-b border-slate-900 pb-1">
                <span>Pins 2 &amp; 5:</span>
                <span className="text-emerald-400 font-bold">RS485- (B-) &rarr; Connect to Adapter B-</span>
              </li>
              <li className="flex items-center justify-between border-b border-slate-900 pb-1">
                <span>Pins 3 &amp; 6:</span>
                <span className="text-slate-400">GND / NC &rarr; Connect to Adapter GND (optional ground ref)</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Pins 7 &amp; 8:</span>
                <span className="text-slate-500">CAN-H / CAN-L (CAN bus only, leave disconnected for RS485)</span>
              </li>
            </ul>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
            <h4 className="font-bold text-cyan-300 text-[11px] uppercase tracking-wider">Verified Operating Parameters</h4>
            <ul className="space-y-1.5 text-slate-300">
              <li className="flex items-center justify-between border-b border-slate-900 pb-1">
                <span>Modbus Slave ID:</span>
                <span className="text-cyan-300 font-bold">214 (0xD6) Standalone / 1..16 Cascade</span>
              </li>
              <li className="flex items-center justify-between border-b border-slate-900 pb-1">
                <span>Serial Framing:</span>
                <span className="text-cyan-300 font-bold">9600 Baud, 8 Data Bits, Even Parity (8-E-1), 1 Stop Bit</span>
              </li>
              <li className="flex items-center justify-between border-b border-slate-900 pb-1">
                <span>Function Code:</span>
                <span className="text-cyan-300 font-bold">FC 0x03 (Read Holding Registers)</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Pack Topology:</span>
                <span className="text-emerald-400 font-bold">16 LiFePO4 Cells in Series (51.2V Nom / 53.5V Rest)</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
