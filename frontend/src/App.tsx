import React, { useEffect, useRef, useState } from 'react'
import { Header } from './components/Header'
import { MultiBatteryBar } from './components/MultiBatteryBar'
import { Sidebar } from './components/Sidebar'
import { AlarmsFaultsPage } from './pages/AlarmsFaultsPage'
import { ApplicationSettingsPage } from './pages/ApplicationSettingsPage'
import { AuditLogPage } from './pages/AuditLogPage'
import { BatteryComparisonPage } from './pages/BatteryComparisonPage'
import { CellModuleMonitoringPage } from './pages/CellModuleMonitoringPage'
import { ConfigHistoryPage } from './pages/ConfigHistoryPage'
import { ConfigurationPage } from './pages/ConfigurationPage'
import { ConnectDevicePage } from './pages/ConnectDevicePage'
import { DashboardPage } from './pages/DashboardPage'
import { DiagnosticsPage } from './pages/DiagnosticsPage'
import { ElectricalMonitoringPage } from './pages/ElectricalMonitoringPage'
import { HistoricalTrendsPage } from './pages/HistoricalTrendsPage'
import { RegisterDatabasePage } from './pages/RegisterDatabasePage'
import { ReportsExportPage } from './pages/ReportsExportPage'
import { api } from './services/api'
import type { CellData, ElectricalData, FreshnessStatus, PageId, TelemetryData, UserRole } from './types'

export function App() {
  const [currentPage, setCurrentPage] = useState<PageId>('dashboard')
  const [userRole, setUserRole] = useState<UserRole>('ADMINISTRATOR')
  const [activeSlaveId, setActiveSlaveId] = useState<number>(1)
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [electrical, setElectrical] = useState<ElectricalData | null>(null)
  const [cells, setCells] = useState<CellData | null>(null)
  const [freshness, setFreshness] = useState<FreshnessStatus | null>(null)

  const wsRef = useRef<WebSocket | null>(null)

  // Fetch initial telemetry via REST fallback and setup WebSocket
  const fetchTelemetry = async () => {
    try {
      const data = await api.getLatestTelemetry()
      if (data) {
        setTelemetry(data.telemetry)
        setElectrical(data.electrical)
        setCells(data.cells)
        setFreshness(data.freshness)
      }
    } catch (e) {
      // ignore
    }
  }

  useEffect(() => {
    fetchTelemetry()

    // Establish WebSocket connection for real-time telemetry streaming
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`

    const connectWs = () => {
      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'TELEMETRY_UPDATE' || data.type === 'INITIAL_STATE') {
              if (data.telemetry) setTelemetry(data.telemetry)
              if (data.electrical) setElectrical(data.electrical)
              if (data.cells) setCells(data.cells)
              if (data.freshness) setFreshness(data.freshness)
            }
          } catch (err) {
            // ignore
          }
        }

        ws.onclose = () => {
          // Reconnect after 3s
          setTimeout(connectWs, 3000)
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch (err) {
        setTimeout(connectWs, 3000)
      }
    }

    connectWs()

    // Periodic heartbeat / polling fallback
    const pollTimer = setInterval(fetchTelemetry, 3000)

    return () => {
      clearInterval(pollTimer)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const handleToggleSimulation = async (enable: boolean) => {
    try {
      await api.toggleSimulation(enable)
      fetchTelemetry()
    } catch (e) {
      // ignore
    }
  }

  const activeAlarmCount = telemetry?.active_alarm_codes?.length ?? 0

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <Header
        telemetry={telemetry}
        freshness={freshness}
        userRole={userRole}
        onRoleChange={setUserRole}
        onToggleSimulation={handleToggleSimulation}
        onNavigateAlarms={() => setCurrentPage('alarms')}
      />

      {/* Multi-Battery Stepper Bar ("View all batteries one by one") */}
      <MultiBatteryBar
        activeSlaveId={activeSlaveId}
        onSelectBattery={(sid) => {
          setActiveSlaveId(sid)
          fetchTelemetry()
        }}
        onNavigateCompare={() => setCurrentPage('compare')}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          activeAlarmCount={activeAlarmCount}
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          {currentPage === 'dashboard' && (
            <DashboardPage
              telemetry={telemetry}
              electrical={electrical}
              cells={cells}
              freshness={freshness}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'compare' && (
            <BatteryComparisonPage
              userRole={userRole}
              activeSlaveId={activeSlaveId}
              onSelectBattery={(sid) => {
                setActiveSlaveId(sid)
                fetchTelemetry()
              }}
              onNavigatePage={setCurrentPage}
            />
          )}

          {currentPage === 'connect' && (
            <ConnectDevicePage onRefreshTelemetry={fetchTelemetry} />
          )}

          {currentPage === 'electrical' && (
            <ElectricalMonitoringPage
              telemetry={telemetry}
              electrical={electrical}
              freshness={freshness}
            />
          )}

          {currentPage === 'cells' && <CellModuleMonitoringPage cells={cells} />}

          {currentPage === 'alarms' && <AlarmsFaultsPage />}

          {currentPage === 'configuration' && (
            <ConfigurationPage
              userRole={userRole}
              onNavigateSnapshots={() => setCurrentPage('config_history')}
            />
          )}

          {currentPage === 'config_history' && (
            <ConfigHistoryPage
              userRole={userRole}
              onNavigateConfig={() => setCurrentPage('configuration')}
            />
          )}

          {currentPage === 'trends' && <HistoricalTrendsPage />}

          {currentPage === 'reports' && <ReportsExportPage />}

          {currentPage === 'diagnostics' && <DiagnosticsPage userRole={userRole} />}

          {currentPage === 'registers' && <RegisterDatabasePage />}

          {currentPage === 'settings' && <ApplicationSettingsPage />}

          {currentPage === 'audit' && <AuditLogPage />}
        </main>
      </div>
    </div>
  )
}

export default App
