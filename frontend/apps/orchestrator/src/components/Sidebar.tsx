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
  title: string
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
      title: 'Cluster Operations',
      items: [
        { id: 'overview', label: '1. Global Overview', icon: LayoutDashboard },
        { id: 'nodes', label: '2. Cluster Nodes', icon: Server, badge: nodeCount > 0 ? nodeCount : undefined },
        { id: 'live_allocation', label: '3. Live Task Allocation', icon: GitBranch },
        { id: 'queue', label: '4. Task Queue', icon: ListFilter, badge: pendingTasksCount > 0 ? pendingTasksCount : undefined },
        { id: 'history', label: '5. Task History', icon: History },
      ],
    },
    {
      title: 'Intelligence & Network',
      items: [
        { id: 'scheduling', label: '6. Scheduling Intelligence', icon: Cpu },
        { id: 'network', label: '7. Network & Inference', icon: Wifi },
      ],
    },
    {
      title: 'Observability & Faults',
      items: [
        { id: 'logs', label: '8. Logs & Events', icon: Terminal },
        { id: 'dlq', label: '9. Dead Letter Queue', icon: AlertOctagon, badge: dlqCount > 0 ? dlqCount : undefined, badgeColor: 'badge-danger' },
        { id: 'recovery', label: '10. Recovery & Failover', icon: ShieldCheck },
      ],
    },
    {
      title: 'Administration',
      items: [
        { id: 'users', label: '11. Users & Permissions', icon: Users },
        { id: 'config', label: '12. System Configuration', icon: Sliders },
        { id: 'audit', label: '13. Security & Audit', icon: FileText },
      ],
    },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-nav">
        {sections.map((section, idx) => (
          <div key={idx} style={{ marginBottom: '0.85rem' }}>
            <div className="nav-section-title">{section.title}</div>
            {section.items.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              return (
                <div
                  key={item.id}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectPage(item.id)}
                >
                  <Icon size={16} style={{ opacity: isActive ? 1 : 0.7 }} />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {item.badge !== undefined && (
                    <span className={`badge ${item.badgeColor || 'badge-neutral'}`} style={{ fontSize: '0.65rem', padding: '1px 5px' }}>
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
          <span>TaskMesh Orchestrator</span>
          <span className="mono">v0.2.0</span>
        </div>
      </div>
    </aside>
  )
}
