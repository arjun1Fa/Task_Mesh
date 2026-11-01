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
  Cpu
} from 'lucide-react'
import { api } from '../../api/client'
import type { Task } from '../../types'

interface WorkerTaskExecutionProps {
  nodeId: string
}

export const WorkerTaskExecutionPage: React.FC<WorkerTaskExecutionProps> = ({ nodeId }) => {
  const [tasksData, setTasksData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const res = await api.getWorkerTasks(nodeId)
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
  }, [nodeId])

  const activeTasks: Task[] = tasksData?.active_tasks || []
  const completedTasks: Task[] = tasksData?.recent_completed || []
  const failedTasks: Task[] = tasksData?.recent_failed || []

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono uppercase tracking-wider text-secondary">
              Worker Agent Console
            </span>
            <span className="text-gray-600">&bull;</span>
            <span className="text-xs font-mono text-cyan-400 font-bold">{nodeId}</span>
          </div>
          <h1 className="page-title flex items-center gap-2">
            <Layers className="text-cyan-400" size={24} />
            Task Execution & History
          </h1>
          <p className="page-description">
            In-flight task execution, AI inference latency decomposition, and recent completion logs on this node.
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

      {/* Active Tasks Section */}
      <div className="card mb-6">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary flex items-center gap-2">
            <Activity size={16} className="text-blue-400" /> In-Flight Executing Tasks ({activeTasks.length})
          </h2>
        </div>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Started</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activeTasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-6 text-secondary">
                    No active tasks currently executing on this worker
                  </td>
                </tr>
              ) : (
                activeTasks.map((t) => (
                  <tr key={t.id} className="hover:bg-[#1a1d24]">
                    <td className="font-mono text-xs text-blue-400 font-bold">
                      {t.id.slice(0, 14)}...
                    </td>
                    <td className="font-mono text-xs text-gray-300">{t.task_type}</td>
                    <td>
                      <span className="badge badge-pending font-mono text-xs">P{t.priority}</span>
                    </td>
                    <td>
                      <span className="badge badge-running">RUNNING</span>
                    </td>
                    <td className="font-mono text-xs text-secondary">
                      {t.scheduled_at ? new Date(t.scheduled_at).toLocaleTimeString() : 'In-flight'}
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedTask(t)}
                        className="btn btn-secondary px-2 py-1 text-xs"
                      >
                        <Eye size={12} /> Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recently Completed Tasks */}
      <div className="card mb-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
          <CheckCircle size={16} className="text-emerald-400" /> Recently Completed ({completedTasks.length})
        </h2>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Type</th>
                <th>Execution Time</th>
                <th>Completed At</th>
                <th>Status</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {completedTasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-6 text-secondary">
                    No recent completions recorded in local buffer
                  </td>
                </tr>
              ) : (
                completedTasks.map((t) => (
                  <tr key={t.id} className="hover:bg-[#1a1d24]">
                    <td className="font-mono text-xs text-emerald-400 font-bold">
                      {t.id.slice(0, 14)}...
                    </td>
                    <td className="font-mono text-xs text-gray-300">{t.task_type}</td>
                    <td className="font-mono text-xs text-white">
                      {t.result?.execution_time_seconds !== undefined
                        ? `${Number(t.result.execution_time_seconds).toFixed(3)}s`
                        : 'N/A'}
                    </td>
                    <td className="font-mono text-xs text-secondary">
                      {t.result?.completed_at
                        ? new Date(t.result.completed_at).toLocaleTimeString()
                        : new Date(t.updated_at).toLocaleTimeString()}
                    </td>
                    <td>
                      <span className="badge badge-completed">COMPLETED</span>
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedTask(t)}
                        className="btn btn-secondary px-2 py-1 text-xs"
                      >
                        <Eye size={12} /> Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Inspection Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="card max-w-2xl w-full bg-[#14161b] border-[#2d3139] max-h-[85vh] flex flex-col">
            <div className="flex justify-between items-center pb-3 border-b border-[#2d3139] mb-3">
              <div>
                <h3 className="font-semibold text-base text-white font-mono">
                  Task Execution: {selectedTask.id}
                </h3>
                <span className={`badge badge-${selectedTask.status} mt-1`}>
                  {selectedTask.status.toUpperCase()}
                </span>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="text-gray-400 hover:text-white font-mono text-lg"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 text-xs font-mono p-2">
              {/* Result & Latency metrics */}
              {selectedTask.result && (
                <div className="bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                  <div className="font-bold text-emerald-400 mb-1 flex items-center gap-1">
                    <CheckCircle size={14} /> Execution Metrics
                  </div>
                  <div className="text-gray-300">
                    Duration: {selectedTask.result.execution_time_seconds?.toFixed(4)}s
                  </div>
                  {selectedTask.result.metrics && (
                    <pre className="bg-[#0f1013] p-2 rounded text-gray-300 mt-2">
                      {JSON.stringify(selectedTask.result.metrics, null, 2)}
                    </pre>
                  )}
                  {selectedTask.result.output && (
                    <div className="mt-2">
                      <span className="text-secondary block font-bold mb-1">Output:</span>
                      <pre className="bg-[#0f1013] p-2 rounded text-gray-300 max-h-36 overflow-y-auto">
                        {JSON.stringify(selectedTask.result.output, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Payload */}
              <div>
                <span className="text-secondary block font-bold mb-1">Input Payload:</span>
                <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-40 overflow-y-auto">
                  {JSON.stringify(selectedTask.payload, null, 2)}
                </pre>
              </div>
            </div>

            <div className="p-3 border-t border-[#2d3139] flex justify-end mt-4">
              <button
                onClick={() => setSelectedTask(null)}
                className="btn btn-secondary text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

