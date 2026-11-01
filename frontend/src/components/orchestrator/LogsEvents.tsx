import React, { useState, useEffect, useRef } from 'react'
import {
  Terminal,
  RefreshCw,
  Search,
  Filter,
  Download,
  Trash2,
  Pause,
  Play,
  ArrowDown,
  AlertTriangle,
  Info,
  Bug,
  AlertOctagon
} from 'lucide-react'
import { api } from '../../api/client'
import { useDashboardSocket } from '../../websocket/useDashboardSocket'
import type { SystemLogEntry } from '../../types'

export const LogsEvents: React.FC = () => {
  const [logs, setLogs] = useState<SystemLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [levelFilter, setLevelFilter] = useState<string>('all')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [autoScroll, setAutoScroll] = useState<boolean>(true)
  const [isPaused, setIsPaused] = useState<boolean>(false)

  const logContainerRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const data = await api.getSystemLogs({
        level: levelFilter === 'all' ? undefined : levelFilter,
        source: sourceFilter === 'all' ? undefined : sourceFilter,
        search: searchQuery.trim() || undefined,
        limit: 200,
      })
      setLogs(data)
    } catch (err) {
      console.error('Failed to fetch system logs:', err)
    } finally {
      setLoading(false)
    }
  }

  // Listen to WebSocket events and append as log entries if not paused
  useDashboardSocket({
    onEvent: (event) => {
      if (isPaused) return
      const newEntry: SystemLogEntry = {
        id: event.event_id,
        timestamp: event.timestamp,
        level: event.event_type.includes('fail') ? 'ERROR' : event.event_type.includes('warn') ? 'WARNING' : 'INFO',
        source: event.source || 'orchestrator',
        message: `[${event.event_type}] entity=${event.entity_id} - ${JSON.stringify(event.data)}`,
        task_id: event.data?.task_id || (event.entity_id?.startsWith('task') ? event.entity_id : undefined),
        node_id: event.data?.node_id || (event.entity_id?.startsWith('node') ? event.entity_id : undefined),
      }

      setLogs((prev) => [newEntry, ...prev.slice(0, 300)])
    },
  })

  useEffect(() => {
    fetchLogs()
  }, [levelFilter, sourceFilter])

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = 0
    }
  }, [logs, autoScroll])

  const handleExport = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `taskmesh_logs_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  const filteredLogs = logs.filter((log) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchMsg = log.message.toLowerCase().includes(q)
      const matchSrc = log.source.toLowerCase().includes(q)
      const matchTask = log.task_id?.toLowerCase().includes(q)
      const matchNode = log.node_id?.toLowerCase().includes(q)
      if (!matchMsg && !matchSrc && !matchTask && !matchNode) return false
    }
    return true
  })

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Terminal className="text-gray-300" size={24} />
            Unified Logs & Real-Time Event Stream
          </h1>
          <p className="page-description">
            Live cluster diagnostic logs, dispatch lifecycle events, scheduler traces, and node communications.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`btn text-xs flex items-center gap-1.5 ${
              isPaused ? 'btn-danger' : 'btn-secondary'
            }`}
          >
            {isPaused ? <Play size={13} /> : <Pause size={13} />}
            {isPaused ? 'Resume Stream' : 'Pause Stream'}
          </button>
          <button
            onClick={fetchLogs}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={handleExport}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            title="Export JSON"
          >
            <Download size={13} />
            Export
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card mb-4 bg-[#14161b]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            {/* Level filters */}
            <div className="flex items-center gap-1">
              <span className="text-xs text-secondary font-mono mr-1">Level:</span>
              {['all', 'DEBUG', 'INFO', 'WARNING', 'ERROR'].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setLevelFilter(lvl)}
                  className={`px-2.5 py-1 text-xs font-mono rounded border transition-colors ${
                    levelFilter === lvl
                      ? 'bg-blue-600/30 border-blue-500 text-blue-300 font-bold'
                      : 'bg-[#181a1f] border-[#2d3139] text-gray-400 hover:border-gray-500'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>

            {/* Source dropdown */}
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="bg-[#181a1f] border border-[#2d3139] text-gray-300 text-xs rounded px-2.5 py-1 focus:border-blue-500 outline-none"
            >
              <option value="all">All Sources</option>
              <option value="orchestrator">orchestrator</option>
              <option value="scheduler">scheduler</option>
              <option value="dispatcher">dispatcher</option>
              <option value="node">node</option>
              <option value="auth">auth</option>
              <option value="audit">audit</option>
            </select>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-2.5 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter logs or task ID..."
                className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded pl-8 pr-3 py-1.5 focus:border-blue-500 outline-none w-64 font-mono"
              />
            </div>
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`px-2.5 py-1 text-xs font-mono rounded border ${
                autoScroll
                  ? 'bg-emerald-950/60 border-emerald-700 text-emerald-300'
                  : 'bg-[#181a1f] border-[#2d3139] text-gray-400'
              }`}
            >
              Auto-Scroll: {autoScroll ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>
      </div>

      {/* Log Console Container */}
      <div className="card bg-[#0b0c0e] border-[#1e2229] p-3 font-mono text-xs">
        <div
          ref={logContainerRef}
          className="h-[550px] overflow-y-auto space-y-1.5 pr-2 select-text"
        >
          {filteredLogs.length === 0 ? (
            <div className="text-center py-20 text-secondary">
              No log entries match the current filter criteria
            </div>
          ) : (
            filteredLogs.map((log) => {
              const isError = log.level === 'ERROR'
              const isWarn = log.level === 'WARNING'
              const isDebug = log.level === 'DEBUG'

              return (
                <div
                  key={log.id}
                  className={`p-2 rounded flex items-start gap-2.5 border ${
                    isError
                      ? 'bg-red-950/20 border-red-900/40 text-red-300'
                      : isWarn
                      ? 'bg-amber-950/20 border-amber-900/40 text-amber-300'
                      : isDebug
                      ? 'bg-gray-900/40 border-gray-800 text-gray-400'
                      : 'bg-[#121418] border-[#1e2229] text-gray-200'
                  }`}
                >
                  <span className="text-secondary select-none text-[11px] whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleTimeString()}.
                    {new Date(log.timestamp).getMilliseconds().toString().padStart(3, '0')}
                  </span>

                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-bold select-none ${
                      isError
                        ? 'bg-red-900 text-red-200'
                        : isWarn
                        ? 'bg-amber-900 text-amber-200'
                        : isDebug
                        ? 'bg-gray-800 text-gray-300'
                        : 'bg-blue-900/60 text-blue-300'
                    }`}
                  >
                    {log.level}
                  </span>

                  <span className="text-purple-400 font-semibold select-none text-[11px]">
                    [{log.source}]
                  </span>

                  {log.task_id && (
                    <span className="text-blue-400 text-[11px] font-semibold">
                      task={log.task_id.slice(0, 8)}
                    </span>
                  )}

                  {log.node_id && (
                    <span className="text-green-400 text-[11px] font-semibold">
                      node={log.node_id}
                    </span>
                  )}

                  <span className="flex-1 break-all whitespace-pre-wrap">{log.message}</span>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

