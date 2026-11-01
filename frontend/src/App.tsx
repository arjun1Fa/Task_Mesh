import React, { useState, useEffect, useCallback } from 'react'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Header } from './components/common/Header'
import { Sidebar } from './components/common/Sidebar'
import type { OrchestratorPage } from './components/common/Sidebar'
import { WorkerSidebar } from './components/common/WorkerSidebar'
import type { WorkerPage } from './components/common/WorkerSidebar'
import { LoginModal } from './components/common/LoginModal'
import { SubmitTaskModal } from './components/orchestrator/SubmitTaskModal'
import { useDashboardSocket } from './websocket/useDashboardSocket'
import { api } from './api/client'
import type {
  ClusterHealth,
  DashboardEvent,
  NodeProfile,
  SchedulerDecision,
  Task
} from './types'

// Orchestrator Pages
import { GlobalOverview } from './components/orchestrator/GlobalOverview'
import { ClusterNodes } from './components/orchestrator/ClusterNodes'
import { LiveTaskMonitor } from './components/orchestrator/LiveTaskMonitor'
import { TaskQueue } from './components/orchestrator/TaskQueue'
import { SchedulingEngine } from './components/orchestrator/SchedulingEngine'
import { NetworkInference } from './components/orchestrator/NetworkInference'
import { WorkersView } from './components/orchestrator/WorkersView'
import { LogsEvents } from './components/orchestrator/LogsEvents'
import { DeadLetterQueue } from './components/orchestrator/DeadLetterQueue'
import { RecoveryHA } from './components/orchestrator/RecoveryHA'
import { UsersPermissions } from './components/orchestrator/UsersPermissions'
import { SystemConfig } from './components/orchestrator/SystemConfig'
import { SecurityAudit } from './components/orchestrator/SecurityAudit'
import { SystemHealth } from './components/orchestrator/SystemHealth'

// Worker Pages
import { WorkerOverviewPage } from './components/worker/WorkerOverviewPage'
import { WorkerHardwarePage } from './components/worker/WorkerHardwarePage'
import { WorkerTaskExecutionPage } from './components/worker/WorkerTaskExecutionPage'
import { WorkerPoolPage } from './components/worker/WorkerPoolPage'
import { WorkerNetworkPage } from './components/worker/WorkerNetworkPage'
import { WorkerLogsPage } from './components/worker/WorkerLogsPage'
import { WorkerSettingsPage } from './components/worker/WorkerSettingsPage'

