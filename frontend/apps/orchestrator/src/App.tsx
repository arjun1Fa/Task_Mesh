import React, { useState, useEffect, useCallback } from 'react'
import { Header } from './components/Header'
import { Sidebar, OrchestratorPage } from './components/Sidebar'
import { Overview } from './components/Overview'
import { ClusterNodes } from './components/ClusterNodes'
import { LiveTaskAllocation } from './components/LiveTaskAllocation'
import { TaskQueue } from './components/TaskQueue'
import { TaskHistory } from './components/TaskHistory'
import { SchedulingEngine } from './components/SchedulingEngine'
import { NetworkInference } from './components/NetworkInference'
import { LogsEvents } from './components/LogsEvents'
import { DeadLetterQueue } from './components/DeadLetterQueue'
import { RecoveryHA } from './components/RecoveryHA'
import { UsersPermissions } from './components/UsersPermissions'
import { SystemConfig } from './components/SystemConfig'
import { SecurityAudit } from './components/SecurityAudit'
import { SubmitTaskModal } from './components/SubmitTaskModal'
import { LoginModal } from './components/LoginModal'
import { api, getAuthToken } from './api/client'
import { useAuth } from './auth/AuthContext'
import { useDashboardSocket } from './websocket/useDashboardSocket'
import type { ClusterHealth, NodeProfile, SchedulerDecision, Task } from '@shared/types'
import '@shared/styles/theme.css'

