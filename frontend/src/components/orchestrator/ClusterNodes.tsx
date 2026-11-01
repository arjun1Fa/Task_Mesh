import React, { useState } from 'react'
import {
  Server,
  Search,
  Filter,
  ArrowUpDown,
  MoreVertical,
  CheckCircle,
  AlertTriangle,
  Play,
  Pause,
  Trash2,
  Cpu,
  Layers,
  Clock,
  Wifi,
  HardDrive,
  X,
  Shield,
  Activity,
} from 'lucide-react'
import type { NodeProfile, Task } from '../../types'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { ConfirmationModal } from '../common/ConfirmationModal'

interface ClusterNodesProps {
  nodes: NodeProfile[]
  onRefresh: () => void
  selectedNodeId?: string | null
  onClearSelectedNode: () => void
  onOpenWorkerConsole: (nodeId: string) => void
}

export const ClusterNodes: React.FC<ClusterNodesProps> = ({
  nodes,
  onRefresh,
  selectedNodeId,
  onClearSelectedNode,
  onOpenWorkerConsole,
}) => {
  const { hasPermission, canManageNode } = useAuth()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [sortField, setSortField] = useState<'id' | 'status' | 'effective_score' | 'cpu' | 'active_tasks'>('effective_score')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  // Detailed drawer state
  const [activeNode, setActiveNode] = useState<NodeProfile | null>(null)
  const [nodeTasks, setNodeTasks] = useState<Task[]>([])
  const [isLoadingNodeTasks, setIsLoadingNodeTasks] = useState(false)

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean
    title: string
    message: string
    affectedComponents?: string[]
    action: () => Promise<void>
    isDangerous?: boolean
  }>({
    isOpen: false,
    title: '',
    message: '',
    action: async () => {},
  })

  // Open detail drawer
  const handleSelectNode = async (node: NodeProfile) => {
    setActiveNode(node)
    setIsLoadingNodeTasks(true)
    try {
      const tasks = await api.getNodeTasks(node.id)
      setNodeTasks(tasks)
    } catch {
      setNodeTasks([])
    } finally {
      setIsLoadingNodeTasks(false)
    }
  }

  // Filter & Sort
  const filteredNodes = nodes.filter((n) => {
    const matchesSearch =
      n.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (n.capabilities.hostname || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (n.capabilities.ip_address || '').toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || n.status === statusFilter
    return matchesSearch && matchesStatus
  })

  filteredNodes.sort((a, b) => {
    let aVal: any = a[sortField as keyof NodeProfile]
    let bVal: any = b[sortField as keyof NodeProfile]
    if (sortField === 'cpu') {
      aVal = a.telemetry?.cpu_percent || 0
      bVal = b.telemetry?.cpu_percent || 0
    }
    if (sortField === 'active_tasks') {
      aVal = a.telemetry?.active_tasks || 0
      bVal = b.telemetry?.active_tasks || 0
    }

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
    return 0
  })

  const toggleSort = (field: any) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  // Action Handlers with Confirmation
  const handleDrain = (node: NodeProfile) => {
    setConfirmModal({
      isOpen: true,
      title: `Drain Node: ${node.id}`,
      message: `Are you sure you want to drain ${node.id}? The node will stop receiving new task allocations from the scheduler while finishing any in-progress tasks.`,
      affectedComponents: ['Scheduler Eligibility Filter', 'Priority Dispatch Queue', `Worker Pool [${node.id}]`],
      action: async () => {
        await api.drainNode(node.id)
        onRefresh()
        if (activeNode?.id === node.id) {
          const updated = await api.getNode(node.id)
          setActiveNode(updated)
        }
      },
    })
  }

  const handleResume = async (node: NodeProfile) => {
    try {
      await api.resumeNode(node.id)
      onRefresh()
      if (activeNode?.id === node.id) {
        const updated = await api.getNode(node.id)
        setActiveNode(updated)
      }
    } catch (e: any) {
      alert(`Resume failed: ${e.message}`)
    }
  }

  const handleMaintenance = (node: NodeProfile, isMaint: boolean) => {
    setConfirmModal({
      isOpen: true,
      title: `${isMaint ? 'Enter' : 'Exit'} Maintenance Mode: ${node.id}`,
      message: isMaint
        ? `Placing ${node.id} in maintenance will temporarily isolate it from cluster scheduling.`
        : `Restoring ${node.id} from maintenance will re-enable scheduling eligibility.`,
      affectedComponents: ['Scheduler Candidate Pool', 'Heartbeat Health Monitor'],
      action: async () => {
        await api.setMaintenance(node.id, isMaint)
        onRefresh()
        if (activeNode?.id === node.id) {
          const updated = await api.getNode(node.id)
          setActiveNode(updated)
        }
      },
    })
  }

  const handleRemove = (node: NodeProfile) => {
    const activeTasks = node.telemetry?.active_tasks || 0
    setConfirmModal({
      isOpen: true,
      title: `Remove Node Registration: ${node.id}`,
      message: `Are you sure you want to remove node ${node.id} from the cluster registry? ${activeTasks > 0 ? `WARNING: This node has ${activeTasks} active task(s). Removing it will forcibly terminate or re-queue them.` : ''}`,
      affectedComponents: ['Node Registry', 'WebSocket Connection Hub', 'Task Lease Store'],
      isDangerous: true,
      action: async () => {
        await api.deleteNode(node.id, activeTasks > 0)
        onRefresh()
        setActiveNode(null)
      },
    })
  }

  return (
    <div>
      {/* Header and Filter Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Cluster & Node Management</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Observe and control all distributed computers connected to the TaskMesh mesh
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-dim)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '2rem', width: '220px' }}
              placeholder="Search nodes, IP, host..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select
            className="form-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: '140px' }}
          >
            <option value="all">All Statuses</option>
            <option value="online">Online</option>
            <option value="degraded">Degraded</option>
            <option value="draining">Draining</option>
            <option value="maintenance">Maintenance</option>
            <option value="offline">Offline</option>
          </select>
        </div>
      </div>

      {/* Node Table */}
      <div className="panel">
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => toggleSort('id')} style={{ cursor: 'pointer' }}>
                  Node ID <ArrowUpDown size={12} style={{ verticalAlign: 'middle' }} />
                </th>
                <th>Hostname / IP</th>
                <th onClick={() => toggleSort('status')} style={{ cursor: 'pointer' }}>
                  Status <ArrowUpDown size={12} style={{ verticalAlign: 'middle' }} />
                </th>
                <th onClick={() => toggleSort('cpu')} style={{ cursor: 'pointer' }}>
                  CPU Load <ArrowUpDown size={12} style={{ verticalAlign: 'middle' }} />
                </th>
                <th>RAM</th>
                <th>GPU Accelerator</th>
                <th onClick={() => toggleSort('active_tasks')} style={{ cursor: 'pointer' }}>
                  Active Tasks <ArrowUpDown size={12} style={{ verticalAlign: 'middle' }} />
                </th>
                <th onClick={() => toggleSort('effective_score')} style={{ cursor: 'pointer' }}>
                  Effective Score <ArrowUpDown size={12} style={{ verticalAlign: 'middle' }} />
                </th>
                <th>RTT</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredNodes.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No compute nodes found matching current filters.
                  </td>
                </tr>
              ) : (
                filteredNodes.map((node) => {
                  const cpu = node.telemetry?.cpu_percent || 0
                  const ram = node.telemetry?.ram_percent || 0
                  const activeTasks = node.telemetry?.active_tasks || 0
                  const rtt = node.telemetry?.rtt_ms_ewma || 0

                  return (
                    <tr
                      key={node.id}
                      className={activeNode?.id === node.id ? 'selected' : ''}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleSelectNode(node)}
                    >
                      <td className="mono" style={{ fontWeight: 600 }}>
                        {node.id}
                        {node.capabilities.is_local && (
                          <span className="badge badge-blue" style={{ marginLeft: '6px', fontSize: '0.62rem' }}>LOCAL</span>
                        )}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>
                        <div>{node.capabilities.hostname || 'unknown'}</div>
                        <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                          {node.capabilities.ip_address || '127.0.0.1'}
                        </div>
                      </td>
                      <td>
                        <span className={`status-pill ${node.status}`}>
                          <span className="pulse-dot" />
                          {node.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div className="progress-bar-bg" style={{ width: '60px' }}>
                            <div className="progress-bar-fill" style={{ width: `${cpu}%` }} />
                          </div>
                          <span className="mono" style={{ fontSize: '0.75rem' }}>{cpu}%</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div className="progress-bar-bg" style={{ width: '60px' }}>
                            <div className="progress-bar-fill" style={{ width: `${ram}%`, background: '#A855F7' }} />
                          </div>
                          <span className="mono" style={{ fontSize: '0.75rem' }}>{ram}%</span>
                        </div>
                      </td>
                      <td>
                        {node.capabilities?.has_gpu ? (
                          <span className="badge badge-purple">
                            {node.capabilities.gpu_name || 'Active CUDA'} ({((node.capabilities.gpu_vram_mb || 0) / 1024).toFixed(0)}G)
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>CPU Only</span>
                        )}
                      </td>
                      <td className="mono" style={{ fontWeight: 600, color: activeTasks > 0 ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                        {activeTasks} / {node.capabilities?.worker_capacity || 4}
                      </td>
                      <td>
                        <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>
                          {(node.effective_score ?? 1.0).toFixed(2)}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginLeft: '4px' }}>
                          (Base {(node.base_score ?? 1.0).toFixed(1)} × {(node.performance_multiplier ?? 1.0).toFixed(2)})
                        </span>
                      </td>
                      <td className="mono" style={{ fontSize: '0.75rem' }}>
                        {rtt > 0 ? `${Number(rtt).toFixed(1)} ms` : '< 1 ms'}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', gap: '0.35rem' }}>
                          {canManageNode(node.id) && (
                            <>
                              {node.status === 'draining' ? (
                                <button
                                  className="btn btn-success btn-sm"
                                  onClick={() => handleResume(node)}
                                  title="Resume worker node"
                                >
                                  Resume
                                </button>
                              ) : (
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleDrain(node)}
                                  title="Drain worker node"
                                >
                                  Drain
                                </button>
                              )}

                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => handleMaintenance(node, node.status !== 'maintenance')}
                                title="Toggle maintenance mode"
                              >
                                {node.status === 'maintenance' ? 'Exit Maint' : 'Maint'}
                              </button>

                              <button
                                className="btn btn-danger btn-sm btn-icon"
                                onClick={() => handleRemove(node)}
                                title="Remove node"
                              >
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Node Detail Drawer Modal */}
      {activeNode && (
        <div className="modal-backdrop" onClick={() => setActiveNode(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Server size={20} color="var(--accent-cyan)" />
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    Node Specification: <span className="mono">{activeNode.id}</span>
                  </h3>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '2px' }}>
                    <span className={`status-pill ${activeNode.status}`}>{activeNode.status}</span>
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      IP: {activeNode.capabilities.ip_address || '127.0.0.1'} | OS: {activeNode.capabilities.os} ({activeNode.capabilities.arch})
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => onOpenWorkerConsole(activeNode.id)}
                  title="Open this node in Worker Agent Console"
                >
                  Open Worker Console →
                </button>
                <button className="btn btn-secondary btn-icon" onClick={() => setActiveNode(null)}>
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="modal-body">
              {/* Hardware Profile & Scoring */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                <div style={{ padding: '1rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-main)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.5rem' }}>
                    Hardware Capabilities (Detected)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Logical CPU Cores:</span>
                      <strong className="mono">{activeNode.capabilities.cpu_cores} cores</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>CPU Frequency:</span>
                      <strong className="mono">{activeNode.capabilities.cpu_frequency_mhz} MHz</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Total / Avail RAM:</span>
                      <strong className="mono">
                        {(((activeNode.capabilities?.ram_total_mb || 0)) / 1024).toFixed(1)} GB / {(((activeNode.capabilities?.ram_available_mb || 0)) / 1024).toFixed(1)} GB
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>GPU Accelerator:</span>
                      <strong>{activeNode.capabilities?.has_gpu ? activeNode.capabilities.gpu_name || 'CUDA Enabled' : 'None detected'}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Worker Concurrency:</span>
                      <strong className="mono">{activeNode.capabilities?.worker_capacity || 4} slots</strong>
                    </div>
                  </div>
                </div>

                <div style={{ padding: '1rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-main)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-indigo)', marginBottom: '0.5rem' }}>
                    Scheduler Profile & DRR State
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Base Hardware Score:</span>
                      <strong className="mono">{(activeNode.base_score ?? 1.0).toFixed(3)}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>EWMA Perf Multiplier:</span>
                      <strong className="mono" style={{ color: 'var(--accent-cyan)' }}>
                        {(activeNode.performance_multiplier ?? 1.0).toFixed(3)}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Effective Score:</span>
                      <strong className="mono" style={{ color: 'var(--accent-emerald)', fontSize: '0.95rem' }}>
                        {(activeNode.effective_score ?? 1.0).toFixed(3)}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>DRR Fairness Deficit:</span>
                      <strong className="mono">{Number(activeNode.drr_deficit ?? 0).toFixed(2)}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Total Completed / Failed:</span>
                      <strong className="mono">
                        <span style={{ color: 'var(--accent-emerald)' }}>{activeNode.total_completed}</span> / <span style={{ color: 'var(--accent-rose)' }}>{activeNode.total_failed}</span>
                      </strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Supported Handlers & Tags */}
              <div style={{ marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                  Supported Execution Handlers:
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  {activeNode.capabilities.supported_handlers.map((h) => (
                    <span key={h} className="badge badge-emerald" style={{ textTransform: 'none' }}>
                      {h}
                    </span>
                  ))}
                  {activeNode.capabilities.tags.map((t) => (
                    <span key={t} className="badge badge-neutral" style={{ textTransform: 'none' }}>
                      #{t}
                    </span>
                  ))}
                </div>
              </div>

              {/* Node Tasks History Table */}
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Tasks Executed on this Node</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{nodeTasks.length} recorded</span>
                </div>

                <div className="data-table-wrapper" style={{ maxHeight: '200px' }}>
                  <table className="data-table" style={{ fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        <th>Task ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nodeTasks.length === 0 ? (
                        <tr>
                          <td colSpan={5} style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-dim)' }}>
                            {isLoadingNodeTasks ? 'Loading tasks...' : 'No tasks recorded for this node yet.'}
                          </td>
                        </tr>
                      ) : (
                        nodeTasks.slice(0, 15).map((t) => (
                          <tr key={t.id}>
                            <td className="mono">{t.id.slice(0, 16)}...</td>
                            <td>{t.task_type}</td>
                            <td>
                              <span className={`badge ${t.status === 'completed' ? 'badge-emerald' : t.status === 'running' ? 'badge-blue' : 'badge-rose'}`}>
                                {t.status}
                              </span>
                            </td>
                            <td className="mono">{t.result?.execution_time_seconds ? `${t.result.execution_time_seconds.toFixed(2)}s` : '-'}</td>
                            <td style={{ color: 'var(--text-dim)' }}>{new Date(t.created_at).toLocaleTimeString()}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setActiveNode(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        affectedComponents={confirmModal.affectedComponents}
        isDangerous={confirmModal.isDangerous}
        onConfirm={async () => {
          await confirmModal.action()
          setConfirmModal((prev) => ({ ...prev, isOpen: false }))
        }}
        onCancel={() => setConfirmModal((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  )
}

