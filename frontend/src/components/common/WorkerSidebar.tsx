import React from 'react'
import {
  Laptop,
  Cpu,
  PlayCircle,
  Layers,
  Wifi,
  Terminal,
  Settings,
  Server,
} from 'lucide-react'

export type WorkerPage =
  | 'overview'
  | 'hardware'
  | 'tasks'
  | 'pool'
  | 'network'
  | 'logs'
  | 'settings'

interface WorkerSidebarProps {
  currentPage: WorkerPage
  onSelectPage: (page: WorkerPage) => void
  activeNodeId: string
  availableNodes: string[]
  onSelectNode: (nodeId: string) => void
  activeTaskCount?: number
}

export const WorkerSidebar: React.FC<WorkerSidebarProps> = ({
  currentPage,
  onSelectPage,
  activeNodeId,
  availableNodes,
  onSelectNode,
  activeTaskCount = 0,
}) => {
  const navItems = [
    { id: 'overview', label: '1. Worker Overview', icon: Laptop },
    { id: 'hardware', label: '2. Hardware & Capabilities', icon: Cpu },
    { id: 'tasks', label: '3. Task Execution', icon: PlayCircle, badge: activeTaskCount > 0 ? activeTaskCount : undefined },
    { id: 'pool', label: '4. Execution & Worker Pool', icon: Layers },
    { id: 'network', label: '5. Network & Communication', icon: Wifi },
    { id: 'logs', label: '6. Worker Logs', icon: Terminal },
    { id: 'settings', label: '7. Worker Settings & Ops', icon: Settings },
  ]

  return (
    <aside className="sidebar">
      {/* Node Context Switcher */}
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-main)', backgroundColor: 'rgba(0,0,0,0.15)' }}>
        <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Server size={12} />
          Target Worker Machine
        </div>
        {availableNodes.length > 0 ? (
          <select
            className="form-select mono"
            value={activeNodeId}
            onChange={(e) => onSelectNode(e.target.value)}
            style={{ fontSize: '0.82rem', padding: '0.35rem 0.5rem' }}
          >
            {availableNodes.map((nid) => (
              <option key={nid} value={nid}>
                {nid}
              </option>
            ))}
          </select>
        ) : (
          <div className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {activeNodeId || 'No active worker'}
          </div>
        )}
      </div>

      <div className="sidebar-nav">
        <div className="nav-section-title">Worker Agent Console</div>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = currentPage === item.id
          return (
            <div
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectPage(item.id as WorkerPage)}
            >
              <Icon size={17} style={{ opacity: isActive ? 1 : 0.7 }} />
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.badge !== undefined && (
                <span className="badge badge-blue" style={{ fontSize: '0.68rem', padding: '1px 5px' }}>
                  {item.badge}
                </span>
              )}
            </div>
          )
        })}
      </div>

      <div className="sidebar-footer">
        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textAlign: 'center' }}>
          Node Agent Execution Plane
        </div>
      </div>
    </aside>
  )
}

