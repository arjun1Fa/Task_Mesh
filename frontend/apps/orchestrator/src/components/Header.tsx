import React from 'react'
import {
  Layers,
  Radio,
  LogIn,
  LogOut,
  User as UserIcon,
  Bell,
  Settings,
  Plus
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
      {/* Brand & Subtitle Pill */}
      <div className="brand-section">
        <div className="brand-icon-box">
          <Layers size={18} />
        </div>
        <div className="brand-title">
          <span>TaskMesh</span>
          <span className="header-slash">/</span>
          <span className="header-subtitle-pill">Orchestrator Control Center</span>
        </div>
      </div>

      {/* Right Actions & Status Badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        {/* Cluster Status Pill */}
        <div
          className="cluster-online-badge"
          style={{ cursor: !isAuthenticated ? 'pointer' : 'default' }}
          onClick={!isAuthenticated ? onOpenLogin : undefined}
          title={!isAuthenticated ? 'Sign in to manage cluster' : 'Cluster is online'}
        >
          <span className="cluster-online-dot" />
          <span>{isHealthy ? 'Cluster Online' : clusterStatus.toUpperCase()}</span>
        </div>

        {/* Quick Submit Task Action */}
        {can('tasks:submit') && (
          <button
            onClick={onOpenSubmitTask}
            className="btn btn-primary btn-sm"
          >
            <Plus size={14} />
            <span>Submit Task</span>
          </button>
        )}

        {/* Bell & Settings Icons */}
        <div className="header-action-icon" title="Notifications">
          <Bell size={15} />
        </div>

        <div className="header-action-icon" title="Settings">
          <Settings size={15} />
        </div>

        {/* User Account / Avatar */}
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div className="user-avatar-circle" title={`${user.username} (${user.role})`}>
              {user.username.slice(0, 1).toUpperCase()}
            </div>
            <button
              onClick={logout}
              className="btn btn-secondary btn-sm"
              title="Sign Out"
            >
              <LogOut size={13} />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenLogin}
            className="btn btn-primary btn-sm"
          >
            <LogIn size={13} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  )
}
