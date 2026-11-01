import React, { useState, useEffect } from 'react'
import {
  AlertOctagon,
  RefreshCw,
  RotateCcw,
  Eye,
  CheckCircle,
  AlertTriangle,
  ShieldCheck,
  Search
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Task } from '@shared/types'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'

interface DlqEntry {
  task: Task
  failed_at: string
  final_error: string
  failure_count: number
}

export const DeadLetterQueue: React.FC = () => {
  const { can } = useAuth()
  const [entries, setEntries] = useState<DlqEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEntry, setSelectedEntry] = useState<DlqEntry | null>(null)

  // Recovery action
  const [recoverTarget, setRecoverTarget] = useState<DlqEntry | null>(null)
  const [recovering, setRecovering] = useState(false)

  const fetchDlq = async () => {
    try {
      setLoading(true)
      const data = await api.listDlq()
      setEntries(data)
    } catch (err) {
      console.error('Failed to fetch DLQ items:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDlq()
    const interval = setInterval(fetchDlq, 4000)
    return () => clearInterval(interval)
  }, [])

  const handleRecover = async () => {
    if (!recoverTarget) return
    try {
      setRecovering(true)
      await api.recoverDlq(recoverTarget.task.id)
      setRecoverTarget(null)
      await fetchDlq()
    } catch (err: any) {
      alert(`Recovery failed: ${err.message}`)
    } finally {
      setRecovering(false)
    }
  }

  const filteredEntries = entries.filter((e) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchId = e.task.id.toLowerCase().includes(q)
      const matchType = e.task.task_type.toLowerCase().includes(q)
      const matchErr = e.final_error?.toLowerCase().includes(q)
      if (!matchId && !matchType && !matchErr) return false
    }
    return true
  })

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <AlertOctagon className="text-red-400" size={24} />
            Dead Letter Queue (DLQ)
          </h1>
          <p className="page-description">
            Isolates tasks that have permanently exceeded retry budgets or encountered fatal unrecoverable errors.
          </p>
        </div>
        <button
          onClick={fetchDlq}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid mb-6">
        <div className="kpi-card">
          <div className="kpi-label">DLQ Queue Depth</div>
          <div className={`kpi-value ${entries.length > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {entries.length}
          </div>
          <div className="kpi-change text-secondary">
            {entries.length === 0 ? 'Zero poisoned tasks in queue' : 'Requires operational inspection'}
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Retry Exhaustion Threshold</div>
          <div className="kpi-value text-white">3 Attempts</div>
          <div className="kpi-change text-secondary">Exponential backoff ceiling: 60s</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Queue Health Status</div>
          <div className="flex items-center gap-2 mt-1">
            {entries.length === 0 ? (
              <span className="badge badge-online text-sm py-1 flex items-center gap-1">
                <CheckCircle size={14} /> HEALTHY (0 DLQ)
              </span>
            ) : (
              <span className="badge badge-failed text-sm py-1 flex items-center gap-1">
                <AlertTriangle size={14} /> ACTION REQUIRED
              </span>
            )}
          </div>
          <div className="kpi-change text-secondary mt-1">Automatic lease expiration handling active</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card mb-4 bg-[#14161b]">
        <div className="flex justify-between items-center">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Task ID or error message..."
              className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded pl-8 pr-3 py-1.5 focus:border-red-500 outline-none w-80 font-mono"
            />
          </div>
          <div className="text-xs text-secondary font-mono">
            Showing <span className="text-white font-bold">{filteredEntries.length}</span> poisoned tasks
          </div>
        </div>
      </div>

      {/* DLQ List */}
      <div className="card">
        {filteredEntries.length === 0 ? (
          <div className="text-center py-16">
            <ShieldCheck size={48} className="mx-auto text-emerald-400 mb-3" />
            <h3 className="text-base font-semibold text-white">Dead Letter Queue is Empty</h3>
            <p className="text-xs text-secondary mt-1 max-w-md mx-auto">
              All submitted tasks have either executed successfully or are completing within normal retry policies.
            </p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Task ID</th>
                  <th>Task Type</th>
                  <th>Failures</th>
                  <th>Failed At</th>
                  <th>Final Error Reason</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry) => (
                  <tr key={entry.task.id} className="hover:bg-[#1a1d24]">
                    <td className="font-mono text-xs text-red-400 font-bold">
                      {entry.task.id.slice(0, 14)}...
                    </td>
                    <td>
                      <span className="font-mono text-xs text-gray-300">{entry.task.task_type}</span>
                    </td>
                    <td>
                      <span className="badge badge-failed font-mono text-xs">
                        {entry.failure_count || entry.task.retry_count} attempts
                      </span>
                    </td>
                    <td className="font-mono text-xs text-secondary">
                      {new Date(entry.failed_at || entry.task.updated_at).toLocaleTimeString()}
                    </td>
                    <td className="font-mono text-xs text-red-300 max-w-md truncate">
                      {entry.final_error || entry.task.error_message || 'Exceeded retry budget'}
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedEntry(entry)}
                          className="btn btn-secondary px-2 py-1 text-xs"
                          title="Inspect Error"
                        >
                          <Eye size={13} />
                        </button>
                        <button
                          onClick={() => setRecoverTarget(entry)}
                          disabled={!can('dlq:recover')}
                          className="btn btn-secondary px-2 py-1 text-xs text-emerald-400 hover:text-emerald-300"
                          title="Recover and Re-queue"
                        >
                          <RotateCcw size={13} /> Recover
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspect Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="card max-w-3xl w-full max-h-[85vh] flex flex-col bg-[#14161b] border-[#2d3139]">
            <div className="flex justify-between items-center pb-3 border-b border-[#2d3139]">
              <div>
                <h3 className="font-semibold text-lg text-white font-mono flex items-center gap-2">
                  <AlertTriangle className="text-red-400" size={18} />
                  DLQ Task Inspection: {selectedEntry.task.id}
                </h3>
                <span className="text-xs text-secondary font-mono">
                  Failed: {new Date(selectedEntry.failed_at).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedEntry(null)}
                className="text-gray-400 hover:text-white font-mono text-lg px-2"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto p-4 space-y-4 text-xs font-mono">
              <div className="bg-red-950/40 border border-red-800 p-3 rounded">
                <span className="text-red-400 block font-bold mb-1">Fatal Error:</span>
                <pre className="text-red-200 whitespace-pre-wrap">
                  {selectedEntry.final_error || selectedEntry.task.error_message || 'Unknown failure'}
                </pre>
              </div>

              <div>
                <span className="text-secondary block font-bold mb-1">Task Payload:</span>
                <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-48 overflow-y-auto">
                  {JSON.stringify(selectedEntry.task.payload, null, 2)}
                </pre>
              </div>

              {selectedEntry.task.metadata && (
                <div>
                  <span className="text-secondary block font-bold mb-1">Execution Metadata:</span>
                  <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-36 overflow-y-auto">
                    {JSON.stringify(selectedEntry.task.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-[#2d3139] flex justify-between bg-[#181a1f]">
              <button
                onClick={() => {
                  setSelectedEntry(null)
                  setRecoverTarget(selectedEntry)
                }}
                disabled={!can('dlq:recover')}
                className="btn btn-secondary text-xs text-emerald-400 hover:text-emerald-300"
              >
                <RotateCcw size={13} className="inline mr-1" /> Re-queue Task
              </button>
              <button onClick={() => setSelectedEntry(null)} className="btn btn-secondary text-xs">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Recover Confirmation Modal */}
      {recoverTarget && (
        <ConfirmationModal
          isOpen={true}
          title="Recover Poisoned Task from DLQ"
          message={`Are you sure you want to re-queue task ${recoverTarget.task.id}? The retry counter will be reset and the task returned to pending dispatch.`}
          confirmLabel="Recover & Re-queue"
          loading={recovering}
          onConfirm={handleRecover}
          onCancel={() => setRecoverTarget(null)}
        />
      )}
    </div>
  )
}

