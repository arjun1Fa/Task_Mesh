import React from 'react'
import { Server, Activity, Wifi, Radio, Cpu, CheckCircle, AlertTriangle } from 'lucide-react'
import type { WorkerOverview, WorkerIdentity } from '@shared/types'

interface WorkerHeaderProps {
  identity: WorkerIdentity | null
  overview: WorkerOverview | null
  isOnline: boolean
}

export const WorkerHeader: React.FC<WorkerHeaderProps> = ({
  identity,
  overview,
  isOnline,
}) => {
  const nodeId = identity?.node_id || overview?.node_id || 'Connecting...'
  const hostname = identity?.hostname || overview?.hostname || 'localhost'
  const status = overview?.status || identity?.status || 'unknown'
  const isWsConnected = overview?.connection_status === 'connected'

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '0s'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    return `${h}h ${m}m ${s}s`
  }

  return (
    <header className="top-header">
      <div className="brand-section">
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: 4,
            backgroundColor: 'var(--accent-purple)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            fontWeight: 800,
          }}
        >
          <Server size={17} />
        </div>
        <div className="brand-title">
          TaskMesh
          <span className="brand-tag tag-worker">Worker Agent Console</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Bound Local Node Identity - STRICTLY UNSELECTABLE / LOCKED TO THIS HARDWARE */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.35rem 0.65rem',
            backgroundColor: 'rgba(0,0,0,0.3)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
          }}
        >
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
            NODE:
          </span>
          <span className="mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
            {nodeId}
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            ({hostname})
          </span>
        </div>

        {/* Node Operational Status */}
        <span className={`status-pill ${status}`}>{status}</span>

        {/* Orchestrator Uplink Status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.35rem 0.6rem',
            backgroundColor: 'rgba(0,0,0,0.25)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
            fontSize: '0.75rem',
          }}
        >
          <Radio
            size={13}
            color={isWsConnected ? 'var(--status-online)' : 'var(--status-failed)'}
            className={isWsConnected ? '' : 'spin'}
          />
          <span style={{ color: isWsConnected ? 'var(--text-color)' : 'var(--status-failed)' }}>
            {isWsConnected ? 'Uplink Synced' : 'Uplink Reconnecting'}
          </span>
        </div>

        {/* Local Uptime */}
        {overview?.uptime_seconds !== undefined && (
          <div
            className="mono"
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-dim)',
              padding: '0.35rem 0.5rem',
            }}
          >
            Uptime: {formatUptime(overview.uptime_seconds)}
          </div>
        )}
      </div>
    </header>
  )
}

