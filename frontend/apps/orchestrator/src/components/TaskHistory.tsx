import React, { useState, useEffect } from 'react'
import {
  History,
  RefreshCw,
  Search,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Eye,
  RotateCcw,
  Layers,
  X,
  Filter,
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Task, TaskStatus } from '@shared/types'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'
import { TaskDetailsDrawer } from '@shared/components/TaskDetailsDrawer'

export const TaskHistory: React.FC = () => {
  const { can } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  // Retry state
  const [retryTask, setRetryTask] = useState<Task | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchHistory = async () => {
    try {
      setLoading(true)
      const data = await api.listTasks(undefined, 250)
      // Historical tasks are completed, failed, cancelled, or dlq
      const historyOnly = data.filter((t) =>
        ['completed', 'failed', 'cancelled', 'dlq'].includes(t.status)
      )
      setTasks(historyOnly)
    } catch (err) {
      console.error('Failed to fetch task history:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleRetry = async () => {
    if (!retryTask) return
    setActionLoading(true)
    try {
      await api.retryTask(retryTask.id)
      setRetryTask(null)
      await fetchHistory()
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const filteredTasks = tasks.filter((t) => {
    const matchesSearch =
      t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.idempotency_key && t.idempotency_key.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (t.assigned_node_id && t.assigned_node_id.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter
    const matchesType = typeFilter === 'all' || t.task_type === typeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  const completedCount = tasks.filter((t) => t.status === 'completed').length
  const failedCount = tasks.filter((t) => t.status === 'failed' || t.status === 'dlq').length
  const successRate = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 100

  const avgDuration =
    tasks.filter((t) => t.result?.execution_time_seconds).length > 0
      ? (
          tasks.reduce((acc, t) => acc + (t.result?.execution_time_seconds || 0), 0) /
          tasks.filter((t) => t.result?.execution_time_seconds).length
        ).toFixed(2)
      : '0.00'

  const taskTypes = Array.from(new Set(tasks.map((t) => t.task_type)))

  return (
    <div>
      {/* Historical KPIs */}
      <div className="grid grid-4" style={{ marginBottom: '1.25rem' }}>
        <div className="stat-card">
          <div className="stat-label">Total Completed History</div>
          <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
            {completedCount}
          </div>
          <div className="stat-hint">Successfully finalized</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Failed / Terminated</div>
          <div className="stat-value" style={{ color: failedCount > 0 ? 'var(--status-failed)' : 'var(--text-color)' }}>
            {failedCount}
          </div>
          <div className="stat-hint">Errors & aborted leases</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Historical Success Rate</div>
          <div className="stat-value" style={{ color: successRate >= 95 ? 'var(--accent-green)' : 'var(--status-degraded)' }}>
            {successRate}%
          </div>
          <div className="stat-hint">Across all recorded workloads</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Avg Execution Latency</div>
          <div className="stat-value mono" style={{ color: 'var(--accent-cyan)' }}>
            {avgDuration}s
          </div>
          <div className="stat-hint">Worker inference compute time</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flex: 1, minWidth: '300px' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input
                type="text"
                placeholder="Search history by Task ID, Idempotency key, Node..."
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
              <option value="all">All Outcomes ({tasks.length})</option>
              <option value="completed">Completed ({completedCount})</option>
              <option value="failed">Failed ({tasks.filter((t) => t.status === 'failed').length})</option>
              <option value="cancelled">Cancelled ({tasks.filter((t) => t.status === 'cancelled').length})</option>
              <option value="dlq">DLQ ({tasks.filter((t) => t.status === 'dlq').length})</option>
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
          <button className="btn btn-secondary btn-sm" onClick={fetchHistory} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* History Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">Completed Workload History</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
            Showing {filteredTasks.length} recorded items
          </span>
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Outcome</th>
                <th>Assigned Node</th>
                <th>Duration</th>
                <th>Completed At</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No historical tasks recorded.
                  </td>
                </tr>
              ) : (
                filteredTasks.map((task) => {
                  return (
                    <tr key={task.id} style={{ cursor: 'pointer' }} onClick={() => setSelectedTask(task)}>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        <span title={task.id}>{task.id.slice(0, 12)}...</span>
                      </td>
                      <td>
                        <span className="badge badge-blue">{task.task_type}</span>
                      </td>
                      <td>
                        <span className="badge badge-slate">P{task.priority}</span>
                      </td>
                      <td>
                        <span className={`status-pill ${task.status}`}>{task.status}</span>
                      </td>
                      <td className="mono" style={{ color: 'var(--accent-cyan)' }}>
                        {task.assigned_node_id || '-'}
                      </td>
                      <td className="mono" style={{ fontSize: '0.8rem' }}>
                        {task.result?.execution_time_seconds ? (
                          <span style={{ color: 'var(--accent-green)' }}>
                            {Number(task.result.execution_time_seconds).toFixed(2)}s
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-dim)' }}>-</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                        {task.result?.completed_at
                          ? new Date(task.result.completed_at).toLocaleString()
                          : new Date(task.updated_at).toLocaleString()}
                      </td>
                      <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                          <button
                            className="btn btn-secondary btn-icon"
                            title="Inspect Payload & Output"
                            onClick={() => setSelectedTask(task)}
                          >
                            <Eye size={14} />
                          </button>
                          {(task.status === 'failed' || task.status === 'dlq') && can('tasks:retry') && (
                            <button
                              className="btn btn-secondary btn-icon"
                              title="Re-run Task"
                              onClick={() => setRetryTask(task)}
                            >
                              <RotateCcw size={14} />
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
      <TaskDetailsDrawer
        task={selectedTask}
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        onRetry={(id) => {
          const t = tasks.find((x) => x.id === id)
          if (t) setRetryTask(t)
        }}
      />

      {/* Confirmation Modal */}
      {retryTask && (
        <ConfirmationModal
          isOpen={true}
          title="Retry Historical Task"
          message={`Re-execute task ${retryTask.id}? A fresh lease will be assigned and the task will enter the active queue.`}
          affectedComponents={[`Task ${retryTask.id}`, 'Scheduler Dispatch Queue']}
          loading={actionLoading}
          onConfirm={handleRetry}
          onCancel={() => setRetryTask(null)}
        />
      )}
    </div>
  )
}

