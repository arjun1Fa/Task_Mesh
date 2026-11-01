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
import { api } from './api/client'
import { useDashboardSocket } from './websocket/useDashboardSocket'
import type { ClusterHealth, NodeProfile, Task } from '@shared/types'
import '@shared/styles/theme.css'

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<OrchestratorPage>('overview')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  // Cluster State
  const [health, setHealth] = useState<ClusterHealth | null>(null)
  const [nodes, setNodes] = useState<NodeProfile[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [dlqCount, setDlqCount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // Modals
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)

  // Fetch initial cluster state
  const refreshClusterData = useCallback(async () => {
    try {
      const [h, n, t, dlq] = await Promise.all([
        api.getHealth().catch(() => null),
        api.listNodes().catch(() => []),
        api.listTasks(undefined, 100).catch(() => []),
        api.listDlq().catch(() => []),
      ])

      if (h) setHealth(h)
      if (n) setNodes(n)
      if (t) setTasks(t)
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

  // Real-time WebSocket connection
  const { status: wsStatus } = useDashboardSocket({
    onMessage: (msg) => {
      if (msg.type === 'telemetry_update' && msg.data) {
        setNodes((prevNodes) =>
          prevNodes.map((node) =>
            node.id === msg.data.node_id ? { ...node, telemetry: msg.data } : node
          )
        )
      } else if (msg.type === 'task_event' && msg.data) {
        setTasks((prevTasks) => {
          const index = prevTasks.findIndex((t) => t.id === msg.data.id)
          if (index >= 0) {
            const updated = [...prevTasks]
            updated[index] = msg.data
            return updated
          }
          return [msg.data, ...prevTasks.slice(0, 99)]
        })
      } else if (msg.type === 'node_status' && msg.data) {
        setNodes((prevNodes) =>
          prevNodes.map((n) =>
            n.id === msg.data.node_id ? { ...n, status: msg.data.status } : n
          )
        )
      }
    },
  })

  const pendingTasksCount = tasks.filter((t) => t.status === 'pending' || t.status === 'scheduled').length

  const handleSelectNode = (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setCurrentPage('nodes')
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header
        clusterStatus={health?.status || 'unknown'}
        wsStatus={wsStatus}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        onOpenSubmitTask={() => setIsSubmitModalOpen(true)}
      />

      <div className="layout-body">
        {/* Left Navigation Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          nodeCount={nodes.length}
          pendingTasksCount={pendingTasksCount}
          dlqCount={dlqCount}
        />

        {/* Main Workspace Content */}
        <main className="content-pane">
          {currentPage === 'overview' && (
            <Overview
              health={health}
              nodes={nodes}
              tasks={tasks}
              onRefresh={refreshClusterData}
              onOpenSubmitModal={() => setIsSubmitModalOpen(true)}
              onNavigateToNodes={() => setCurrentPage('nodes')}
              onNavigateToTasks={() => setCurrentPage('queue')}
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
      />

      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </div>
  )
}
export default App

