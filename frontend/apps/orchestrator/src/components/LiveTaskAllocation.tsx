import React, { useState } from 'react'
import {
  GitBranch,
  Server,
  Layers,
  ArrowRight,
  CheckCircle,
  Clock,
  AlertTriangle,
  Eye,
  RefreshCw,
  Cpu,
  Zap,
  Activity
} from 'lucide-react'
import type { NodeProfile, Task, SchedulerDecision } from '@shared/types'

interface LiveTaskAllocationProps {
  nodes: NodeProfile[]
  tasks: Task[]
  decisions: SchedulerDecision[]
  onRefresh: () => void
}

export const LiveTaskAllocation: React.FC<LiveTaskAllocationProps> = ({
  nodes,
  tasks,
  decisions,
  onRefresh,
}) => {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [selectedDecision, setSelectedDecision] = useState<SchedulerDecision | null>(null)

  const runningTasks = tasks.filter((t) => t.status === 'running')
  const pendingTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'scheduled')
  const recentCompleted = tasks.filter((t) => t.status === 'completed').slice(0, 10)

  const handleSelectTask = (task: Task) => {
    setSelectedTask(task)
    const matchDec = decisions.find((d) => d.task_id === task.id) || null
    setSelectedDecision(matchDec)
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Live Task Allocation Topology
          </h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Physical distributed routing: Central Orchestrator dispatching tasks across active worker nodes.
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
          <RefreshCw size={13} />
          <span>Refresh Tree</span>
        </button>
      </div>

      {/* Allocation Architecture Visualizer */}
      <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem', backgroundColor: 'var(--bg-surface-elevated)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '2rem' }}>
          {/* Central Orchestrator Dispatch Node */}
          <div style={{
            width: '260px',
            backgroundColor: 'var(--bg-surface)',
            border: '2px solid var(--accent-blue-border)',
            borderRadius: 'var(--radius-lg)',
            padding: '1.25rem',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <div style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--accent-blue)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}>
                <Layers size={18} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>Primary Orchestrator</div>
                <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--accent-blue)' }}>PORT 8000 &bull; ADAPTIVE</div>
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-surface-sunken)',
              padding: '0.6rem 0.75rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.35rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pending Queue:</span>
                <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-amber)' }}>{pendingTasks.length} tasks</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>In-Flight Running:</span>
                <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>{runningTasks.length} tasks</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Active Workers:</span>
                <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>{nodes.length} connected</span>
              </div>
            </div>
          </div>

          {/* Allocation Routing Paths */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {nodes.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', border: '1px dashed var(--border-main)', borderRadius: 'var(--radius-md)' }}>
                No worker nodes connected. Start a worker node agent to view live allocation paths.
              </div>
            ) : (
              nodes.map((node) => {
                const assignedRunning = runningTasks.filter((t) => t.assigned_node_id === node.id)
                const assignedCompleted = recentCompleted.filter((t) => t.assigned_node_id === node.id)

                return (
                  <div
                    key={node.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      backgroundColor: 'var(--bg-surface)',
                      border: '1px solid var(--border-main)',
                      borderRadius: 'var(--radius-md)',
                      padding: '1rem 1.25rem',
                    }}
                  >
                    {/* Routing Line Indicator */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', minWidth: '140px' }}>
                      <span className="mono" style={{ fontSize: '0.72rem' }}>DISPATCH</span>
                      <ArrowRight size={14} color="var(--accent-blue)" />
                      <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>WS LINK</span>
                    </div>

                    {/* Target Worker Box */}
                    <div style={{ minWidth: '220px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Server size={15} color="var(--accent-emerald)" />
                        <span className="mono" style={{ fontWeight: 700, fontSize: '0.85rem' }}>{node.id}</span>
                        <span className={`badge badge-${node.status}`}>{node.status}</span>
                      </div>
                      <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {node.capabilities.hostname || 'Worker'} &bull; Concurrency: {node.capabilities.worker_capacity} slots
                      </div>
                    </div>

                    {/* Live Dispatched Tasks on this Node */}
                    <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                      {assignedRunning.length === 0 && assignedCompleted.length === 0 ? (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                          Idle &bull; Waiting for dispatch
                        </span>
                      ) : (
                        <>
                          {assignedRunning.map((t) => (
                            <button
                              key={t.id}
                              onClick={() => handleSelectTask(t)}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.35rem 0.6rem',
                                backgroundColor: 'var(--accent-blue-subtle)',
                                border: '1px solid var(--accent-blue-border)',
                                borderRadius: 'var(--radius-sm)',
                                color: '#93c5fd',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                              }}
                            >
                              <Activity size={12} className="animate-spin" />
                              <span className="mono" style={{ fontWeight: 600 }}>{t.id.slice(0, 10)}</span>
                              <span style={{ opacity: 0.8 }}>({t.task_type})</span>
                              <span className="badge badge-info" style={{ fontSize: '0.65rem', padding: '1px 4px' }}>RUNNING</span>
                            </button>
                          ))}

                          {assignedCompleted.slice(0, 3).map((t) => (
                            <button
                              key={t.id}
                              onClick={() => handleSelectTask(t)}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.35rem 0.6rem',
                                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                                border: '1px solid var(--accent-emerald-border)',
                                borderRadius: 'var(--radius-sm)',
                                color: '#6ee7b7',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                              }}
                            >
                              <CheckCircle size={12} />
                              <span className="mono">{t.id.slice(0, 10)}</span>
                              <span style={{ opacity: 0.8 }}>({t.result?.execution_time_seconds ? `${Number(t.result.execution_time_seconds).toFixed(2)}s` : 'OK'})</span>
                            </button>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>

      {/* Task Inspection Drawer */}
      {selectedTask && (
        <div className="card" style={{ border: '1px solid var(--accent-blue-border)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="card-header">
            <div className="card-title">
              <Eye size={16} color="var(--accent-blue)" />
              Task Execution Lifecycle & Decision: <span className="mono">{selectedTask.id}</span>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => setSelectedTask(null)}>
              Close
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ backgroundColor: 'var(--bg-surface-sunken)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Task Type & Priority</div>
              <div className="mono" style={{ fontWeight: 700, marginTop: '2px' }}>{selectedTask.task_type} (P{selectedTask.priority})</div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-surface-sunken)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Assigned Worker</div>
              <div className="mono" style={{ fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '2px' }}>
                {selectedTask.assigned_node_id || 'Unassigned'}
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-surface-sunken)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Status</div>
              <span className={`badge badge-${selectedTask.status}`} style={{ marginTop: '4px' }}>
                {selectedTask.status.toUpperCase()}
              </span>
            </div>

            <div style={{ backgroundColor: 'var(--bg-surface-sunken)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Duration</div>
              <div className="mono" style={{ fontWeight: 700, marginTop: '2px' }}>
                {selectedTask.result?.execution_time_seconds ? `${Number(selectedTask.result.execution_time_seconds).toFixed(3)}s` : 'In flight'}
              </div>
            </div>
          </div>

          {selectedDecision && (
            <div style={{ backgroundColor: 'var(--bg-surface-sunken)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-blue)', marginBottom: '0.4rem' }}>
                Auction Bidding Breakdown:
              </div>
              <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Policy: <strong>{selectedDecision.policy_used}</strong> &bull; Candidates: {selectedDecision.candidate_node_ids?.join(', ')}
              </div>
            </div>
          )}

          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>Payload:</div>
            <pre className="mono" style={{ backgroundColor: 'var(--bg-surface-sunken)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-secondary)', maxHeight: '180px', overflowY: 'auto' }}>
              {JSON.stringify(selectedTask.payload, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

