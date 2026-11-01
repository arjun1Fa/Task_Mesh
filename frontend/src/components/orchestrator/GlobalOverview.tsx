import React, { useState } from 'react'
import {
  Server,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Pause,
  RefreshCw,
  Cpu,
  Layers,
  ArrowUpRight,
  Clock,
  Send,
} from 'lucide-react'
import type { ClusterHealth, NodeProfile, Task } from '../../types'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

interface GlobalOverviewProps {
  health: ClusterHealth | null
  nodes: NodeProfile[]
  tasks: Task[]
  onRefresh: () => void
  onOpenSubmitModal: () => void
  onSelectNode: (nodeId: string) => void
}

export const GlobalOverview: React.FC<GlobalOverviewProps> = ({
  health,
  nodes,
  tasks,
  onRefresh,
  onOpenSubmitModal,
  onSelectNode,
}) => {
  const { hasPermission } = useAuth()
  const [isTogglingDispatch, setIsTogglingDispatch] = useState(false)

  const onlineNodes = nodes.filter((n) => n.status === 'online')
  const degradedNodes = nodes.filter((n) => n.status === 'degraded' || n.status === 'draining')
  const offlineNodes = nodes.filter((n) => n.status === 'offline')

  const runningTasks = tasks.filter((t) => t.status === 'running')
  const pendingTasks = tasks.filter((t) => t.status === 'pending')
  const completedTasks = tasks.filter((t) => t.status === 'completed')
  const failedTasks = tasks.filter((t) => t.status === 'failed')

  // Calculate cluster average metrics
  const avgCpu = nodes.length > 0
    ? Math.round(nodes.reduce((acc, n) => acc + (n.telemetry?.cpu_percent || 0), 0) / nodes.length)
    : 0

  const avgRam = nodes.length > 0
    ? Math.round(nodes.reduce((acc, n) => acc + (n.telemetry?.ram_percent || 0), 0) / nodes.length)
    : 0

  // Calculate measured latency from completed tasks
  const completedDurations = completedTasks
    .map((t) => t.result?.execution_time_seconds)
    .filter((d): d is number => typeof d === 'number')

  const avgLatencyMs = completedDurations.length > 0
    ? Math.round((completedDurations.reduce((a, b) => a + b, 0) / completedDurations.length) * 1000)
    : 0

  const sortedDurations = [...completedDurations].sort((a, b) => a - b)
  const p95LatencyMs = sortedDurations.length > 0
    ? Math.round(sortedDurations[Math.floor(sortedDurations.length * 0.95)] * 1000)
    : 0

  const isDispatchPaused = health ? (health as any).dispatch_paused : false

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

  // Meaningful calculated cluster health diagnosis
  let healthSummary = 'All systems nominal'
  let healthSeverity: 'healthy' | 'warning' | 'critical' = 'healthy'
  if (nodes.length === 0) {
    healthSummary = 'No compute worker nodes registered with cluster.'
    healthSeverity = 'warning'
  } else if (onlineNodes.length === 0) {
    healthSummary = 'Zero online compute nodes available. Task dispatch is stalled.'
    healthSeverity = 'critical'
  } else if (offlineNodes.length > 0) {
    healthSummary = `${offlineNodes.length} compute node(s) currently OFFLINE.`
    healthSeverity = 'warning'
  } else if ((health?.dlq_tasks || 0) > 0) {
    healthSummary = `Dead Letter Queue contains ${health?.dlq_tasks} permanently failed task(s).`
    healthSeverity = 'warning'
  }

  return (
    <div>
      {/* Page Header & Quick Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Global Cluster Overview</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Real-time status, cluster-wide compute capacity, and execution telemetry
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem' }}>
          {hasPermission('tasks.submit') && (
            <button className="btn btn-primary" onClick={onOpenSubmitModal}>
              <Send size={15} />
              <span>Submit Task</span>
            </button>
          )}

          {hasPermission('cluster.manage') && (
            <button
              className={`btn ${isDispatchPaused ? 'btn-success' : 'btn-secondary'}`}
              onClick={handleToggleDispatch}
              disabled={isTogglingDispatch}
              title={isDispatchPaused ? 'Resume task assignment loop' : 'Temporarily pause task assignment loop'}
            >
              {isDispatchPaused ? <Play size={15} /> : <Pause size={15} />}
              <span>{isDispatchPaused ? 'Resume Dispatch' : 'Pause Dispatch'}</span>
            </button>
          )}

          <button className="btn btn-secondary btn-icon" onClick={onRefresh} title="Refresh Metrics">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Cluster Health Summary Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.85rem',
        padding: '0.9rem 1.25rem',
        backgroundColor: healthSeverity === 'healthy' ? 'rgba(16, 185, 129, 0.08)' : healthSeverity === 'warning' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(239, 68, 68, 0.08)',
        border: `1px solid ${healthSeverity === 'healthy' ? 'rgba(16, 185, 129, 0.25)' : healthSeverity === 'warning' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
        borderRadius: 'var(--radius-lg)',
        marginBottom: '1.5rem',
      }}>
        {healthSeverity === 'healthy' ? (
          <CheckCircle2 size={20} color="var(--accent-emerald)" />
        ) : (
          <AlertTriangle size={20} color={healthSeverity === 'warning' ? 'var(--accent-amber)' : 'var(--accent-rose)'} />
        )}
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>
            System Assessment: {healthSummary}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Scheduler: <strong style={{ color: 'var(--accent-cyan)' }}>{health?.scheduler_mode?.toUpperCase() || 'ADAPTIVE'}</strong> | DRR Fairness CV: <strong className="mono">{health?.fairness_cv !== undefined && health.fairness_cv !== null ? Number(health.fairness_cv).toFixed(3) : '0.000'}</strong> (0.0 = perfect equity) | Dispatch: {isDispatchPaused ? <span style={{ color: 'var(--accent-amber)' }}>PAUSED</span> : <span style={{ color: 'var(--accent-emerald)' }}>ACTIVE</span>}
          </div>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Online Nodes</span>
            <Server size={14} color="var(--accent-emerald)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-emerald)' }}>
            {onlineNodes.length} <span style={{ fontSize: '1rem', color: 'var(--text-dim)' }}>/ {nodes.length}</span>
          </div>
          <div className="kpi-sub">{degradedNodes.length} degraded, {offlineNodes.length} offline</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Running Tasks</span>
            <Activity size={14} color="var(--accent-cyan)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-cyan)' }}>
            {runningTasks.length}
          </div>
          <div className="kpi-sub">Active WebSocket worker execution</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Pending Queue</span>
            <Layers size={14} color="var(--accent-amber)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>
            {pendingTasks.length}
          </div>
          <div className="kpi-sub">Awaiting scheduling dispatch</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Lifetime Throughput</span>
            <CheckCircle2 size={14} color="var(--accent-emerald)" />
          </div>
          <div className="kpi-value">
            {completedTasks.length}
          </div>
          <div className="kpi-sub">{failedTasks.length} total failed executions</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Average Latency</span>
            <Clock size={14} color="var(--accent-blue)" />
          </div>
          <div className="kpi-value">
            {avgLatencyMs} <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>ms</span>
          </div>
          <div className="kpi-sub">P95: {p95LatencyMs} ms (measured)</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Cluster Load</span>
            <Cpu size={14} color="var(--accent-indigo)" />
          </div>
          <div className="kpi-value">
            {avgCpu}<span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>% CPU</span>
          </div>
          <div className="kpi-sub">{avgRam}% Cluster RAM utilization</div>
        </div>
      </div>

      {/* Main Overview Visualizations Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.25rem' }}>

        {/* Node Capacity & Utilization Bars */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <Server size={16} />
              <span>Node Hardware Load & Utilization</span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{nodes.length} registered</span>
          </div>
          <div className="panel-body">
            {nodes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                No worker nodes connected. Start a node agent to begin orchestration.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {nodes.map((node) => {
                  const cpu = node.telemetry?.cpu_percent || 0
                  const ram = node.telemetry?.ram_percent || 0
                  const isOnline = node.status === 'online'
                  return (
                    <div
                      key={node.id}
                      onClick={() => onSelectNode(node.id)}
                      style={{
                        padding: '0.85rem 1rem',
                        backgroundColor: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-main)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        transition: 'border-color 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent-cyan)')}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-main)')}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={`status-pill ${node.status}`} style={{ padding: '1px 5px', fontSize: '0.68rem' }}>
                            {node.status}
                          </span>
                          <strong className="mono" style={{ fontSize: '0.88rem' }}>{node.id}</strong>
                          {node.capabilities.has_gpu && (
                            <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>GPU: {node.capabilities.gpu_name || 'Active'}</span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                          Score: <span className="mono" style={{ color: 'var(--accent-cyan)' }}>{(node.effective_score ?? 1.0).toFixed(2)}</span> (Base {(node.base_score ?? 1.0).toFixed(2)} × EWMA {(node.performance_multiplier ?? 1.0).toFixed(2)})
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '3px' }}>
                            <span>CPU ({node.capabilities.cpu_cores} cores)</span>
                            <span className="mono">{cpu}%</span>
                          </div>
                          <div className="progress-bar-bg">
                            <div className="progress-bar-fill" style={{ width: `${cpu}%`, backgroundColor: cpu > 80 ? 'var(--accent-rose)' : undefined }} />
                          </div>
                        </div>

                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '3px' }}>
                            <span>RAM ({(((node.capabilities?.ram_total_mb ?? 1024)) / 1024).toFixed(1)} GB)</span>
                            <span className="mono">{ram}%</span>
                          </div>
                          <div className="progress-bar-bg">
                            <div className="progress-bar-fill" style={{ width: `${ram}%`, background: 'linear-gradient(90deg, #6366F1, #A855F7)' }} />
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Scheduler Pipeline Allocation & Recent Activity */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <Activity size={16} />
              <span>Scheduler Allocation & Task Breakdown</span>
            </div>
            <span className="badge badge-blue">Real Measurements</span>
          </div>
          <div className="panel-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <div style={{ padding: '0.75rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Completion Rate</div>
                <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '4px' }}>
                  {tasks.length > 0 ? ((completedTasks.length / tasks.length) * 100).toFixed(1) : 0}%
                </div>
              </div>

              <div style={{ padding: '0.75rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Failure Rate</div>
                <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: failedTasks.length > 0 ? 'var(--accent-rose)' : 'var(--text-muted)', marginTop: '4px' }}>
                  {tasks.length > 0 ? ((failedTasks.length / tasks.length) * 100).toFixed(1) : 0}%
                </div>
              </div>

              <div style={{ padding: '0.75rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Active Leases</div>
                <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '4px' }}>
                  {runningTasks.length}
                </div>
              </div>
            </div>

            {/* Task Types Distribution */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                Observed Task Workload Distribution
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {Object.entries(
                  tasks.reduce((acc, t) => {
                    acc[t.task_type] = (acc[t.task_type] || 0) + 1
                    return acc
                  }, {} as Record<string, number>)
                ).map(([type, count]) => {
                  const pct = Math.round((count / tasks.length) * 100)
                  return (
                    <div key={type}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span className="mono">{type}</span>
                        <span>{count} tasks ({pct}%)</span>
                      </div>
                      <div className="progress-bar-bg" style={{ height: '4px', marginTop: '3px' }}>
                        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Recent Executions Preview */}
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                Recent Task Allocations
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {tasks.slice(0, 4).map((task) => (
                  <div
                    key={task.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.5rem 0.75rem',
                      backgroundColor: 'rgba(255, 255, 255, 0.02)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className={`badge ${task.status === 'completed' ? 'badge-emerald' : task.status === 'running' ? 'badge-blue' : task.status === 'failed' ? 'badge-rose' : 'badge-amber'}`}>
                        {task.status}
                      </span>
                      <span className="mono" style={{ color: 'var(--text-main)' }}>{task.id.slice(0, 16)}...</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                      <span>→ {task.assigned_node_id || 'unassigned'}</span>
                      {task.result?.execution_time_seconds !== undefined && (
                        <span className="mono">({Number(task.result.execution_time_seconds).toFixed(2)}s)</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

