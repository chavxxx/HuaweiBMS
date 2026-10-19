import React from 'react'
import {
  Activity,
  AlertOctagon,
  BatteryCharging,
  Columns3,
  Cpu,
  Database,
  FileSpreadsheet,
  FileText,
  History,
  LayoutDashboard,
  Radio,
  Settings,
  ShieldCheck,
  Sliders,
  Terminal,
  Zap,
} from 'lucide-react'
import type { PageId } from '../types'

interface SidebarProps {
  currentPage: PageId
  onSelectPage: (page: PageId) => void
  activeAlarmCount: number
}

interface NavItem {
  id: PageId
  label: string
  icon: React.ComponentType<{ className?: string }>
  badge?: number
  category?: string
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  activeAlarmCount,
}) => {
  const navItems: NavItem[] = [
    // Category: Core
    { id: 'dashboard', label: '1. Dashboard', icon: LayoutDashboard, category: 'OVERVIEW' },
    { id: 'compare', label: '2. Battery Comparison', icon: Columns3, category: 'OVERVIEW' },
    { id: 'connect', label: '3. Connect Device', icon: Radio, category: 'OVERVIEW' },

    // Category: Telemetry
    { id: 'electrical', label: '4. Electrical Monitoring', icon: Zap, category: 'MONITORING' },
    { id: 'cells', label: '5. Cell & Module View', icon: BatteryCharging, category: 'MONITORING' },
    { id: 'alarms', label: '6. Alarms & Faults', icon: AlertOctagon, badge: activeAlarmCount, category: 'MONITORING' },

    // Category: Configuration
    { id: 'configuration', label: '6. Configuration', icon: Sliders, category: 'CONTROL' },
    { id: 'config_history', label: '7. Config Snapshots', icon: History, category: 'CONTROL' },

    // Category: Analytics & Logs
    { id: 'trends', label: '8. Historical Trends', icon: Activity, category: 'ANALYTICS' },
    { id: 'reports', label: '9. Reports & Export', icon: FileSpreadsheet, category: 'ANALYTICS' },

    // Category: Engineering
    { id: 'diagnostics', label: '10. Diagnostics & Trace', icon: Terminal, category: 'ENGINEERING' },
    { id: 'registers', label: '11. Register Database', icon: Database, category: 'ENGINEERING' },
    { id: 'settings', label: '12. App Settings', icon: Settings, category: 'ENGINEERING' },
    { id: 'audit', label: '13. Audit Log', icon: ShieldCheck, category: 'ENGINEERING' },
  ]

  let currentCategory = ''

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-[calc(100vh-4rem)] select-none">
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {navItems.map((item) => {
          const showCat = item.category && item.category !== currentCategory
          if (showCat) {
            currentCategory = item.category!
          }
          const isActive = currentPage === item.id
          const Icon = item.icon

          return (
            <React.Fragment key={item.id}>
              {showCat && (
                <div className="pt-3 pb-1 px-3 text-[10px] font-mono font-bold tracking-wider text-slate-500 uppercase">
                  {item.category}
                </div>
              )}
              <button
                onClick={() => onSelectPage(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-400 font-semibold border-l-2 border-cyan-400 shadow-sm shadow-cyan-950'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="px-1.5 py-0.2 bg-rose-600 text-white rounded text-[10px] font-mono font-bold animate-pulse">
                    {item.badge}
                  </span>
                )}
              </button>
            </React.Fragment>
          )
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 bg-slate-950/60 border-t border-slate-800 text-[10px] font-mono text-slate-500 flex flex-col gap-1">
        <div className="flex justify-between items-center">
          <span>Huawei EMS B1 V1.0</span>
          <span className="text-emerald-500 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" /> Online
          </span>
        </div>
        <div className="text-slate-600 truncate">CRC16 · RTU / Baud 9600</div>
      </div>
    </aside>
  )
}
