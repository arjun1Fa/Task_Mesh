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
import { TaskDetailsDrawer } from '@shared/components/TaskDetailsDrawer'

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
                (task: any) => {
                  const taskId = task.id || task.task_id || 'unknown'
                  const execTime = task.result?.execution_time_seconds ?? task.execution_time_seconds
                  const createdAt = task.scheduled_at || task.created_at || task.started_at
                  return (
                    <tr key={taskId} style={{ cursor: 'pointer' }} onClick={() => setSelectedTask(task)}>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        <span title={taskId}>{taskId.slice(0, 14)}...</span>
                      </td>
                      <td>
                        <span className="badge badge-blue">{task.task_type}</span>
                      </td>
                      <td>
                        <span className="badge badge-slate">P{task.priority ?? 5}</span>
                      </td>
                      <td>
                        <span className={`status-pill ${task.status}`}>{task.status}</span>
                      </td>
                      <td className="mono" style={{ fontSize: '0.8rem' }}>
                        {execTime !== undefined ? (
                          <span style={{ color: 'var(--accent-green)' }}>
                            {Number(execTime).toFixed(2)}s
                          </span>
                        ) : (
                          <span style={{ color: 'var(--accent-cyan)' }}>Running...</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                        {createdAt ? new Date(createdAt).toLocaleTimeString() : 'N/A'}
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
                }
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Drawer */}
      <TaskDetailsDrawer
        task={selectedTask}
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
      />
    </div>
  )
}

