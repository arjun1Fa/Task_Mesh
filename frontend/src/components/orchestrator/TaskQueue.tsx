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
  Cpu
} from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import type { Task, TaskStatus } from '../../types'
import { ConfirmationModal } from '../common/ConfirmationModal'

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
      setActionError(err.message || 'Action failed')
    } finally {
      setActionLoading(false)
    }
  }

  const uniqueTypes = Array.from(new Set(tasks.map((t) => t.task_type)))

  const filteredTasks = tasks.filter((t) => {
    if (typeFilter !== 'all' && t.task_type !== typeFilter) return false
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchId = t.id.toLowerCase().includes(q)
      const matchType = t.task_type.toLowerCase().includes(q)
      const matchNode = t.assigned_node_id?.toLowerCase().includes(q)
      if (!matchId && !matchType && !matchNode) return false
    }
    return true
  })

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Layers className="text-blue-400" size={24} />
            Global Task Queue & Operations
          </h1>
          <p className="page-description">
            Complete lifecycle inspection, priority ordering, lease monitoring, and cancellation/retry controls.
          </p>
        </div>
        <button
          onClick={fetchTasks}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="card mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1">
              <ListFilter size={14} /> Status:
            </span>
            {['all', 'pending', 'scheduled', 'running', 'completed', 'failed', 'retrying', 'cancelled', 'dlq'].map(
              (st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 text-xs font-mono rounded-md border transition-colors ${
                    statusFilter === st
                      ? 'bg-blue-600/20 border-blue-500 text-blue-300 font-semibold'
                      : 'bg-[#181a1f] border-[#2d3139] text-gray-400 hover:border-gray-500'
                  }`}
                >
                  {st.toUpperCase()}
                </button>
              )
            )}
          </div>

          <div className="flex items-center gap-3">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded-md px-3 py-1.5 focus:border-blue-500 outline-none"
            >
              <option value="all">All Task Types</option>
              {uniqueTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>

            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-2.5 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ID, type, node..."
                className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded-md pl-8 pr-3 py-1.5 focus:border-blue-500 outline-none w-56"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <div className="text-xs text-secondary font-mono">
            Showing <span className="text-white font-semibold">{filteredTasks.length}</span> of {tasks.length} tasks
          </div>
        </div>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assigned Node</th>
                <th>Attempt</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-secondary">
                    No tasks found matching criteria
                  </td>
                </tr>
              ) : (
                filteredTasks.map((task) => (
                  <tr key={task.id} className="hover:bg-[#1a1d24]">
                    <td className="font-mono text-xs text-blue-400 font-semibold">
                      {task.id.slice(0, 12)}...
                    </td>
                    <td>
                      <span className="inline-flex items-center gap-1 font-mono text-xs text-gray-300">
                        {task.requires_gpu && <Cpu size={12} className="text-purple-400" />}
                        {task.task_type}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`inline-block px-2 py-0.5 text-xs font-mono font-bold rounded ${
                          task.priority >= 9
                            ? 'bg-red-900/40 text-red-300 border border-red-700/50'
                            : task.priority >= 6
                            ? 'bg-amber-900/40 text-amber-300 border border-amber-700/50'
                            : 'bg-gray-800 text-gray-300'
                        }`}
                      >
                        P{task.priority}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-${task.status}`}>{task.status.toUpperCase()}</span>
                    </td>
                    <td className="font-mono text-xs text-gray-300">
                      {task.assigned_node_id ? (
                        <span className="text-green-400">{task.assigned_node_id}</span>
                      ) : (
                        <span className="text-gray-500 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="font-mono text-xs text-gray-400">
                      {task.current_attempt || 1} / {task.retry_count + 1}
                    </td>
                    <td className="text-xs text-secondary font-mono">
                      {new Date(task.created_at).toLocaleTimeString()}
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedTask(task)}
                          className="btn btn-secondary px-2 py-1 text-xs"
                          title="Inspect Details"
                        >
                          <Eye size={13} />
                        </button>
                        {['pending', 'scheduled', 'running'].includes(task.status) && can('task:cancel') && (
                          <button
                            onClick={() => setActionTask({ task, action: 'cancel' })}
                            className="btn btn-danger px-2 py-1 text-xs"
                            title="Cancel Task"
                          >
                            <Ban size={13} />
                          </button>
                        )}
                        {['failed', 'cancelled', 'dlq'].includes(task.status) && can('task:retry') && (
                          <button
                            onClick={() => setActionTask({ task, action: 'retry' })}
                            className="btn btn-secondary px-2 py-1 text-xs text-amber-400 hover:text-amber-300"
                            title="Retry Task"
                          >
                            <RotateCcw size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Inspection Drawer / Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="card max-w-3xl w-full max-h-[85vh] flex flex-col bg-[#14161b] border-[#2d3139]">
            <div className="flex justify-between items-center pb-3 border-b border-[#2d3139]">
              <div>
                <h3 className="font-semibold text-lg text-white font-mono">Task: {selectedTask.id}</h3>
                <span className={`badge badge-${selectedTask.status} mt-1`}>
                  {selectedTask.status.toUpperCase()}
                </span>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="text-gray-400 hover:text-white font-mono text-lg px-2"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto p-4 space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-4 bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                <div>
                  <span className="text-secondary block">Task Type:</span>
                  <span className="text-white font-bold">{selectedTask.task_type}</span>
                </div>
                <div>
                  <span className="text-secondary block">Priority:</span>
                  <span className="text-white font-bold">P{selectedTask.priority}</span>
                </div>
                <div>
                  <span className="text-secondary block">Assigned Node:</span>
                  <span className="text-green-400 font-bold">{selectedTask.assigned_node_id || 'None'}</span>
                </div>
                <div>
                  <span className="text-secondary block">Timeout (sec):</span>
                  <span className="text-white font-bold">{selectedTask.timeout_seconds}s</span>
                </div>
                <div>
                  <span className="text-secondary block">Offload Policy:</span>
                  <span className="text-purple-300 font-bold">{selectedTask.offload_policy}</span>
                </div>
                <div>
                  <span className="text-secondary block">GPU Required:</span>
                  <span className={selectedTask.requires_gpu ? 'text-purple-400 font-bold' : 'text-gray-400'}>
                    {selectedTask.requires_gpu ? 'YES' : 'NO'}
                  </span>
                </div>
              </div>

              {selectedTask.error_message && (
                <div className="bg-red-950/40 border border-red-800/60 p-3 rounded text-red-300">
                  <div className="font-bold flex items-center gap-1.5 mb-1 text-red-400">
                    <AlertTriangle size={14} /> Error Traceback:
                  </div>
                  <pre className="whitespace-pre-wrap">{selectedTask.error_message}</pre>
                </div>
              )}

              {selectedTask.result && (
                <div className="bg-[#181a1f] border border-[#2d3139] p-3 rounded">
                  <div className="font-bold text-green-400 flex items-center gap-1.5 mb-1">
                    <CheckCircle size={14} /> Execution Result ({selectedTask.result.execution_time_seconds.toFixed(3)}s):
                  </div>
                  <pre className="bg-[#0f1013] p-2 rounded text-gray-300 overflow-x-auto">
                    {JSON.stringify(selectedTask.result.output || selectedTask.result, null, 2)}
                  </pre>
                </div>
              )}

              <div>
                <span className="text-secondary block font-bold mb-1">Payload:</span>
                <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-48 overflow-y-auto">
                  {JSON.stringify(selectedTask.payload, null, 2)}
                </pre>
              </div>

              {selectedTask.metadata && Object.keys(selectedTask.metadata).length > 0 && (
                <div>
                  <span className="text-secondary block font-bold mb-1">Metadata:</span>
                  <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-36 overflow-y-auto">
                    {JSON.stringify(selectedTask.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-[#2d3139] flex justify-end gap-2 bg-[#181a1f]">
              <button onClick={() => setSelectedTask(null)} className="btn btn-secondary text-xs">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Confirmation Modal */}
      {actionTask && (
        <ConfirmationModal
          isOpen={true}
          title={actionTask.action === 'retry' ? 'Confirm Task Retry' : 'Confirm Task Cancellation'}
          message={
            actionTask.action === 'retry'
              ? `Re-queue task ${actionTask.task.id} for execution immediately?`
              : `Are you sure you want to cancel executing task ${actionTask.task.id}?`
          }
          confirmLabel={actionTask.action === 'retry' ? 'Re-queue Task' : 'Cancel Task'}
          isDanger={actionTask.action === 'cancel'}
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionTask(null)}
        />
      )}
    </div>
  )
}

