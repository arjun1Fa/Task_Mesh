import React, { useState } from 'react'
import {
  Activity,
  Layers,
  Server,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Clock,
  HelpCircle,
  X,
  Play,
  RotateCcw,
  AlertTriangle,
  Zap,
} from 'lucide-react'
import type { DashboardEvent, NodeProfile, SchedulerDecision, Task } from '../../types'

interface LiveTaskMonitorProps {
  nodes: NodeProfile[]
  tasks: Task[]
  decisions: SchedulerDecision[]
  events: DashboardEvent[]
  onSelectNode: (nodeId: string) => void
}

export const LiveTaskMonitor: React.FC<LiveTaskMonitorProps> = ({
  nodes,
  tasks,
  decisions,
  events,
  onSelectNode,
}) => {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [selectedDecision, setSelectedDecision] = useState<SchedulerDecision | null>(null)

  const runningTasks = tasks.filter((t) => t.status === 'running')
  const pendingTasks = tasks.filter((t) => t.status === 'pending')

  const handleOpenTaskDetail = (task: Task) => {
    setSelectedTask(task)
    // Find matching decision
    const dec = decisions.find((d) => d.task_id === task.id) || null
    setSelectedDecision(dec)
  }

  return (
    <div>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Live Task Allocation & Dispatch Monitor</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Real-time topology flow from Orchestrator Control Plane to distributed Compute Workers
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem' }}>
          <span className="badge badge-blue" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.3rem 0.6rem' }}>
            <span className="pulse-dot" />
            Live Reactive Stream
          </span>
        </div>
      </div>

      {/* TOPOLOGY ALLOCATION MAP */}
      <div className="panel" style={{ marginBottom: '1.5rem' }}>
        <div className="panel-header">
          <div className="panel-title">
            <Layers size={16} color="var(--accent-cyan)" />
            <span>Distributed Task Allocation Topology</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            {runningTasks.length} active assignments currently executing
          </span>
        </div>

        <div className="panel-body" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)', padding: '2rem 1.5rem' }}>
          <div className="allocation-tree">
            {/* Orchestrator Master Hub */}
            <div className="node-hub-card">
              <div style={{
                width: 44,
                height: 44,
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, #06B6D4 0%, #2563EB 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 15px rgba(6, 182, 212, 0.3)',
              }}>
                <Server size={22} color="#fff" />
              </div>
              <div>
                <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--accent-cyan)', fontWeight: 700, letterSpacing: '0.05em' }}>
                  Central Control Plane
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                  TaskMesh Orchestrator
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                  Queue: <strong className="mono" style={{ color: 'var(--accent-amber)' }}>{pendingTasks.length} pending</strong> | Active Dispatcher: <strong style={{ color: 'var(--accent-emerald)' }}>RUNNING</strong>
                </div>
              </div>
            </div>

            {/* Connecting Visual Trunk */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ width: 2, height: 28, backgroundColor: 'var(--accent-cyan)', opacity: 0.7 }} />
              <div style={{
                padding: '0.2rem 0.6rem',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                borderRadius: '9999px',
                fontSize: '0.68rem',
                color: 'var(--accent-cyan)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>
                Adaptive Scheduling Pipeline (EWMA + DRR + Q-Learning)
              </div>
              <div style={{ width: 2, height: 28, backgroundColor: 'var(--accent-cyan)', opacity: 0.7 }} />
            </div>

            {/* Worker Nodes Leaves */}
            <div className="workers-branch">
              {nodes.length === 0 ? (
                <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                  No worker compute nodes registered.
                </div>
              ) : (
                nodes.map((node) => {
                  const assignedToThisNode = runningTasks.filter((t) => t.assigned_node_id === node.id)
                  const isOnline = node.status === 'online'
                  const cpu = node.telemetry?.cpu_percent || 0
                  const capacity = node.capabilities.worker_capacity || 4

                  return (
                    <div
                      key={node.id}
                      className="worker-node-leaf"
                      onClick={() => onSelectNode(node.id)}
                      style={{
                        cursor: 'pointer',
                        borderColor: assignedToThisNode.length > 0 ? 'var(--accent-cyan)' : undefined,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.65rem' }}>
                        <div>
                          <div className="mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fff' }}>
                            {node.id}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                            {node.capabilities.hostname || 'localhost'} ({node.capabilities.ip_address || '127.0.0.1'})
                          </div>
                        </div>
                        <span className={`status-pill ${node.status}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                          <span className="pulse-dot" />
                          {node.status}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>
                        <span>Utilization ({cpu}%)</span>
                        <span className="mono">{assignedToThisNode.length} / {capacity} slots</span>
                      </div>

                      <div className="progress-bar-bg" style={{ marginBottom: '0.85rem' }}>
                        <div
                          className="progress-bar-fill"
                          style={{
                            width: `${Math.min(100, (assignedToThisNode.length / capacity) * 100)}%`,
                            backgroundColor: assignedToThisNode.length > 0 ? 'var(--accent-cyan)' : 'var(--border-main)',
                          }}
                        />
                      </div>

                      {/* Active Tasks Chips */}
                      <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                          Active Assigned Tasks ({assignedToThisNode.length}):
                        </div>
                        {assignedToThisNode.length === 0 ? (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                            Idle (Ready for assignment)
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                            {assignedToThisNode.map((task) => (
                              <div
                                key={task.id}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleOpenTaskDetail(task)
                                }}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  padding: '0.35rem 0.55rem',
                                  backgroundColor: 'rgba(6, 182, 212, 0.08)',
                                  border: '1px solid rgba(6, 182, 212, 0.25)',
                                  borderRadius: 'var(--radius-sm)',
                                  fontSize: '0.75rem',
                                }}
                              >
                                <span className="mono" style={{ color: 'var(--accent-cyan)' }}>
                                  {task.id.slice(0, 14)}...
                                </span>
                                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                  {task.task_type}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Live Activity Feed & Running Tasks List */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.25rem' }}>

        {/* Live Task Activity Feed */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <Activity size={16} />
              <span>Real-Time Activity Feed</span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Latest events</span>
          </div>

          <div className="panel-body" style={{ maxHeight: '420px', overflowY: 'auto' }}>
            {events.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                Waiting for cluster activity events...
              </div>
            ) : (
              <div className="activity-feed">
                {events.slice(0, 30).map((evt) => {
                  let badgeType = 'assigned'
                  if (evt.event_type.includes('completed')) badgeType = 'completed'
                  if (evt.event_type.includes('failed')) badgeType = 'failed'
                  if (evt.event_type.includes('retrying')) badgeType = 'retried'

                  return (
                    <div key={evt.event_id} className={`activity-item ${badgeType}`}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong className="mono" style={{ fontSize: '0.8rem', color: '#fff' }}>
                            {evt.event_type}
                          </strong>
                          <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                            {new Date(evt.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {evt.entity_id && <span className="mono" style={{ color: 'var(--accent-cyan)', marginRight: '6px' }}>[{evt.entity_id.slice(0, 16)}]</span>}
                          {evt.data.selected_node_id && (
                            <span>Assigned to <strong className="mono" style={{ color: '#fff' }}>{evt.data.selected_node_id}</strong> via {evt.data.policy_used}</span>
                          )}
                          {evt.data.execution_time_seconds && (
                            <span>Execution duration: <strong className="mono">{evt.data.execution_time_seconds.toFixed(2)}s</strong></span>
                          )}
                          {evt.data.error && (
                            <span style={{ color: 'var(--accent-rose)' }}>{evt.data.error}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Currently Executing Tasks with Explainability Shortcut */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <Play size={16} color="var(--accent-cyan)" />
              <span>Active In-Flight Executions</span>
            </div>
            <span className="badge badge-blue">{runningTasks.length} running</span>
          </div>

          <div className="panel-body" style={{ maxHeight: '420px', overflowY: 'auto' }}>
            {runningTasks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                No tasks currently under active execution.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                {runningTasks.map((t) => (
                  <div
                    key={t.id}
                    onClick={() => handleOpenTaskDetail(t)}
                    style={{
                      padding: '0.85rem',
                      backgroundColor: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid var(--border-main)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      transition: 'border-color 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent-cyan)')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-main)')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <span className="mono" style={{ fontWeight: 600, color: '#fff' }}>{t.id}</span>
                      <span className="badge badge-blue">Attempt {t.current_attempt}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      <span>Type: <strong>{t.task_type}</strong></span>
                      <span>Node: <strong className="mono" style={{ color: 'var(--accent-cyan)' }}>{t.assigned_node_id}</strong></span>
                    </div>

                    <div style={{ marginTop: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                      <span>Lease: {t.timeout_seconds}s timeout</span>
                      <span style={{ color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '2px' }}>
                        Why this node? <ArrowRight size={12} />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* TASK DETAIL & SCHEDULER EXPLAINABILITY MODAL */}
      {selectedTask && (
        <div className="modal-backdrop" onClick={() => setSelectedTask(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '750px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Zap size={20} color="var(--accent-cyan)" />
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Task Dispatch Diagnostics</h3>
                  <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{selectedTask.id}</div>
                </div>
              </div>
              <button className="btn btn-secondary btn-icon" onClick={() => setSelectedTask(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              {/* Task Core Metadata */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ padding: '0.65rem 0.85rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Task Type</div>
                  <strong style={{ fontSize: '0.88rem' }}>{selectedTask.task_type}</strong>
                </div>

                <div style={{ padding: '0.65rem 0.85rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Current State</div>
                  <strong className={`badge ${selectedTask.status === 'completed' ? 'badge-emerald' : selectedTask.status === 'running' ? 'badge-blue' : 'badge-rose'}`} style={{ marginTop: '2px' }}>
                    {selectedTask.status}
                  </strong>
                </div>

                <div style={{ padding: '0.65rem 0.85rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Assigned Node</div>
                  <strong className="mono" style={{ fontSize: '0.88rem', color: 'var(--accent-cyan)' }}>
                    {selectedTask.assigned_node_id || 'None'}
                  </strong>
                </div>
              </div>

              {/* WHY WAS THIS NODE SELECTED? (EXPLAINABILITY SECTION) */}
              <div style={{
                padding: '1.1rem',
                backgroundColor: 'rgba(6, 182, 212, 0.04)',
                border: '1px solid rgba(6, 182, 212, 0.25)',
                borderRadius: 'var(--radius-lg)',
                marginBottom: '1.25rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <HelpCircle size={18} color="var(--accent-cyan)" />
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                    WHY WAS THIS NODE SELECTED?
                  </h4>
                </div>

                {selectedDecision ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
                    <div>
                      <span style={{ color: 'var(--text-dim)' }}>Policy Engine Used:</span>{' '}
                      <strong className="badge badge-purple">{selectedDecision.policy_used}</strong>
                    </div>

                    {/* Candidate Bids Comparison */}
                    {selectedDecision.bids && Object.keys(selectedDecision.bids).length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                          Contract-Net Bids across Candidates:
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                          {Object.entries(selectedDecision.bids).map(([nid, bid]) => {
                            const isWinner = nid === selectedDecision.selected_node_id
                            return (
                              <div
                                key={nid}
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  padding: '0.35rem 0.6rem',
                                  backgroundColor: isWinner ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                                  border: isWinner ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-main)',
                                  borderRadius: 'var(--radius-sm)',
                                }}
                              >
                                <span className="mono">{nid} {isWinner && '★ (Winner)'}</span>
                                <span className="mono" style={{ fontWeight: 700, color: isWinner ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
                                  Bid Score: {bid.toFixed(4)}
                                </span>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}

                    {/* Wireless Network-Aware Cost Comparison */}
                    {selectedDecision.local_estimate_ms !== undefined && selectedDecision.remote_estimate_ms !== undefined && (
                      <div style={{
                        marginTop: '0.5rem',
                        padding: '0.75rem',
                        backgroundColor: 'rgba(0, 0, 0, 0.25)',
                        borderRadius: 'var(--radius-md)',
                      }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                          Wireless Cost Estimator Breakdown:
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                          <div>
                            <span style={{ color: 'var(--text-dim)' }}>Local Execution Estimate:</span>
                            <div className="mono" style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                              {selectedDecision.local_estimate_ms.toFixed(1)} ms
                            </div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-dim)' }}>Remote Total Estimate:</span>
                            <div className="mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                              {selectedDecision.remote_estimate_ms.toFixed(1)} ms
                            </div>
                          </div>
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                          Decision: <strong>{selectedDecision.offload_decision?.toUpperCase()}</strong> ({selectedDecision.offload_reason || 'Optimal estimated completion time'})
                        </div>
                      </div>
                    )}

                    {/* Q-Learning Slot Selection */}
                    {selectedDecision.rl_action !== undefined && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        Q-Learning Action: Slot <strong>{selectedDecision.rl_action}</strong> selected from ranked candidates (State: {JSON.stringify(selectedDecision.rl_state)})
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>
                    Detailed scheduling decision telemetry for this task attempt is not in memory or was dispatched prior to the latest snapshot.
                  </div>
                )}
              </div>

              {/* Task Result Details if completed */}
              {selectedTask.result && (
                <div style={{
                  padding: '1rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-main)',
                }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '0.4rem' }}>
                    Execution Result Output
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                    <span>Duration: <strong className="mono">{selectedTask.result.execution_time_seconds.toFixed(3)}s</strong></span>
                    <span>Completed: {new Date(selectedTask.result.completed_at).toLocaleTimeString()}</span>
                  </div>
                  <pre className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-main)', backgroundColor: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', overflowX: 'auto' }}>
                    {JSON.stringify(selectedTask.result.output || selectedTask.result.metrics, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setSelectedTask(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

