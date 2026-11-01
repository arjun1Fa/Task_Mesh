import React, { useState, useEffect, useRef } from 'react'
import {
  Terminal,
  RefreshCw,
  Search,
  Download,
  AlertTriangle,
  Info
} from 'lucide-react'
import { api } from '../../api/client'
import type { SystemLogEntry } from '../../types'

interface WorkerLogsProps {
  nodeId: string
}

export const WorkerLogsPage: React.FC<WorkerLogsProps> = ({ nodeId }) => {
  const [logs, setLogs] = useState<SystemLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [levelFilter, setLevelFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)

  const logContainerRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const data = await api.getSystemLogs({
        node_id: nodeId,
        level: levelFilter === 'all' ? undefined : levelFilter,
        search: searchQuery.trim() || undefined,
        limit: 150,
      })
      setLogs(data)
    } catch (err) {
      console.error('Failed to load worker logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 4000)
    return () => clearInterval(interval)
  }, [nodeId, levelFilter])

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = 0
    }
  }, [logs, autoScroll])

  const handleDownload = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `${nodeId}_logs_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

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
            <Terminal className="text-cyan-400" size={24} />
            Worker Agent Logs
          </h1>
          <p className="page-description">
            Real-time stdout, dispatch receipts, execution traces, and error logging for this worker instance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchLogs}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={handleDownload}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
          >
            <Download size={13} /> Export
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card mb-4 bg-[#14161b]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-secondary font-mono mr-1">Level:</span>
            {['all', 'DEBUG', 'INFO', 'WARNING', 'ERROR'].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setLevelFilter(lvl)}
                className={`px-2.5 py-1 text-xs font-mono rounded border transition-colors ${
                  levelFilter === lvl
                    ? 'bg-cyan-950/60 border-cyan-700 text-cyan-300 font-bold'
                    : 'bg-[#181a1f] border-[#2d3139] text-gray-400'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-2.5 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchLogs()}
                placeholder="Search log messages..."
                className="bg-[#181a1f] border border-[#2d3139] text-gray-200 text-xs rounded pl-8 pr-3 py-1.5 focus:border-cyan-500 outline-none w-64 font-mono"
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

      {/* Logs View Container */}
      <div className="card bg-[#0b0c0e] border-[#1e2229] p-3 font-mono text-xs">
        <div
          ref={logContainerRef}
          className="h-[520px] overflow-y-auto space-y-1.5 pr-2 select-text"
        >
          {logs.length === 0 ? (
            <div className="text-center py-20 text-secondary">
              No worker log entries available for this node
            </div>
          ) : (
            logs.map((log) => {
              const isError = log.level === 'ERROR'
              const isWarn = log.level === 'WARNING'

              return (
                <div
                  key={log.id}
                  className={`p-2 rounded flex items-start gap-2.5 border ${
                    isError
                      ? 'bg-red-950/20 border-red-900/40 text-red-300'
                      : isWarn
                      ? 'bg-amber-950/20 border-amber-900/40 text-amber-300'
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
                        : 'bg-cyan-950 text-cyan-300'
                    }`}
                  >
                    {log.level}
                  </span>
                  <span className="text-cyan-400 font-semibold select-none text-[11px]">
                    [{nodeId}]
                  </span>
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

