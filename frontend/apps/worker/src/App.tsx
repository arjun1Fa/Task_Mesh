import React, { useState, useEffect, useCallback } from 'react'
import { WorkerHeader } from './components/WorkerHeader'
import { WorkerSidebar, WorkerPage } from './components/WorkerSidebar'
import { WorkerOverview } from './components/WorkerOverview'
import { WorkerHardware } from './components/WorkerHardware'
import { WorkerTasks } from './components/WorkerTasks'
import { WorkerPool } from './components/WorkerPool'
import { WorkerNetwork } from './components/WorkerNetwork'
import { WorkerLogs } from './components/WorkerLogs'
import { WorkerSettings } from './components/WorkerSettings'
import { workerApi } from './api/workerClient'
import type { WorkerOverview as WorkerOverviewType, WorkerIdentity } from '@shared/types'
import { AlertCircle, RefreshCw, Server } from 'lucide-react'
import '@shared/styles/theme.css'

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<WorkerPage>('overview')
  const [identity, setIdentity] = useState<WorkerIdentity | null>(null)
  const [overview, setOverview] = useState<WorkerOverviewType | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isOffline, setIsOffline] = useState<boolean>(false)

  // Fetch local node state from the daemon running on this machine
  const refreshWorkerData = useCallback(async () => {
    try {
      const [idRes, ovRes] = await Promise.all([
        workerApi.getIdentity(),
        workerApi.getOverview(),
      ])
      setIdentity(idRes)
      setOverview(ovRes)
      setIsOffline(false)
    } catch (err) {
      console.warn('Worker daemon not reachable:', err)
      setIsOffline(true)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshWorkerData()
    const timer = setInterval(refreshWorkerData, 3000)
    return () => clearInterval(timer)
  }, [refreshWorkerData])

  if (isOffline && !overview) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-main)',
          padding: '2rem',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '1rem',
          }}
        >
          <AlertCircle size={28} color="var(--status-failed)" />
        </div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Worker Node Agent Daemon Unreachable
        </h2>
        <p style={{ color: 'var(--text-dim)', maxWidth: '480px', fontSize: '0.85rem', lineHeight: '1.5', marginBottom: '1.5rem' }}>
          The Worker Agent Console is trying to connect to the local Node Agent API at{' '}
          <code style={{ color: 'var(--accent-cyan)' }}>/api/worker/identity</code>. Ensure the TaskMesh worker daemon is active on this computer:
        </p>
        <div
          style={{
            backgroundColor: '#0a0b0e',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.75rem 1.25rem',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            color: 'var(--accent-green)',
            marginBottom: '1.5rem',
          }}
        >
          python -m taskmesh.node.agent --node-id node-alpha --orchestrator-url ws://127.0.0.1:8000/v1/ws/nodes --console-port 8081
        </div>
        <button className="btn btn-primary btn-sm" onClick={refreshWorkerData} disabled={isLoading}>
          <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
          <span>Retry Connection</span>
        </button>
      </div>
    )
  }

  return (
    <div className="app-container">
      {/* Worker Top Header (Locked to this machine's node identity) */}
      <WorkerHeader
        identity={identity}
        overview={overview}
        isOnline={!isOffline}
      />

      <div className="layout-body">
        {/* Worker Local Navigation */}
        <WorkerSidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          activeTasksCount={overview?.active_tasks ?? 0}
          concurrency={overview?.worker_concurrency ?? 4}
        />

        {/* Worker Main Workspace */}
        <main className="content-pane">
          {currentPage === 'overview' && (
            <WorkerOverview
              overview={overview}
              onRefresh={refreshWorkerData}
              onNavigateToHardware={() => setCurrentPage('hardware')}
              onNavigateToTasks={() => setCurrentPage('tasks')}
              onNavigateToSettings={() => setCurrentPage('settings')}
            />
          )}

          {currentPage === 'hardware' && <WorkerHardware />}

          {currentPage === 'tasks' && <WorkerTasks />}

          {currentPage === 'pool' && <WorkerPool />}

          {currentPage === 'network' && <WorkerNetwork />}

          {currentPage === 'logs' && <WorkerLogs />}

          {currentPage === 'settings' && (
            <WorkerSettings
              overview={overview}
              onRefresh={refreshWorkerData}
            />
          )}
        </main>
      </div>
    </div>
  )
}
export default App

