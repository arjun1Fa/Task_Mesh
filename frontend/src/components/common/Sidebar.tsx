import React from 'react'
import {
  LayoutDashboard,
  Server,
  Activity,
  ListTodo,
  Cpu,
  Wifi,
  HardDrive,
  Terminal,
  AlertOctagon,
  ShieldCheck,
  Users,
  Sliders,
  FileText,
  HeartPulse,
} from 'lucide-react'

export type OrchestratorPage =
  | 'overview'
  | 'nodes'
  | 'live_monitor'
  | 'tasks'
  | 'scheduling'
  | 'network'
  | 'workers'
  | 'logs'
  | 'dlq'
  | 'recovery'
  | 'users'
  | 'config'
  | 'audit'
  | 'health'

interface SidebarProps {
  currentPage: OrchestratorPage
  onSelectPage: (page: OrchestratorPage) => void
  taskQueueCount?: number
  dlqCount?: number
  nodeCount?: number
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  taskQueueCount = 0,
  dlqCount = 0,
  nodeCount = 0,
}) => {
  interface NavItem {
    id: string
    label: string
    icon: any
    badge?: number
    badgeColor?: string
  }

  interface NavSection {
    title: string
    items: NavItem[]
  }

  const navSections: NavSection[] = [
    {
      title: 'Core Operations',
      items: [
        { id: 'overview', label: 'Global Overview', icon: LayoutDashboard },
        { id: 'nodes', label: 'Cluster & Nodes', icon: Server, badge: nodeCount > 0 ? nodeCount : undefined },
        { id: 'live_monitor', label: 'Live Task Monitor', icon: Activity },
        { id: 'tasks', label: 'Task Queue', icon: ListTodo, badge: taskQueueCount > 0 ? taskQueueCount : undefined },
      ],
    },
    {
      title: 'Intelligence & Network',
      items: [
        { id: 'scheduling', label: 'Scheduling Engine', icon: Cpu },
        { id: 'network', label: 'Network & Inference', icon: Wifi },
        { id: 'workers', label: 'Workers Pool', icon: HardDrive },
      ],
    },
    {
      title: 'Observability & Faults',
      items: [
        { id: 'logs', label: 'Logs & Events', icon: Terminal },
        { id: 'dlq', label: 'Dead Letter Queue', icon: AlertOctagon, badge: dlqCount > 0 ? dlqCount : undefined, badgeColor: 'badge-rose' },
        { id: 'recovery', label: 'Recovery & HA', icon: ShieldCheck },
        { id: 'health', label: 'System Health', icon: HeartPulse },
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
        {navSections.map((section, idx) => (
          <div key={idx} style={{ marginBottom: '0.75rem' }}>
            <div className="nav-section-title">{section.title}</div>
            {section.items.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              return (
                <div
                  key={item.id}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectPage(item.id as OrchestratorPage)}
                >
                  <Icon size={17} style={{ opacity: isActive ? 1 : 0.7 }} />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {item.badge !== undefined && (
                    <span className={`badge ${item.badgeColor || 'badge-neutral'}`} style={{ fontSize: '0.68rem', padding: '1px 5px' }}>
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>TaskMesh Orchestrator</span>
          <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>v0.2.0</span>
        </div>
      </div>
    </aside>
  )
}
