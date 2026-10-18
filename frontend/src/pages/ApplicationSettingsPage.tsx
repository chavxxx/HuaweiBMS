import React, { useEffect, useState } from 'react'
import {
  Bell,
  CheckCircle2,
  Database,
  ExternalLink,
  GitBranch,
  Moon,
  RefreshCw,
  Save,
  Settings,
  ShieldAlert,
  Sun,
} from 'lucide-react'
import { api } from '../services/api'
import type { UpdateCheckResult } from '../types'
import { SoftwareUpdateModal } from '../components/SoftwareUpdateModal'

export const ApplicationSettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<any>({
    low_soc_threshold: 15.0,
    high_temp_threshold: 50.0,
    max_delta_v_mv_threshold: 60.0,
    telemetry_stale_seconds: 5.0,
    theme: 'dark',
    retention_days: 30,
  })
  const [saving, setSaving] = useState(false)
  const [savedMsg, setSavedMsg] = useState<string | null>(null)
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false)
  const [updateInfo, setUpdateInfo] = useState<UpdateCheckResult | null>(null)
  const [checkingUpdates, setCheckingUpdates] = useState(false)

  const fetchUpdates = async () => {
    setCheckingUpdates(true)
    try {
      const res = await api.checkUpdates()
      setUpdateInfo(res)
    } catch {
      // ignore
    } finally {
      setCheckingUpdates(false)
    }
  }

  useEffect(() => {
    api.getSettings().then((s) => {
      if (s && Object.keys(s).length > 0) {
        setSettings((prev: any) => ({ ...prev, ...s }))
      }
    })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSavedMsg(null)
    try {
      await api.updateSettings(settings)
      setSavedMsg('Settings saved successfully.')
    } catch (e: any) {
      setSavedMsg(`Error: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Settings className="w-5 h-5 text-cyan-400" />
            <span>Application Settings & Operator Warning Thresholds</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure local UI notification limits, data retention policies, and telemetry staleness timers.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 shadow-lg shadow-cyan-500/20"
        >
          <Save className="w-3.5 h-3.5" />
          <span>{saving ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>

      {savedMsg && (
        <div className="p-3 bg-emerald-950/50 border border-emerald-600 rounded-lg text-emerald-300 text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{savedMsg}</span>
        </div>
      )}

      {/* Safety Notice Banner */}
      <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex items-start gap-3 text-xs font-mono">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-slate-300 space-y-1">
          <span className="font-bold text-slate-200">Independent Software Alerts Notice:</span>
          <p className="text-slate-400 font-sans text-[11px] leading-relaxed">
            The warning thresholds below trigger local in-app warnings and alerts for the operator. They do
            <strong> NOT </strong> replace or override the Huawei BMS's factory hardware protection mechanisms
            and safety interlocks.
          </p>
        </div>
      </div>

      {/* Thresholds Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5 font-mono text-xs">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3 text-sm font-bold text-slate-200">
          <Bell className="w-4 h-4 text-cyan-400" />
          <span>Telemetry Alert Thresholds</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-slate-400 block mb-1">Low SOC Warning Threshold (%)</label>
            <input
              type="number"
              min={1}
              max={50}
              value={settings.low_soc_threshold ?? 15}
              onChange={(e) =>
                setSettings({ ...settings, low_soc_threshold: Number(e.target.value) })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              Triggers visual alert when battery falls below this level.
            </span>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">High Cell Temperature Alert (°C)</label>
            <input
              type="number"
              min={30}
              max={65}
              value={settings.high_temp_threshold ?? 50}
              onChange={(e) =>
                setSettings({ ...settings, high_temp_threshold: Number(e.target.value) })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              Triggers thermal warning prior to hardware shutdown.
            </span>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">
              Cell Voltage Spread ΔV Warning (mV)
            </label>
            <input
              type="number"
              min={10}
              max={150}
              value={settings.max_delta_v_mv_threshold ?? 60}
              onChange={(e) =>
                setSettings({ ...settings, max_delta_v_mv_threshold: Number(e.target.value) })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              Cell imbalance alert threshold between highest and lowest cell.
            </span>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">
              Telemetry Staleness Threshold (seconds)
            </label>
            <input
              type="number"
              min={2}
              max={30}
              value={settings.telemetry_stale_seconds ?? 5}
              onChange={(e) =>
                setSettings({ ...settings, telemetry_stale_seconds: Number(e.target.value) })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              Time elapsed before telemetry readings are flagged as stale.
            </span>
          </div>
        </div>
      </div>

      {/* Database Retention Policy */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 font-mono text-xs">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3 text-sm font-bold text-slate-200">
          <Database className="w-4 h-4 text-cyan-400" />
          <span>Local Storage & Retention Settings</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-slate-400 block mb-1">Historical Retention Period (Days)</label>
            <select
              value={settings.retention_days ?? 30}
              onChange={(e) =>
                setSettings({ ...settings, retention_days: Number(e.target.value) })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            >
              <option value={7}>7 Days (Small disk)</option>
              <option value={30}>30 Days (Standard)</option>
              <option value={90}>90 Days (Quarterly)</option>
              <option value={365}>365 Days (Full Year)</option>
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1">UI Theme Mode</label>
            <select
              value={settings.theme ?? 'dark'}
              onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            >
              <option value="dark">Industrial Dark (Default)</option>
              <option value="light">High-Contrast Light</option>
            </select>
          </div>
        </div>
      </div>

      {/* Software Version & Git Repository Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            <span>Software Version & Git Repository</span>
          </div>
          <span className="text-[11px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded font-bold">
            v1.0.5
          </span>
        </div>

        <p className="text-slate-400 font-sans text-xs">
          Synchronize HuaweiBMS with the latest updates, bug fixes, and battery hardware presets directly from the GitHub repository.
        </p>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="text-slate-400 text-xs font-mono">
            Repository:{' '}
            <a
              href="https://github.com/chavxxx/HuaweiBMS"
              target="_blank"
              rel="noreferrer"
              className="text-cyan-400 underline hover:text-cyan-300 ml-1 inline-flex items-center gap-1"
            >
              github.com/chavxxx/HuaweiBMS
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <button
            onClick={() => {
              setIsUpdateModalOpen(true)
              fetchUpdates()
            }}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 border border-cyan-800/60"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Check for Updates</span>
          </button>
        </div>
      </div>

      {/* Software Update Modal */}
      <SoftwareUpdateModal
        isOpen={isUpdateModalOpen}
        onClose={() => setIsUpdateModalOpen(false)}
        userRole="ADMINISTRATOR"
        updateInfo={updateInfo}
        loading={checkingUpdates}
        onRefreshCheck={fetchUpdates}
      />
    </div>
  )
}

