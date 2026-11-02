import React from 'react'
import {
  LayoutDashboard,
  Server,
  GitBranch,
  ListFilter,
  History,
  Cpu,
  Wifi,
  Terminal,
  AlertOctagon,
  ShieldCheck,
  Users,
  Sliders,
  FileText,
} from 'lucide-react'

export type OrchestratorPage =
  | 'overview'
  | 'nodes'
  | 'live_allocation'
  | 'queue'
  | 'history'
  | 'scheduling'
  | 'network'
  | 'logs'
  | 'dlq'
  | 'recovery'
  | 'users'
  | 'config'
  | 'audit'

interface SidebarProps {
  currentPage: OrchestratorPage
  onSelectPage: (page: OrchestratorPage) => void
  nodeCount?: number
  pendingTasksCount?: number
  dlqCount?: number
}

interface NavItem {
  id: OrchestratorPage
  label: string
  icon: any
  badge?: number
  badgeColor?: string
}

interface NavSection {
  title?: string
  items: NavItem[]
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  nodeCount = 0,
  pendingTasksCount = 0,
  dlqCount = 0,
}) => {
  const sections: NavSection[] = [
    {
      items: [
        { id: 'overview', label: 'Cluster Overview', icon: LayoutDashboard },
        { id: 'nodes', label: 'Cluster Nodes', icon: Server, badge: nodeCount > 0 ? nodeCount : undefined },
        { id: 'live_allocation', label: 'Live Task Allocation', icon: GitBranch },
        { id: 'queue', label: 'Task Queue', icon: ListFilter, badge: pendingTasksCount > 0 ? pendingTasksCount : 4, badgeColor: 'badge-red' },
        { id: 'history', label: 'Task History', icon: History },
      ],
    },
    {
      title: 'Intelligence & Network',
      items: [
        { id: 'scheduling', label: 'Scheduling Intelligence', icon: Cpu },
        { id: 'network', label: 'Network & Inference', icon: Wifi },
      ],
    },
    {
      title: 'Observability & Faults',
      items: [
        { id: 'logs', label: 'Logs & Events', icon: Terminal },
        { id: 'dlq', label: 'Dead Letter Queue', icon: AlertOctagon, badge: dlqCount > 0 ? dlqCount : undefined, badgeColor: 'badge-danger' },
        { id: 'recovery', label: 'Recovery & Failover', icon: ShieldCheck },
      ],
    },
    {
      title: 'Administration',
      items: [
        { id: 'users', label: 'Users & Permissions', icon: Users },
        { id: 'config', label: 'System Configuration', icon: Sliders },
        { id: 'audit', label: 'Security & Audit', icon: FileText },
      ],
    },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-nav">
        {sections.map((section, idx) => (
          <div key={idx} style={{ marginBottom: '1rem' }}>
            {section.title && <div className="nav-section-title">{section.title}</div>}
            {section.items.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              return (
                <div
                  key={item.id}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectPage(item.id)}
                >
                  <Icon size={16} className="nav-icon" />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {item.badge !== undefined && (
                    <span
                      style={{
                        padding: '1px 6px',
                        borderRadius: '9999px',
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        backgroundColor: item.badgeColor === 'badge-red' ? '#ff334b' : 'rgba(255, 255, 255, 0.1)',
                        color: '#ffffff',
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ width: 14, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-red)' }}>
            <Layers size={14} />
          </div>
          <span>TaskMesh</span>
        </div>
        <span className="mono" style={{ color: 'var(--text-muted)' }}>v0.2.0</span>
      </div>
    </aside>
  )
}
