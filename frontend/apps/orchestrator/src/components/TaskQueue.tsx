import React, { useState, useEffect } from 'react'
import {
  ListFilter,
  RefreshCw,
  Search,
  RotateCcw,
  Ban,
  Clock,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Layers,
  Cpu,
  X,
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Task, TaskStatus } from '@shared/types'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'

interface TaskQueueProps {
  initialStatus?: TaskStatus
}

export const TaskQueue: React.FC<TaskQueueProps> = ({ initialStatus }) => {
  const { can } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [statusFilter, setStatusFilter] = useState<string>(initialStatus || 'all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  // Action confirmation state
  const [actionTask, setActionTask] = useState<{ task: Task; action: 'retry' | 'cancel' } | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const st = statusFilter === 'all' ? undefined : (statusFilter as TaskStatus)
      const data = await api.listTasks(st, 150)
      setTasks(data)
    } catch (err: any) {
      console.error('Failed to fetch tasks:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
    const interval = setInterval(fetchTasks, 3000)
    return () => clearInterval(interval)
  }, [statusFilter])

  const handleConfirmAction = async () => {
    if (!actionTask) return
    setActionLoading(true)
    setActionError(null)
    try {
      if (actionTask.action === 'retry') {
        await api.retryTask(actionTask.task.id)
      } else {
        await api.cancelTask(actionTask.task.id, 'User initiated cancellation from console')
      }
      setActionTask(null)
      await fetchTasks()
    } catch (err: any) {
      setActionError(err.message || 'Operation failed')
    } finally {
      setActionLoading(false)
    }
  }

  const filteredTasks = tasks.filter((t) => {
    const matchesSearch =
      t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.idempotency_key && t.idempotency_key.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (t.assigned_node_id && t.assigned_node_id.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesType = typeFilter === 'all' || t.task_type === typeFilter
    return matchesSearch && matchesType
  })

  const taskTypes = Array.from(new Set(tasks.map((t) => t.task_type)))

  return (
    <div>
      {/* Action Bar */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flex: 1, minWidth: '300px' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input
                type="text"
                placeholder="Search by Task ID, Idempotency Key, Node..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '2.2rem' }}
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-input"
              style={{ width: 'auto' }}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="scheduled">Scheduled</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="retrying">Retrying</option>
              <option value="cancelled">Cancelled</option>
              <option value="dlq">DLQ</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="form-input"
              style={{ width: 'auto' }}
            >
              <option value="all">All Types</option>
              {taskTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary btn-sm" onClick={fetchTasks} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Task Queue Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">Active Workload Queue</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
            Showing {filteredTasks.length} tasks
          </span>
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assigned Node</th>
                <th>Attempt</th>
                <th>Duration / Timeout</th>
                <th>Created At</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No tasks found matching criteria.
                  </td>
                </tr>
              ) : (
                filteredTasks.map((task) => {
                  return (
                    <tr key={task.id} style={{ cursor: 'pointer' }} onClick={() => setSelectedTask(task)}>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span title={task.id}>{task.id.slice(0, 8)}...</span>
                          {task.requires_gpu && (
                            <span className="badge badge-amber" style={{ fontSize: '0.65rem', padding: '1px 4px' }}>
                              GPU
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-blue">{task.task_type}</span>
                      </td>
                      <td>
                        <span
                          className={`badge ${task.priority >= 8 ? 'badge-rose' : task.priority >= 5 ? 'badge-amber' : 'badge-slate'}`}
                        >
                          P{task.priority}
                        </span>
                      </td>
                      <td>
                        <span className={`status-pill ${task.status}`}>{task.status}</span>
                      </td>
                      <td className="mono">
                        {task.assigned_node_id ? (
                          <span style={{ color: 'var(--accent-cyan)' }}>{task.assigned_node_id}</span>
                        ) : (
                          <span style={{ color: 'var(--text-dim)' }}>Unassigned</span>
                        )}
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem' }}>
                        {task.current_attempt || 1} / {task.retry_count + 1}
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem' }}>
                        {task.result?.execution_time_seconds ? (
                          <span style={{ color: 'var(--accent-green)' }}>
                            {Number(task.result.execution_time_seconds).toFixed(2)}s
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-dim)' }}>{task.timeout_seconds}s limit</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                        {new Date(task.created_at).toLocaleTimeString()}
                      </td>
                      <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                          <button
                            className="btn btn-secondary btn-icon"
                            title="Inspect Task Details"
                            onClick={() => setSelectedTask(task)}
                          >
                            <Eye size={14} />
                          </button>
                          {(task.status === 'failed' || task.status === 'cancelled' || task.status === 'dlq') &&
                            can('tasks:retry') && (
                              <button
                                className="btn btn-secondary btn-icon"
                                title="Retry Task"
                                onClick={() => setActionTask({ task, action: 'retry' })}
                              >
                                <RotateCcw size={14} />
                              </button>
                            )}
                          {(task.status === 'pending' || task.status === 'scheduled' || task.status === 'running') &&
                            can('tasks:cancel') && (
                              <button
                                className="btn btn-secondary btn-icon"
                                title="Cancel Task"
                                onClick={() => setActionTask({ task, action: 'cancel' })}
                              >
                                <Ban size={14} color="var(--status-failed)" />
                              </button>
                            )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Details Drawer Modal */}
      {selectedTask && (
        <div className="modal-backdrop" onClick={() => setSelectedTask(null)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: '750px', maxHeight: '90vh', overflowY: 'auto' }}
          >
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Layers size={18} color="var(--accent-blue)" />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
                  Task Inspector: <span className="mono">{selectedTask.id}</span>
                </h3>
              </div>
              <button className="btn btn-secondary btn-icon" onClick={() => setSelectedTask(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="grid grid-3" style={{ gap: '0.75rem' }}>
                <div className="card" style={{ margin: 0, padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Status</div>
                  <div style={{ marginTop: '0.25rem' }}>
                    <span className={`status-pill ${selectedTask.status}`}>{selectedTask.status}</span>
                  </div>
                </div>
                <div className="card" style={{ margin: 0, padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Assigned Node</div>
                  <div className="mono" style={{ marginTop: '0.25rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                    {selectedTask.assigned_node_id || 'None'}
                  </div>
                </div>
                <div className="card" style={{ margin: 0, padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Priority & Policy</div>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>
                    P{selectedTask.priority} • {selectedTask.offload_policy}
                  </div>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>Task Payload</div>
                <pre
                  className="code-font"
                  style={{
                    backgroundColor: 'rgba(0,0,0,0.3)',
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-color)',
                    maxHeight: '160px',
                    overflowY: 'auto',
                    fontSize: '0.78rem',
                  }}
                >
                  {JSON.stringify(selectedTask.payload, null, 2)}
                </pre>
              </div>

              {selectedTask.result && (
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>Execution Result</div>
                  <pre
                    className="code-font"
                    style={{
                      backgroundColor: 'rgba(0,0,0,0.3)',
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-color)',
                      maxHeight: '160px',
                      overflowY: 'auto',
                      fontSize: '0.78rem',
                    }}
                  >
                    {JSON.stringify(selectedTask.result, null, 2)}
                  </pre>
                </div>
              )}

              {selectedTask.error_message && (
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--status-failed)' }}>
                    Error Message
                  </div>
                  <pre
                    className="code-font"
                    style={{
                      backgroundColor: 'rgba(239, 68, 68, 0.08)',
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      color: 'var(--status-failed)',
                      fontSize: '0.78rem',
                    }}
                  >
                    {selectedTask.error_message}
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

      {/* Confirmation Modal */}
      {actionTask && (
        <ConfirmationModal
          isOpen={true}
          title={actionTask.action === 'retry' ? 'Confirm Task Retry' : 'Confirm Task Cancellation'}
          message={
            actionTask.action === 'retry'
              ? `Re-enqueue task ${actionTask.task.id} for execution? A new attempt lease will be generated.`
              : `Abort task ${actionTask.task.id}? If currently running on ${actionTask.task.assigned_node_id || 'a node'}, a cancellation signal will be transmitted.`
          }
          affectedComponents={[
            `Task ${actionTask.task.id}`,
            actionTask.task.assigned_node_id || 'Unassigned Queue',
          ]}
          isDangerous={actionTask.action === 'cancel'}
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionTask(null)}
        />
      )}
    </div>
  )
}

