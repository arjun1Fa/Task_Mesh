import React, { useState, useEffect } from 'react'
import {
  ShieldAlert,
  RefreshCw,
  Search,
  Filter,
  Download,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  Lock
} from 'lucide-react'
import { api } from '../api/client'
import type { AuditEvent } from '@shared/types'

export const SecurityAudit: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [actorFilter, setActorFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [resultFilter, setResultFilter] = useState('all')
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null)

  const fetchAuditLogs = async () => {
    try {
      setLoading(true)
      const data = await api.getAuditLogs({
        actor: actorFilter.trim() || undefined,
        action: actionFilter.trim() || undefined,
        result: resultFilter === 'all' ? undefined : resultFilter,
        limit: 150,
      })
      setEvents(data)
    } catch (err) {
      console.error('Failed to load audit logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAuditLogs()
  }, [resultFilter])

  const handleExport = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(events, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `taskmesh_audit_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Lock className="text-red-400" size={24} />
            Security Audit Trail & Compliance
          </h1>
          <p className="page-description">
            Immutable SQLite & in-memory audit logs tracking all administrative actions, configuration changes, and RBAC operations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAuditLogs}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={handleExport}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
          >
            <Download size={14} /> Export JSON
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card mb-4 bg-[#14161b]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1">
              <span className="text-xs text-secondary font-mono mr-1">Result:</span>
              {['all', 'success', 'denied', 'error'].map((res) => (
                <button
                  key={res}
                  onClick={() => setResultFilter(res)}
                  className={`px-2.5 py-1 text-xs font-mono rounded border transition-colors ${
                    resultFilter === res
                      ? 'bg-red-950/60 border-red-700 text-red-300 font-bold'
                      : 'bg-[#181a1f] border-[#2d3139] text-gray-400 hover:border-gray-500'
                  }`}
                >
                  {res.toUpperCase()}
                </button>
              ))}
            </div>

            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-2.5 text-gray-500" />
              <input
                type="text"
                value={actorFilter}
                onChange={(e) => setActorFilter(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchAuditLogs()}
                placeholder="Filter by actor (e.g. admin)..."
                className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded pl-8 pr-3 py-1.5 focus:border-red-500 outline-none w-52 font-mono"
              />
            </div>

            <div className="relative">
              <input
                type="text"
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchAuditLogs()}
                placeholder="Filter action (e.g. node:drain)..."
                className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded px-3 py-1.5 focus:border-red-500 outline-none w-52 font-mono"
              />
            </div>

            <button
              onClick={fetchAuditLogs}
              className="btn btn-secondary text-xs px-3 py-1.5"
            >
              Apply Filter
            </button>
          </div>

          <div className="text-xs text-secondary font-mono">
            Recorded: <span className="text-white font-bold">{events.length}</span> audit events
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Role</th>
                <th>Action</th>
                <th>Target</th>
                <th>Result</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-10 text-secondary">
                    No audit records found matching criteria
                  </td>
                </tr>
              ) : (
                events.map((evt) => (
                  <tr key={evt.id} className="hover:bg-[#1a1d24]">
                    <td className="font-mono text-xs text-secondary whitespace-nowrap">
                      {new Date(evt.timestamp).toLocaleString()}
                    </td>
                    <td className="font-mono text-xs font-bold text-white">
                      {evt.actor}
                    </td>
                    <td>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#181a1f] text-gray-300 border border-[#2d3139]">
                        {evt.role}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-blue-400 font-semibold">
                      {evt.action}
                    </td>
                    <td className="font-mono text-xs text-gray-300">
                      {evt.target}
                    </td>
                    <td>
                      <span
                        className={`text-xs font-mono font-bold px-2 py-0.5 rounded inline-flex items-center gap-1 ${
                          evt.result === 'success'
                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                            : evt.result === 'denied'
                            ? 'bg-amber-950/80 text-amber-300 border border-amber-800'
                            : 'bg-red-950/80 text-red-300 border border-red-800'
                        }`}
                      >
                        {evt.result === 'success' ? (
                          <CheckCircle2 size={11} />
                        ) : (
                          <XCircle size={11} />
                        )}
                        {evt.result.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedEvent(evt)}
                        className="btn btn-secondary px-2 py-1 text-xs"
                      >
                        <Eye size={12} /> View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Event Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="card max-w-2xl w-full bg-[#14161b] border-[#2d3139]">
            <div className="flex justify-between items-center pb-3 border-b border-[#2d3139] mb-3">
              <div>
                <h3 className="font-semibold text-base text-white font-mono">
                  Audit Record: {selectedEvent.id}
                </h3>
                <span className="text-xs text-secondary font-mono">
                  {new Date(selectedEvent.timestamp).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-gray-400 hover:text-white font-mono text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3 bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                <div>
                  <span className="text-secondary block">Actor:</span>
                  <span className="text-white font-bold">{selectedEvent.actor}</span>
                </div>
                <div>
                  <span className="text-secondary block">Role:</span>
                  <span className="text-white font-bold">{selectedEvent.role}</span>
                </div>
                <div>
                  <span className="text-secondary block">Action:</span>
                  <span className="text-blue-400 font-bold">{selectedEvent.action}</span>
                </div>
                <div>
                  <span className="text-secondary block">Target:</span>
                  <span className="text-white font-bold">{selectedEvent.target}</span>
                </div>
              </div>

              <div>
                <span className="text-secondary block font-bold mb-1">Details & Payload:</span>
                <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-56 overflow-y-auto">
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </pre>
              </div>
            </div>

            <div className="p-3 border-t border-[#2d3139] flex justify-end mt-4">
              <button
                onClick={() => setSelectedEvent(null)}
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

