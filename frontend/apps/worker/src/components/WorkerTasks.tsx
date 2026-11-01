import React, { useState, useEffect } from 'react'
import {
  Layers,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Eye,
  Activity,
  Zap,
  Cpu,
  X,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { Task, WorkerTasksResponse } from '@shared/types'

export const WorkerTasks: React.FC = () => {
  const [tasksData, setTasksData] = useState<WorkerTasksResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [activeTab, setActiveTab] = useState<'active' | 'completed' | 'failed'>('active')

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const res = await workerApi.getTasks()
      setTasksData(res)
    } catch (err) {
      console.error('Failed to load worker tasks:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
    const interval = setInterval(fetchTasks, 3000)
    return () => clearInterval(interval)
  }, [])

  const activeTasks: Task[] = (tasksData?.active_tasks as any) || []
  const completedTasks: Task[] = (tasksData?.recent_completed as any) || []
  const failedTasks: Task[] = (tasksData?.recent_failed as any) || []

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Layers size={20} color="var(--accent-purple)" />
            Local Task Execution
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Workloads currently dispatched and executing on this machine's CPU/GPU worker thread pool
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={fetchTasks} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          className={`btn btn-sm ${activeTab === 'active' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('active')}
        >
          Active Tasks ({activeTasks.length})
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'completed' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('completed')}
        >
          Recent Completed ({completedTasks.length})
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'failed' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('failed')}
        >
          Recent Failed ({failedTasks.length})
        </button>
      </div>

      {/* Table */}
      <div className="card">
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Execution Duration</th>
                <th>Scheduled At</th>
                <th style={{ textAlign: 'right' }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {activeTab === 'active' && activeTasks.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No tasks are currently running on this worker. Concurrency pool is idle and ready.
                  </td>
                </tr>
              )}
              {activeTab === 'completed' && completedTasks.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No completed tasks recorded in recent buffer.
                  </td>
                </tr>
              )}
              {activeTab === 'failed' && failedTasks.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No failed tasks recorded. All workloads executed successfully.
                  </td>
                </tr>
              )}

              {(activeTab === 'active' ? activeTasks : activeTab === 'completed' ? completedTasks : failedTasks).map(
                (task: Task) => (
                  <tr key={task.id} style={{ cursor: 'pointer' }} onClick={() => setSelectedTask(task)}>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      <span title={task.id}>{task.id.slice(0, 14)}...</span>
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
                    <td className="mono" style={{ fontSize: '0.8rem' }}>
                      {task.result?.execution_time_seconds ? (
                        <span style={{ color: 'var(--accent-green)' }}>
                          {Number(task.result.execution_time_seconds).toFixed(2)}s
                        </span>
                      ) : (
                        <span style={{ color: 'var(--accent-cyan)' }}>Running...</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                      {new Date(task.scheduled_at || task.created_at).toLocaleTimeString()}
                    </td>
                    <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn btn-secondary btn-icon"
                        title="Inspect Task"
                        onClick={() => setSelectedTask(task)}
                      >
                        <Eye size={14} />
                      </button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Drawer */}
      {selectedTask && (
        <div className="modal-backdrop" onClick={() => setSelectedTask(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Layers size={18} color="var(--accent-purple)" />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
                  Worker Task Record: <span className="mono">{selectedTask.id}</span>
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
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Task Type</div>
                  <div className="mono" style={{ marginTop: '0.25rem', fontWeight: 600 }}>
                    {selectedTask.task_type}
                  </div>
                </div>
                <div className="card" style={{ margin: 0, padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Compute Time</div>
                  <div className="mono" style={{ marginTop: '0.25rem', color: 'var(--accent-green)' }}>
                    {selectedTask.result?.execution_time_seconds
                      ? `${Number(selectedTask.result.execution_time_seconds).toFixed(3)}s`
                      : 'Executing'}
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
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>Output / Result</div>
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

