import React from 'react'
import {
  LayoutDashboard,
  Cpu,
  Layers,
  Sliders,
  Wifi,
  Terminal,
  Settings,
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
  activeTasksCount?: number
  concurrency?: number
}

interface NavItem {
  id: WorkerPage
  label: string
  icon: any
  badge?: string | number
  badgeColor?: string
}

export const WorkerSidebar: React.FC<WorkerSidebarProps> = ({
  currentPage,
  onSelectPage,
  activeTasksCount = 0,
  concurrency = 4,
}) => {
  const navItems: NavItem[] = [
    {
      id: 'overview',
      label: '1. Local Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'hardware',
      label: '2. Hardware Profile',
      icon: Cpu,
    },
    {
      id: 'tasks',
      label: '3. Task Execution',
      icon: Layers,
      badge: activeTasksCount > 0 ? activeTasksCount : undefined,
    },
    {
      id: 'pool',
      label: '4. Concurrency Slots',
      icon: Sliders,
      badge: `${activeTasksCount}/${concurrency}`,
      badgeColor: 'badge-blue',
    },
    {
      id: 'network',
      label: '5. Network & TMCH',
      icon: Wifi,
    },
    {
      id: 'logs',
      label: '6. Node Agent Logs',
      icon: Terminal,
    },
    {
      id: 'settings',
      label: '7. Local Management',
      icon: Settings,
    },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-nav">
        <div className="nav-section-title">Worker Node Operations</div>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = currentPage === item.id
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectPage(item.id)}
            >
              <Icon size={16} className="nav-icon" />
              <span style={{ flex: 1, textAlign: 'left' }}>{item.label}</span>
              {item.badge !== undefined && (
                <span className={`badge ${item.badgeColor || 'badge-blue'}`} style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                  {item.badge}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
        <div>Worker Daemon v0.2.0</div>
        <div style={{ marginTop: '2px', color: 'var(--accent-purple)' }}>Local Architecture</div>
      </div>
    </aside>
  )
}