const MainApp: React.FC = () => {
  const { user } = useAuth()

  // Interface switcher: 'orchestrator' | 'worker'
  const [currentInterface, setCurrentInterface] = useState<'orchestrator' | 'worker'>('orchestrator')

  // Page selection
  const [orchestratorPage, setOrchestratorPage] = useState<OrchestratorPage>('overview')
  const [workerPage, setWorkerPage] = useState<WorkerPage>('overview')

  // Modals
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [submitTaskModalOpen, setSubmitTaskModalOpen] = useState(false)

  // Cluster data
  const [health, setHealth] = useState<ClusterHealth | null>(null)
  const [nodes, setNodes] = useState<NodeProfile[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [decisions, setDecisions] = useState<SchedulerDecision[]>([])
  const [events, setEvents] = useState<DashboardEvent[]>([])

  const [activeWorkerId, setActiveWorkerId] = useState<string>('node-alpha')
  const [taskQueueCount, setTaskQueueCount] = useState<number>(0)
  const [dlqCount, setDlqCount] = useState<number>(0)

  // WebSocket Live Feed
  const { status: wsStatus } = useDashboardSocket({
    onEvent: (event: DashboardEvent) => {
      setEvents((prev) => [event, ...prev.slice(0, 99)])
      if (event.event_type === 'task_submitted') {
        setTaskQueueCount((prev) => prev + 1)
      } else if (event.event_type === 'task_dlq') {
        setDlqCount((prev) => prev + 1)
      }
    },
    onHealth: (healthData: any) => {
      if (healthData) {
        setHealth((prev) => ({ ...(prev || {} as any), ...healthData }))
        if (healthData.pending_tasks !== undefined) setTaskQueueCount(healthData.pending_tasks)
        if (healthData.dlq_tasks !== undefined) setDlqCount(healthData.dlq_tasks)
      }
    },
  })

  // Poll cluster overview periodically
  const fetchClusterMeta = useCallback(async () => {
    try {
      const [h, nList, tList, decList, dlq] = await Promise.all([
        api.getClusterHealth().catch(() => null),
        api.listNodes().catch(() => []),
        api.listTasks(undefined, 100).catch(() => []),
        api.getSchedulerDecisions(50).catch(() => []),
        api.listDlq().catch(() => []),
      ])

      if (h) {
        setHealth(h)
        setTaskQueueCount(h.pending_tasks || 0)
      }
      if (nList) {
        setNodes(nList)
        if (nList.length > 0) {
          const ids = nList.map((n) => n.id)
          if (!ids.includes(activeWorkerId)) {
            setActiveWorkerId(ids[0])
          }
        }
      }
      if (tList) setTasks(tList)
      if (decList) setDecisions(decList)
      if (dlq) setDlqCount(dlq.length)
    } catch (err) {
      console.error('Failed to fetch cluster metadata:', err)
    }
  }, [activeWorkerId])

  useEffect(() => {
    fetchClusterMeta()
    const interval = setInterval(fetchClusterMeta, 5000)
    return () => clearInterval(interval)
  }, [fetchClusterMeta])

  // If user has node_scope (worker operator), automatically select that node
  useEffect(() => {
    if (user?.role === 'worker_operator' && user.node_scope) {
      setActiveWorkerId(user.node_scope)
    }
  }, [user])

  const nodeList = nodes.map((n) => n.id)
  const clusterStatus = health?.status || 'healthy'

  const handleOpenWorkerConsole = (nodeId: string) => {
    setActiveWorkerId(nodeId)
    setCurrentInterface('worker')
    setWorkerPage('overview')
  }

  const renderOrchestratorPage = () => {
    switch (orchestratorPage) {
      case 'overview':
        return (
          <GlobalOverview
            health={health}
            nodes={nodes}
            tasks={tasks}
            onRefresh={fetchClusterMeta}
            onOpenSubmitModal={() => setSubmitTaskModalOpen(true)}
            onSelectNode={handleOpenWorkerConsole}
          />
        )
      case 'nodes':
        return (
          <ClusterNodes
            nodes={nodes}
            onRefresh={fetchClusterMeta}
            selectedNodeId={null}
            onClearSelectedNode={() => {}}
            onOpenWorkerConsole={handleOpenWorkerConsole}
          />
        )
      case 'live_monitor':
        return (
          <LiveTaskMonitor
            nodes={nodes}
            tasks={tasks}
            decisions={decisions}
            events={events}
            onSelectNode={handleOpenWorkerConsole}
          />
        )
      case 'tasks':
        return <TaskQueue />
      case 'scheduling':
        return <SchedulingEngine />
      case 'network':
        return <NetworkInference />
      case 'workers':
        return <WorkersView />
      case 'logs':
        return <LogsEvents />
      case 'dlq':
        return <DeadLetterQueue />
      case 'recovery':
        return <RecoveryHA />
      case 'users':
        return <UsersPermissions />
      case 'config':
        return <SystemConfig />
      case 'audit':
        return <SecurityAudit />
      case 'health':
        return <SystemHealth />
      default:
        return (
          <GlobalOverview
            health={health}
            nodes={nodes}
            tasks={tasks}
            onRefresh={fetchClusterMeta}
            onOpenSubmitModal={() => setSubmitTaskModalOpen(true)}
            onSelectNode={handleOpenWorkerConsole}
          />
        )
    }
  }

  const renderWorkerPage = () => {
    const targetNode = activeWorkerId || (nodeList.length > 0 ? nodeList[0] : 'node-alpha')
    switch (workerPage) {
      case 'overview':
        return <WorkerOverviewPage nodeId={targetNode} />
      case 'hardware':
        return <WorkerHardwarePage nodeId={targetNode} />
      case 'tasks':
        return <WorkerTaskExecutionPage nodeId={targetNode} />
      case 'pool':
        return <WorkerPoolPage nodeId={targetNode} />
      case 'network':
        return <WorkerNetworkPage nodeId={targetNode} />
      case 'logs':
        return <WorkerLogsPage nodeId={targetNode} />
      case 'settings':
        return <WorkerSettingsPage nodeId={targetNode} />
      default:
        return <WorkerOverviewPage nodeId={targetNode} />
    }
  }

  return (
    <div className="app-shell">
      {/* Top Header */}
      <Header
        currentInterface={currentInterface}
        onSwitchInterface={(ui) => setCurrentInterface(ui)}
        clusterStatus={clusterStatus}
        wsStatus={wsStatus}
        onOpenLogin={() => setLoginModalOpen(true)}
        activeWorkerId={activeWorkerId}
      />

      {/* Main Layout (Sidebar + Content) */}
      <div className="main-layout">
        {currentInterface === 'orchestrator' ? (
          <Sidebar
            currentPage={orchestratorPage}
            onSelectPage={(page) => setOrchestratorPage(page)}
            taskQueueCount={taskQueueCount}
            dlqCount={dlqCount}
            nodeCount={nodeList.length}
          />
        ) : (
          <WorkerSidebar
            currentPage={workerPage}
            onSelectPage={(page) => setWorkerPage(page)}
            activeNodeId={activeWorkerId}
            availableNodes={nodeList}
            onSelectNode={(nid) => setActiveWorkerId(nid)}
          />
        )}

        <main className="content-area">
          {currentInterface === 'orchestrator'
            ? renderOrchestratorPage()
            : renderWorkerPage()}
        </main>
      </div>

      {/* Login Modal */}
      <LoginModal
        isOpen={loginModalOpen}
        onClose={() => setLoginModalOpen(false)}
      />

      {/* Submit Task Modal */}
      <SubmitTaskModal
        isOpen={submitTaskModalOpen}
        onClose={() => setSubmitTaskModalOpen(false)}
        onTaskSubmitted={() => {
          fetchClusterMeta()
          setOrchestratorPage('tasks')
        }}
      />
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  )
}

export default App
