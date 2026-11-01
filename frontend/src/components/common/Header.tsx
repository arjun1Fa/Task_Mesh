import React from 'react'
import {
  Activity,
  Layers,
  Radio,
  LogIn,
  LogOut,
  User,
  Shield,
  Laptop,
} from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import type { ConnectionStatus } from '../../websocket/useDashboardSocket'

interface HeaderProps {
  currentInterface: 'orchestrator' | 'worker'
  onSwitchInterface: (ui: 'orchestrator' | 'worker') => void
  clusterStatus: string
  wsStatus: ConnectionStatus
  onOpenLogin: () => void
  activeWorkerId?: string
}

export const Header: React.FC<HeaderProps> = ({
  currentInterface,
  onSwitchInterface,
  clusterStatus,
  wsStatus,
  onOpenLogin,
  activeWorkerId,
}) => {
  const { user, isAuthenticated, logout } = useAuth()

  const isHealthy = clusterStatus === 'healthy' || clusterStatus === 'online'

  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="brand-badge">
            <Layers size={18} />
          </div>
          <div className="brand-text">
            <h1 style={{ fontSize: '0.98rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              TaskMesh
              <span style={{
                fontSize: '0.7rem',
                padding: '2px 6px',
                borderRadius: '4px',
                background: currentInterface === 'orchestrator' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(168, 85, 247, 0.15)',
                color: currentInterface === 'orchestrator' ? 'var(--accent-cyan)' : 'var(--accent-purple)',
                fontWeight: 600,
                border: `1px solid ${currentInterface === 'orchestrator' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(168, 85, 247, 0.3)'}`,
              }}>
                {currentInterface === 'orchestrator' ? 'CONTROL CENTER' : `WORKER CONSOLE ${activeWorkerId ? `(${activeWorkerId})` : ''}`}
              </span>
            </h1>
          </div>
        </div>

        {/* Interface Switcher Button */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => onSwitchInterface(currentInterface === 'orchestrator' ? 'worker' : 'orchestrator')}
          style={{ marginLeft: '1rem', gap: '0.4rem', borderStyle: 'dashed' }}
          title={currentInterface === 'orchestrator' ? 'Open local Worker Agent Console' : 'Return to Orchestrator Control Center'}
        >
          {currentInterface === 'orchestrator' ? (
            <>
              <Laptop size={14} color="var(--accent-purple)" />
              <span>Switch to Worker Console</span>
            </>
          ) : (
            <>
              <Activity size={14} color="var(--accent-cyan)" />
              <span>Switch to Orchestrator</span>
            </>
          )}
        </button>
      </div>

      <div className="top-bar-right">
        {/* Live WebSocket Status Pill */}
        <div
          className={`status-pill ${wsStatus === 'connected' ? 'online' : wsStatus === 'connecting' || wsStatus === 'reconnecting' ? 'degraded' : 'offline'}`}
          title={`Live WebSocket Event Feed: ${wsStatus}`}
        >
          <span className="pulse-dot" />
          <Radio size={12} style={{ marginRight: 2 }} />
          <span>WS: {wsStatus}</span>
        </div>

        {/* Cluster / Node Status Indicator */}
        <div className={`status-pill ${isHealthy ? 'online' : 'degraded'}`}>
          <span className="pulse-dot" />
          <span>{currentInterface === 'orchestrator' ? `Cluster: ${clusterStatus.toUpperCase()}` : `Node: ${clusterStatus.toUpperCase()}`}</span>
        </div>

        {/* User Account / Auth Status */}
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.3rem 0.65rem',
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-main)',
            }}>
              <Shield size={14} color="var(--accent-cyan)" />
              <div style={{ lineHeight: 1.2 }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{user.username}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                  {user.role.replace('_', ' ')}
                </div>
              </div>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={logout}
              title="Sign Out"
              style={{ padding: '0.35rem 0.5rem' }}
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <button className="btn btn-primary btn-sm" onClick={onOpenLogin}>
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  )
}

