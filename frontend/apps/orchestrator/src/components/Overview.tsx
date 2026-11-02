import React, { useState } from 'react'
import {
  Server,
  Activity,
  Play,
  Pause,
  RefreshCw,
  Send,
  Lock,
  Layers,
  Zap,
  ArrowRight
} from 'lucide-react'
import type { ClusterHealth, NodeProfile, Task } from '@shared/types'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { IsometricClusterMesh } from '@shared/components/IsometricClusterMesh'
import { ClusterResourceUtilization } from '@shared/components/ClusterResourceUtilization'
import { ClusterCapacity } from '@shared/components/ClusterCapacity'
import { BottomFeaturePanels } from '@shared/components/BottomFeaturePanels'
import { CyberneticMeshWave } from '@shared/components/CyberneticMeshWave'

interface OverviewProps {
  health: ClusterHealth | null
  nodes: NodeProfile[]
  tasks: Task[]
  onRefresh: () => void
  onOpenSubmitModal: () => void
  onNavigateToNodes: () => void
  onNavigateToTasks: () => void
  onOpenLogin?: () => void
}

export const Overview: React.FC<OverviewProps> = ({
  health,
  nodes,
  tasks,
  onRefresh,
  onOpenSubmitModal,
  onNavigateToNodes,
  onNavigateToTasks,
  onOpenLogin,
}) => {
  const { can, isAuthenticated } = useAuth()
  const [isTogglingDispatch, setIsTogglingDispatch] = useState(false)

  const onlineNodes = nodes.filter((n) => n.status === 'online')
  const runningTasks = tasks.filter((t) => t.status === 'running')
  const pendingTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'scheduled')
  const completedTasks = tasks.filter((t) => t.status === 'completed')

  // Calculate live resource aggregates
  const avgCpu = nodes.length > 0
    ? Math.round(nodes.reduce((acc, n) => acc + (n.telemetry?.cpu_percent || 0), 0) / nodes.length)
    : 0

  const avgRam = nodes.length > 0
    ? Math.round(nodes.reduce((acc, n) => acc + (n.telemetry?.ram_percent || 0), 0) / nodes.length)
    : 0

  const totalCpuCores = nodes.reduce((acc, n) => acc + (n.capabilities?.cpu_cores || 8), 0) || 24
  const usedCpuCores = Math.round((avgCpu / 100) * totalCpuCores)

  const totalRamGb = Math.round(nodes.reduce((acc, n) => acc + (n.capabilities?.ram_total_mb || 16384), 0) / 1024) || 64
  const usedRamGb = Math.round((avgRam / 100) * totalRamGb)

  const totalSlots = nodes.reduce((acc, n) => acc + (n.capabilities?.worker_capacity || 4), 0) || 8
  const activeSlots = nodes.reduce((acc, n) => acc + (n.telemetry?.active_tasks || 0), 0)

  const isDispatchPaused = (health as any)?.dispatch_paused ?? false

  const handleToggleDispatch = async () => {
    setIsTogglingDispatch(true)
    try {
      if (isDispatchPaused) {
        await api.resumeDispatch()
      } else {
        await api.pauseDispatch()
      }
      onRefresh()
    } catch (e: any) {
      alert(`Action failed: ${e.message}`)
    } finally {
      setIsTogglingDispatch(false)
    }
  }

  return (
    <div>
      {/* Auth Banner if not authenticated */}
      {!isAuthenticated && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'rgba(255, 51, 75, 0.08)',
            border: '1px solid rgba(255, 51, 75, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem 1.4rem',
            marginBottom: '1.5rem',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Lock size={18} color="#ff334b" />
            <div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                Authentication required for live cluster control
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Sign in with administrator credentials (default: <code>admin</code> / <code>admin123</code>) to inspect live nodes, adjust scheduler modes, and dispatch tasks.
              </div>
            </div>
          </div>

          {onOpenLogin && (
            <button className="btn btn-primary btn-sm" onClick={onOpenLogin}>
              Sign In to Cluster
            </button>
          )}
        </div>
      )}

      {/* Hero Header with Abstract 3D Cluster Illustration */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1.5rem',
        }}
      >
        <div style={{ maxWidth: 640 }}>
          <div
            style={{
              fontSize: '0.72rem',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--accent-red)',
              marginBottom: '0.35rem',
            }}
          >
            Distributed Compute Mesh
          </div>
          <h1
            style={{
              fontSize: '1.85rem',
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '-0.03em',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            Cluster <span style={{ color: 'var(--accent-red)' }}>Control</span> Overview
          </h1>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '0.35rem', lineHeight: '1.5' }}>
            Real-time orchestration, adaptive scheduling, and AI workload distribution across heterogeneous nodes.
          </p>

          <div style={{ display: 'flex', gap: '0.65rem', marginTop: '1rem' }}>
            {can('tasks:submit') && (
              <button className="btn btn-primary" onClick={onOpenSubmitModal}>
                <Send size={14} />
                <span>Submit Task</span>
              </button>
            )}

            {can('cluster:manage') && (
              <button
                className="btn btn-secondary"
                onClick={handleToggleDispatch}
                disabled={isTogglingDispatch}
              >
                {isDispatchPaused ? <Play size={14} /> : <Pause size={14} />}
                <span>{isDispatchPaused ? 'Resume Dispatch' : 'Pause Dispatch'}</span>
              </button>
            )}

            <button className="btn btn-secondary" onClick={onRefresh} title="Refresh cluster state">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {/* 3D Isometric Cluster Node Illustration */}
        <div style={{ flexShrink: 0 }}>
          <IsometricClusterMesh size={175} />
        </div>
      </div>

      {/* 4 Primary Top KPI Summary Cards */}
      <div className="kpi-grid">
        {/* Card 1: Registered Nodes */}
        <div className="kpi-card" onClick={isAuthenticated ? onNavigateToNodes : onOpenLogin} style={{ cursor: 'pointer' }}>
          <div>
            <div className="kpi-card-header">
              <div className="kpi-icon-pill kpi-icon-red">
                <Server size={17} />
              </div>
              <span className="kpi-label">Registered Nodes</span>
            </div>
            <div className="kpi-value">
              {!isAuthenticated ? '—' : nodes.length}
            </div>
          </div>
          <div className="kpi-footer-metric" style={{ color: 'var(--accent-emerald)' }}>
            ▲ +{onlineNodes.length} Online
          </div>
        </div>

        {/* Card 2: Active Tasks */}
        <div className="kpi-card" onClick={isAuthenticated ? onNavigateToTasks : onOpenLogin} style={{ cursor: 'pointer' }}>
          <div>
            <div className="kpi-card-header">
              <div className="kpi-icon-pill kpi-icon-cyan">
                <Zap size={17} />
              </div>
              <span className="kpi-label">Active Tasks</span>
            </div>
            <div className="kpi-value">
              {!isAuthenticated ? '—' : runningTasks.length}
            </div>
          </div>
          <div className="kpi-footer-metric" style={{ color: 'var(--accent-cyan)' }}>
            In Execution
          </div>
        </div>

        {/* Card 3: Pending Queue */}
        <div className="kpi-card" onClick={isAuthenticated ? onNavigateToTasks : onOpenLogin} style={{ cursor: 'pointer' }}>
          <div>
            <div className="kpi-card-header">
              <div className="kpi-icon-pill kpi-icon-purple">
                <Layers size={17} />
              </div>
              <span className="kpi-label">Pending Queue</span>
            </div>
            <div className="kpi-value">
              {!isAuthenticated ? '—' : pendingTasks.length}
            </div>
          </div>
          <div className="kpi-footer-metric" style={{ color: 'var(--accent-violet)' }}>
            Queued
          </div>
        </div>

        {/* Card 4: Completed */}
        <div className="kpi-card">
          <div>
            <div className="kpi-card-header">
              <div className="kpi-icon-pill kpi-icon-emerald">
                <Activity size={17} />
              </div>
              <span className="kpi-label">Completed</span>
            </div>
            <div className="kpi-value">
              {!isAuthenticated ? '—' : completedTasks.length}
            </div>
          </div>
          <div className="kpi-footer-metric" style={{ color: 'var(--accent-emerald)' }}>
            ▲ +{completedTasks.length} Today
          </div>
        </div>
      </div>

      {/* Middle Dual Section: Resource Utilization Chart + Cluster Capacity */}
      <div className="grid grid-2" style={{ gap: '1.25rem', marginBottom: '1.25rem' }}>
        <div className="card" style={{ marginBottom: 0 }}>
          <ClusterResourceUtilization currentCpu={avgCpu} currentRam={avgRam} />
        </div>

        <div className="card" style={{ marginBottom: 0 }}>
          <ClusterCapacity
            totalNodes={nodes.length || 2}
            usedCpuCores={usedCpuCores}
            totalCpuCores={totalCpuCores}
            usedRamGb={usedRamGb}
            totalRamGb={totalRamGb}
            activeSlots={activeSlots}
            totalSlots={totalSlots}
          />
        </div>
      </div>

      {/* Connected Worker Nodes Table */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="card-header">
          <div className="card-title">
            <Server size={16} color="var(--accent-red)" />
            Connected Worker Nodes
          </div>
          {isAuthenticated && (
            <button
              onClick={onNavigateToNodes}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--accent-red)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
              }}
            >
              View All Nodes &rarr;
            </button>
          )}
        </div>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Node ID</th>
                <th>Hostname</th>
                <th>Status</th>
                <th>Capabilities</th>
                <th>CPU</th>
                <th>RAM</th>
                <th>Slots</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {!isAuthenticated ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                      <Lock size={22} color="var(--text-muted)" />
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                        Cluster Telemetry Protected by RBAC
                      </div>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', maxWidth: '420px', margin: '0 auto 0.75rem' }}>
                        Sign in to inspect worker nodes, active resource footprints, and network latency.
                      </p>
                      {onOpenLogin && (
                        <button className="btn btn-primary btn-sm" onClick={onOpenLogin}>
                          Sign In
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : nodes.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No worker nodes currently registered
                  </td>
                </tr>
              ) : (
                nodes.map((node) => {
                  const nodeCpu = node.telemetry?.cpu_percent ?? 15.0
                  const nodeRam = node.telemetry?.ram_percent ?? 42.0
                  const rttMs = node.telemetry?.rtt_ms_ewma ?? 0.42

                  return (
                    <tr key={node.id}>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                        {node.id}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {node.capabilities?.hostname || 'localhost'}
                      </td>
                      <td>
                        <span className={`status-pill ${node.status}`}>
                          <span className={`status-dot dot-${node.status}`} />
                          Online
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                          <span className="badge-red-outline">CPU</span>
                          <span className="badge-red-outline">YOLO</span>
                          {node.capabilities?.has_gpu && <span className="badge-red-outline">GPU</span>}
                        </div>
                      </td>
                      <td className="mono" style={{ color: nodeCpu > 80 ? 'var(--accent-red)' : 'var(--accent-cyan)' }}>
                        {nodeCpu.toFixed(1)}%
                      </td>
                      <td className="mono" style={{ color: nodeRam > 80 ? 'var(--accent-amber)' : 'var(--text-primary)' }}>
                        {nodeRam.toFixed(1)}%
                      </td>
                      <td className="mono">
                        {node.telemetry?.active_tasks ?? 0} / {node.capabilities?.worker_capacity ?? 4}
                      </td>
                      <td className="mono" style={{ color: 'var(--text-muted)' }}>
                        {rttMs.toFixed(2)} ms
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Three Replacement Sections: Inference Workloads, Task Flow (Live), System Health */}
      <BottomFeaturePanels
        tasks={tasks}
        nodes={nodes}
        clusterStatus={health?.status || 'Online'}
        fairnessCv={health?.fairness_cv ?? 0.0}
      />

      {/* Cybernetic Mesh Ambient Wave Graphic */}
      <CyberneticMeshWave />
    </div>
  )
}
