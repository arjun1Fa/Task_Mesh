import React, { useState, useEffect, useRef } from 'react'
import {
  Terminal,
  RefreshCw,
  Search,
  Download,
  AlertTriangle,
  Info,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { SystemLogEntry } from '@shared/types'

export const WorkerLogs: React.FC = () => {
  const [logs, setLogs] = useState<SystemLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [levelFilter, setLevelFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)

  const logContainerRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const data = await workerApi.getLogs(150, levelFilter === 'all' ? undefined : levelFilter)
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
  }, [levelFilter])

  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true
    return log.message.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const handleDownload = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `worker_logs_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Terminal size={20} color="var(--accent-purple)" />
            Local Node Agent Logs
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Daemon event stream, heartbeat transmissions, task lease execution, and local process output
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleDownload} title="Download Logs (JSON)">
            <Download size={14} />
            <span>Export</span>
          </button>
          <button className="btn btn-secondary btn-sm" onClick={fetchLogs} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
            <input
              type="text"
              placeholder="Filter logs by keyword or task ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-input"
              style={{ paddingLeft: '2.2rem' }}
            />
          </div>

          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="form-input"
            style={{ width: 'auto' }}
          >
            <option value="all">All Levels</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </div>
      </div>

      {/* Terminal Container */}
      <div
        ref={logContainerRef}
        style={{
          backgroundColor: '#0a0b0e',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.78rem',
          maxHeight: '520px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.35rem',
        }}
      >
        {filteredLogs.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)' }}>
            No log entries found.
          </div>
        ) : (
          filteredLogs.map((log, idx) => {
            const isErr = log.level === 'ERROR'
            const isWarn = log.level === 'WARNING'
            return (
              <div
                key={log.id || idx}
                style={{
                  display: 'flex',
                  gap: '0.75rem',
                  lineHeight: '1.4',
                  color: isErr ? 'var(--status-failed)' : isWarn ? 'var(--status-degraded)' : 'var(--text-color)',
                }}
              >
                <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span
                  style={{
                    fontWeight: 600,
                    width: '60px',
                    flexShrink: 0,
                    color: isErr ? 'var(--status-failed)' : isWarn ? 'var(--status-degraded)' : 'var(--accent-blue)',
                  }}
                >
                  [{log.level}]
                </span>
                <span style={{ flex: 1, wordBreak: 'break-all' }}>{log.message}</span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