export const App: React.FC = () => {
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth()
  const [currentPage, setCurrentPage] = useState<OrchestratorPage>('overview')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  // Cluster State
  const [health, setHealth] = useState<ClusterHealth | null>(null)
  const [nodes, setNodes] = useState<NodeProfile[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [decisions, setDecisions] = useState<SchedulerDecision[]>([])
  const [dlqCount, setDlqCount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // Modals
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)

  // Fetch initial cluster state
  const refreshClusterData = useCallback(async () => {
    try {
      const token = getAuthToken()
      if (!token) {
        setHealth(null)
        setNodes([])
        setTasks([])
        setDecisions([])
        setDlqCount(0)
        setIsLoading(false)
        return
      }

      const [h, n, t, dec, dlq] = await Promise.all([
        api.getHealth().catch(() => null),
        api.listNodes().catch(() => []),
        api.listTasks(undefined, 100).catch(() => []),
        api.getSchedulerDecisions(50).catch(() => []),
        api.listDlq().catch(() => []),
      ])

      if (h) setHealth(h)
      if (n) setNodes(n)
      if (t) setTasks(t)
      if (dec) setDecisions(dec)
      setDlqCount(dlq.length)
    } catch (err) {
      console.error('Failed to refresh cluster data:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshClusterData()
    const timer = setInterval(refreshClusterData, 5000)
    return () => clearInterval(timer)
  }, [refreshClusterData])

  // Refetch immediately whenever authentication state changes
  useEffect(() => {
    refreshClusterData()
  }, [isAuthenticated, refreshClusterData])

  // Real-time WebSocket connection
  const { status: wsStatus } = useDashboardSocket({
    token: getAuthToken(),
    isAuthenticated,
    onEvent: (evt) => {
      if (!evt || !evt.event_type) return

      switch (evt.event_type) {
        case 'task.submitted': {
          const tData = evt.data || {}
          setTasks((prev) => {
            const taskId = tData.task_id || evt.entity_id
            if (!taskId) return prev
            const existing = prev.find((x) => x.id === taskId)
            if (existing) return prev
            const newTask: Task = {
              id: taskId,
              task_type: tData.task_type || 'task',
              payload: tData.payload || {},
              priority: tData.priority ?? 5,
              status: 'pending',
              created_at: evt.timestamp || new Date().toISOString(),
              updated_at: evt.timestamp || new Date().toISOString(),
              timeout_seconds: 60,
              current_attempt: 0,
              requires_gpu: false,
              required_memory_mb: 256,
              required_capabilities: [],
              offload_policy: tData.offload_policy || 'remote_allowed',
              retry_count: 0,
              progress: 0,
              metadata: {},
            }
            return [newTask, ...prev.slice(0, 99)]
          })
          break
        }
        case 'task.assigned': {
          const tData = evt.data || {}
          const taskId = tData.task_id || evt.entity_id
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? {
                    ...t,
                    status: 'running',
                    assigned_node_id: tData.selected_node_id,
                    current_attempt_id: tData.attempt_id,
                    updated_at: evt.timestamp || new Date().toISOString(),
                  }
                : t
            )
          )
          break
        }
        case 'task.started': {
          const tData = evt.data || {}
          const taskId = tData.task_id || evt.entity_id
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? {
                    ...t,
                    status: 'running',
                    assigned_node_id: tData.node_id || t.assigned_node_id,
                    updated_at: evt.timestamp || new Date().toISOString(),
                  }
                : t
            )
          )
          break
        }
        case 'task.progress': {
          const tData = evt.data || {}
          const taskId = tData.task_id || evt.entity_id
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? {
                    ...t,
                    progress: tData.progress ?? t.progress,
                    updated_at: evt.timestamp || new Date().toISOString(),
                  }
                : t
            )
          )
          break
        }
        case 'task.completed': {
          const tData = evt.data || {}
          const taskId = tData.task_id || evt.entity_id
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? {
                    ...t,
                    status: 'completed',
                    progress: 1.0,
                    assigned_node_id: tData.node_id || t.assigned_node_id,
                    result: {
                      task_id: taskId,
                      attempt_id: tData.attempt_id || '',
                      node_id: tData.node_id || '',
                      status: 'completed',
                      execution_time_seconds: tData.execution_time_seconds ?? 0,
                      output: tData.output,
                      metrics: tData.metrics,
                      completed_at: evt.timestamp || new Date().toISOString(),
                    },
                    updated_at: evt.timestamp || new Date().toISOString(),
                  }
                : t
            )
          )
          break
        }
        case 'task.failed': {
          const tData = evt.data || {}
          const taskId = tData.task_id || evt.entity_id
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? {
                    ...t,
                    status: 'failed',
                    error_message: tData.error,
                    updated_at: evt.timestamp || new Date().toISOString(),
                  }
                : t
            )
          )
          if (tData.moved_to_dlq) {
            setDlqCount((c) => c + 1)
          }
          break
        }
        case 'task.cancelled': {
          const tData = evt.data || {}
          const taskId = tData.task_id || evt.entity_id
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? {
                    ...t,
                    status: 'cancelled',
                    error_message: tData.reason,
                    updated_at: evt.timestamp || new Date().toISOString(),
                  }
                : t
            )
          )
          break
        }
        case 'node.online':
        case 'node.registered': {
          const nData = evt.data || {}
          const nodeId = nData.node_id || evt.entity_id
          setNodes((prev) => {
            const idx = prev.findIndex((n) => n.id === nodeId)
            if (idx >= 0) {
              const updated = [...prev]
              updated[idx] = { ...updated[idx], status: 'online' }
              return updated
            }
            return prev
          })
          refreshClusterData()
          break
        }
        case 'node.offline':
        case 'node.disconnected': {
          const nData = evt.data || {}
          const nodeId = nData.node_id || evt.entity_id
          setNodes((prev) =>
            prev.map((n) => (n.id === nodeId ? { ...n, status: 'offline' } : n))
          )
          break
        }
        case 'node.status_changed': {
          const nData = evt.data || {}
          const nodeId = nData.node_id || evt.entity_id
          if (nodeId && nData.status) {
            setNodes((prev) =>
              prev.map((n) => (n.id === nodeId ? { ...n, status: nData.status } : n))
            )
          }
          break
        }
        default:
          break
      }
    },
    onHealth: (h) => {
      if (h) setHealth(h)
    },
  })

  const pendingTasksCount = tasks.filter((t) => t.status === 'pending' || t.status === 'scheduled').length

  const handleSelectNode = (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setCurrentPage('nodes')
  }

  return (
    <div className="app-shell">
      {/* Top Header */}
      <Header
        clusterStatus={health?.status || 'unknown'}
        wsStatus={wsStatus}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        onOpenSubmitTask={() => setIsSubmitModalOpen(true)}
      />

      <div className="main-layout">
        {/* Left Navigation Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          nodeCount={nodes.length}
          pendingTasksCount={pendingTasksCount}
          dlqCount={dlqCount}
        />

        {/* Main Workspace Content */}
        <main className="content-area">
          {currentPage === 'overview' && (
            <Overview
              health={health}
              nodes={nodes}
              tasks={tasks}
              onRefresh={refreshClusterData}
              onOpenSubmitModal={() => setIsSubmitModalOpen(true)}
              onNavigateToNodes={() => setCurrentPage('nodes')}
              onNavigateToTasks={() => setCurrentPage('queue')}
              onOpenLogin={() => setIsLoginModalOpen(true)}
            />
          )}

          {currentPage === 'nodes' && (
            <ClusterNodes
              nodes={nodes}
              onRefresh={refreshClusterData}
              selectedNodeId={selectedNodeId}
              onClearSelectedNode={() => setSelectedNodeId(null)}
            />
          )}

          {currentPage === 'live_allocation' && (
            <LiveTaskAllocation
              nodes={nodes}
              tasks={tasks}
              decisions={decisions}
              onRefresh={refreshClusterData}
              onSelectNode={handleSelectNode}
            />
          )}

          {currentPage === 'queue' && <TaskQueue />}

          {currentPage === 'history' && <TaskHistory />}

          {currentPage === 'scheduling' && <SchedulingEngine />}

          {currentPage === 'network' && <NetworkInference />}

          {currentPage === 'logs' && <LogsEvents />}

          {currentPage === 'dlq' && <DeadLetterQueue />}

          {currentPage === 'recovery' && <RecoveryHA />}

          {currentPage === 'users' && <UsersPermissions />}

          {currentPage === 'config' && <SystemConfig />}

          {currentPage === 'audit' && <SecurityAudit />}
        </main>
      </div>

      {/* Modals */}
      <SubmitTaskModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onTaskSubmitted={refreshClusterData}
        onNavigateToTasks={() => setActiveTab('queue')}
      />

      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </div>
  )
}
export default App

