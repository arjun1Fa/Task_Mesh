import React from 'react'
import { Server, Radio, Bell, Settings } from 'lucide-react'
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
  const nodeId = identity?.node_id || overview?.node_id || 'node-local-1'
  const status = overview?.status || identity?.status || 'online'

  return (
    <header className="top-header">
      {/* Brand & Subtitle Pill */}
      <div className="brand-section">
        <div className="brand-icon-box">
          <Server size={18} />
        </div>
        <div className="brand-title">
          <span>TaskMesh</span>
          <span className="header-slash">/</span>
          <span className="header-subtitle-pill worker">Worker Agent Console</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        {/* Node Status Pill */}
        <div className="cluster-online-badge">
          <span className="cluster-online-dot" />
          <span>ONLINE</span>
        </div>

        {/* Bound Local Node ID Tag */}
        <div
          className="mono"
          style={{
            padding: '4px 10px',
            borderRadius: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-main)',
            fontSize: '0.78rem',
            fontWeight: 600,
            color: 'var(--text-primary)',
          }}
        >
          {nodeId}
        </div>

        {/* Header Action Icons */}
        <div className="header-action-icon" title="Notifications">
          <Bell size={15} />
        </div>

        <div className="header-action-icon" title="Settings">
          <Settings size={15} />
        </div>
      </div>
    </header>
  )
}
