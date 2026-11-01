import React from 'react'
import {
  Layers,
  Radio,
  LogIn,
  LogOut,
  User as UserIcon,
  PlusCircle,
  Activity,
  Server
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import type { ConnectionStatus } from '../websocket/useDashboardSocket'

interface HeaderProps {
  clusterStatus: string
  wsStatus: ConnectionStatus
  onOpenLogin: () => void
  onOpenSubmitTask: () => void
}

export const Header: React.FC<HeaderProps> = ({
  clusterStatus,
  wsStatus,
  onOpenLogin,
  onOpenSubmitTask,
}) => {
  const { user, isAuthenticated, logout, can } = useAuth()
  const isHealthy = clusterStatus === 'healthy' || clusterStatus === 'online'

  return (
    <header className="top-header">
      <div className="brand-section">
        <div style={{
          width: 30,
          height: 30,
          borderRadius: 4,
          backgroundColor: 'var(--accent-blue)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          fontWeight: 800,
        }}>
          <Layers size={17} />
        </div>
        <div className="brand-title">
          TaskMesh
          <span className="brand-tag tag-orchestrator">
            Orchestrator Control Center
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Quick Submit Task Action */}
        {can('tasks:submit') && (
          <button
            onClick={onOpenSubmitTask}
            className="btn btn-primary btn-sm"
          >
            <PlusCircle size={13} />
            <span>Submit Task</span>
          </button>
        )}

        {/* Live WebSocket Status Pill */}
        <div
          className={`badge ${wsStatus === 'connected' ? 'badge-connected' : 'badge-danger'}`}
          title={`WebSocket feed: ${wsStatus}`}
        >
          <span className={`status-dot ${wsStatus === 'connected' ? 'dot-connected' : 'dot-disconnected'}`} />
          <Radio size={11} />
          <span>WS: {wsStatus}</span>
        </div>

        {/* Cluster Status Pill */}
        <div className={`badge ${isHealthy ? 'badge-healthy' : 'badge-warning'}`}>
          <span className={`status-dot ${isHealthy ? 'dot-online' : 'dot-degraded'}`} />
          <span>Cluster: {clusterStatus.toUpperCase()}</span>
        </div>

        {/* User Account State */}
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '0.5rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              backgroundColor: 'var(--bg-surface-elevated)',
              padding: '0.2rem 0.5rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-main)',
            }}>
              <UserIcon size={12} color="var(--accent-blue)" />
              <span className="mono" style={{ fontSize: '0.75rem', fontWeight: 600 }}>{user.username}</span>
              <span style={{
                fontSize: '0.65rem',
                textTransform: 'uppercase',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                padding: '1px 4px',
                borderRadius: 2,
                color: 'var(--text-muted)',
              }}>
                {user.role}
              </span>
            </div>
            <button
              onClick={logout}
              className="btn btn-secondary btn-sm"
              title="Sign Out"
            >
              <LogOut size={12} />
              <span>Logout</span>
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenLogin}
            className="btn btn-secondary btn-sm"
            style={{ marginLeft: '0.5rem' }}
          >
            <LogIn size={12} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  )
}

