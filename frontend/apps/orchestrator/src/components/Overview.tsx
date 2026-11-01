import React, { useState } from 'react'
import {
  Server,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  RefreshCw,
  Cpu,
  Layers,
  ArrowUpRight,
  Clock,
  Send
} from 'lucide-react'
import type { ClusterHealth, NodeProfile, Task } from '@shared/types'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

interface OverviewProps {
  health: ClusterHealth | null
  nodes: NodeProfile[]
  tasks: Task[]
  onRefresh: () => void
  onOpenSubmitModal: () => void
  onNavigateToNodes: () => void
  onNavigateToTasks: () => void
}

export const Overview: React.FC<OverviewProps> = ({
  health,
  nodes,
  tasks,
  onRefresh,
  onOpenSubmitModal,
  onNavigateToNodes,
  onNavigateToTasks,
}) => {
  const { can, isAuthenticated } = useAuth()
  const [isTogglingDispatch, setIsTogglingDispatch] = useState(false)

  const onlineNodes = nodes.filter((n) => n.status === 'online')
  const degradedNodes = nodes.filter((n) => n.status === 'degraded' || n.status === 'draining')
  const offlineNodes = nodes.filter((n) => n.status === 'offline')

  const runningTasks = tasks.filter((t) => t.status === 'running')
  const pendingTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'scheduled')
  const completedTasks = tasks.filter((t) => t.status === 'completed')
  const failedTasks = tasks.filter((t) => t.status === 'failed')

  const avgCpu = nodes.length > 0
    ? Math.round(nodes.reduce((acc, n) => acc + (n.telemetry?.cpu_percent || 0), 0) / nodes.length)
    : 0

  const avgRam = nodes.length > 0
    ? Math.round(nodes.reduce((acc, n) => acc + (n.telemetry?.ram_percent || 0), 0) / nodes.length)
    : 0

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
      {!isAuthenticated && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'rgba(59, 130, 246, 0.12)',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1.25rem',
            marginBottom: '1.25rem',
            color: '#93c5fd',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Activity size={18} color="var(--accent-blue)" />
            <div>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Sign In Required to View Live Cluster Telemetry:</span>
              <span style={{ marginLeft: '0.35rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Use username <code style={{ color: '#fff', fontWeight: 600 }}>admin</code> with password <code style={{ color: '#fff', fontWeight: 600 }}>admin123</code> (or your cluster token) to view connected worker nodes and dispatch tasks.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Cluster Control Overview
          </h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Real-time status, cluster compute capacity, and global execution telemetry
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {can('tasks:submit') && (
            <button className="btn btn-primary btn-sm" onClick={onOpenSubmitModal}>
              <Send size={13} />
              <span>Submit Task</span>
            </button>
          )}

          {can('cluster:manage') && (
            <button
              className={`btn ${isDispatchPaused ? 'btn-primary' : 'btn-secondary'} btn-sm`}
              onClick={handleToggleDispatch}
              disabled={isTogglingDispatch}
            >
              {isDispatchPaused ? <Play size={13} /> : <Pause size={13} />}
              <span>{isDispatchPaused ? 'Resume Dispatch' : 'Pause Dispatch'}</span>
            </button>
          )}

          <button className="btn btn-secondary btn-sm" onClick={onRefresh} title="Refresh Metrics">
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Cluster Health Banner */}
      <div className="card" style={{ padding: '0.85rem 1.25rem', marginBottom: '1.25rem', backgroundColor: 'var(--bg-surface-elevated)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="status-dot dot-online" style={{ width: 10, height: 10 }} />
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>
                Cluster Status: {health?.status?.toUpperCase() || 'HEALTHY'}
              </div>
              <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Active Mode: <strong style={{ color: 'var(--accent-blue)' }}>{health?.scheduler_mode?.toUpperCase() || 'ADAPTIVE'}</strong> &bull; Fairness CV: <strong style={{ color: 'var(--accent-emerald)' }}>{health?.fairness_cv !== undefined ? Number(health.fairness_cv).toFixed(3) : '0.000'}</strong>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Dispatch Loop: <strong style={{ color: isDispatchPaused ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>{isDispatchPaused ? 'PAUSED' : 'ACTIVE'}</strong></span>
          </div>
        </div>
      </div>

      {/* KPI Summary Grid */}
      <div className="kpi-grid">
        <div className="kpi-card" onClick={onNavigateToNodes} style={{ cursor: 'pointer' }}>
          <div className="kpi-label">Registered Nodes</div>
          <div className="kpi-value" style={{ color: 'var(--accent-emerald)' }}>{onlineNodes.length} / {nodes.length}</div>
          <div className="kpi-sub">{degradedNodes.length} degraded &bull; {offlineNodes.length} offline</div>
        </div>

        <div className="kpi-card" onClick={onNavigateToTasks} style={{ cursor: 'pointer' }}>
          <div className="kpi-label">Active Running Tasks</div>
          <div className="kpi-value" style={{ color: 'var(--accent-blue)' }}>{runningTasks.length}</div>
          <div className="kpi-sub">In-flight on worker nodes</div>
        </div>

        <div className="kpi-card" onClick={onNavigateToTasks} style={{ cursor: 'pointer' }}>
          <div className="kpi-label">Pending In Queue</div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>{pendingTasks.length}</div>
          <div className="kpi-sub">Awaiting dispatch</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Completed Executions</div>
          <div className="kpi-value">{completedTasks.length}</div>
          <div className="kpi-sub">{failedTasks.length} execution failures</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Cluster CPU Load</div>
          <div className="kpi-value">{avgCpu}%</div>
          <div className="progress-bar-bg" style={{ marginTop: '0.4rem' }}>
            <div className="progress-bar-fill" style={{ width: `${avgCpu}%`, backgroundColor: 'var(--accent-blue)' }} />
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Cluster RAM Footprint</div>
          <div className="kpi-value">{avgRam}%</div>
          <div className="progress-bar-bg" style={{ marginTop: '0.4rem' }}>
            <div className="progress-bar-fill" style={{ width: `${avgRam}%`, backgroundColor: 'var(--accent-cyan)' }} />
          </div>
        </div>
      </div>

      {/* Connected Nodes Quick Table */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Server size={15} color="var(--accent-blue)" />
            Connected Worker Nodes
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onNavigateToNodes}>
            View All Nodes &rarr;
          </button>
        </div>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Node ID</th>
                <th>Hostname</th>
                <th>Status</th>
                <th>Effective Score</th>
                <th>Active Slots</th>
                <th>CPU / RAM</th>
                <th>Last Heartbeat</th>
              </tr>
            </thead>
            <tbody>
              {nodes.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No worker nodes currently registered
                  </td>
                </tr>
              ) : (
                nodes.map((node) => (
                  <tr key={node.id}>
                    <td className="mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{node.id}</td>
                    <td className="mono" style={{ color: 'var(--text-muted)' }}>{node.capabilities.hostname || 'localhost'}</td>
                    <td><span className={`badge badge-${node.status}`}>{node.status}</span></td>
                    <td className="mono">{(node.effective_score ?? 1.0).toFixed(3)}</td>
                    <td className="mono">{node.telemetry?.active_tasks ?? 0} / {node.capabilities.worker_capacity}</td>
                    <td className="mono">{node.telemetry?.cpu_percent ?? 0}% &bull; {node.telemetry?.ram_percent ?? 0}%</td>
                    <td className="mono" style={{ color: 'var(--text-muted)' }}>
                      {new Date(node.last_heartbeat).toLocaleTimeString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

