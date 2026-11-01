import React, { useState } from 'react'
import {
  Server,
  Search,
  Filter,
  ArrowUpDown,
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
  ExternalLink,
} from 'lucide-react'
import type { NodeProfile, Task } from '@shared/types'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'

interface ClusterNodesProps {
  nodes: NodeProfile[]
  onRefresh: () => void
  selectedNodeId?: string | null
  onClearSelectedNode?: () => void
}

export const ClusterNodes: React.FC<ClusterNodesProps> = ({
  nodes,
  onRefresh,
  selectedNodeId,
  onClearSelectedNode,
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

  // Open drawer if selectedNodeId changes
  React.useEffect(() => {
    if (selectedNodeId) {
      const match = nodes.find((n) => n.id === selectedNodeId)
      if (match) {
        handleOpenNodeDetails(match)
      }
    }
  }, [selectedNodeId, nodes])

  const handleOpenNodeDetails = async (node: NodeProfile) => {
    setActiveNode(node)
    setIsLoadingNodeTasks(true)
    try {
      const tasks = await api.listTasks(undefined, 50)
      setNodeTasks(tasks.filter((t) => t.assigned_node_id === node.id))
    } catch (err) {
      console.error('Failed to load node tasks:', err)
    } finally {
      setIsLoadingNodeTasks(false)
    }
  }

  // Node Actions
  const handleDrainNode = (node: NodeProfile) => {
    setConfirmModal({
      isOpen: true,
      title: `Drain Worker Node: ${node.id}`,
      message: `Are you sure you want to drain ${node.id}? Existing running tasks will complete normally, but no new tasks will be assigned by the scheduler.`,
      affectedComponents: ['Scheduler Dispatcher', 'Task Queue Lease Allocator', node.id],
      isDangerous: true,
      action: async () => {
        await api.drainNode(node.id)
        onRefresh()
        if (activeNode?.id === node.id) {
          setActiveNode((prev) => (prev ? { ...prev, status: 'draining' } : null))
        }
      },
    })
  }

  const handleResumeNode = (node: NodeProfile) => {
    setConfirmModal({
      isOpen: true,
      title: `Resume Worker Node: ${node.id}`,
      message: `Activate ${node.id} back into the active scheduling pool? It will immediately begin bidding on tasks matching its capability profile.`,
      affectedComponents: ['Scheduler Dispatcher', node.id],
      isDangerous: false,
      action: async () => {
        await api.resumeNode(node.id)
        onRefresh()
        if (activeNode?.id === node.id) {
          setActiveNode((prev) => (prev ? { ...prev, status: 'online' } : null))
        }
      },
    })
  }

  const handleMaintenanceMode = (node: NodeProfile) => {
    setConfirmModal({
      isOpen: true,
      title: `Set Maintenance Mode: ${node.id}`,
      message: `Placing ${node.id} in maintenance will temporarily withdraw it from the cluster. Use this for hardware upgrades, driver installs, or diagnostics.`,
      affectedComponents: ['Cluster Membership', 'Heartbeat Watchdog', node.id],
      isDangerous: true,
      action: async () => {
        await api.setNodeMaintenance(node.id)
        onRefresh()
        if (activeNode?.id === node.id) {
          setActiveNode((prev) => (prev ? { ...prev, status: 'maintenance' } : null))
        }
      },
    })
  }

  // Filter & Sort
  const filteredNodes = nodes.filter((node) => {
    const matchesSearch =
      node.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (node.capabilities?.hostname || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (node.capabilities?.os || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (node.capabilities?.gpu_name || '').toLowerCase().includes(searchTerm.toLowerCase())

    const matchesStatus = statusFilter === 'all' || node.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const sortedNodes = [...filteredNodes].sort((a, b) => {
    let comparison = 0
    if (sortField === 'id') {
      comparison = a.id.localeCompare(b.id)
    } else if (sortField === 'status') {
      comparison = a.status.localeCompare(b.status)
    } else if (sortField === 'effective_score') {
      comparison = (a.score_breakdown?.final_score || 0) - (b.score_breakdown?.final_score || 0)
    } else if (sortField === 'cpu') {
      comparison = (a.telemetry?.cpu_percent || 0) - (b.telemetry?.cpu_percent || 0)
    } else if (sortField === 'active_tasks') {
      comparison = (a.telemetry?.active_tasks || 0) - (b.telemetry?.active_tasks || 0)
    }
    return sortDirection === 'desc' ? -comparison : comparison
  })

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  return (
    <div>
      {/* Search & Filter Toolbar */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <input
                type="text"
                className="form-input"
                placeholder="Search by Node ID, hostname, OS, GPU model..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '2.2rem' }}
              />
              <Search
                size={16}
                color="var(--text-dim)"
                style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }}
              />
            </div>

            <select
              className="form-input"
              style={{ width: 'auto' }}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses ({nodes.length})</option>
              <option value="online">Online ({nodes.filter((n) => n.status === 'online').length})</option>
              <option value="degraded">Degraded ({nodes.filter((n) => n.status === 'degraded').length})</option>
              <option value="draining">Draining ({nodes.filter((n) => n.status === 'draining').length})</option>
              <option value="maintenance">Maintenance ({nodes.filter((n) => n.status === 'maintenance').length})</option>
              <option value="offline">Offline ({nodes.filter((n) => n.status === 'offline').length})</option>
            </select>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Sort by:</span>
            <button
              className={`btn btn-secondary btn-sm ${sortField === 'effective_score' ? 'btn-active' : ''}`}
              onClick={() => toggleSort('effective_score')}
            >
              Score {sortField === 'effective_score' && (sortDirection === 'desc' ? '↓' : '↑')}
            </button>
            <button
              className={`btn btn-secondary btn-sm ${sortField === 'cpu' ? 'btn-active' : ''}`}
              onClick={() => toggleSort('cpu')}
            >
              CPU {sortField === 'cpu' && (sortDirection === 'desc' ? '↓' : '↑')}
            </button>
            <button
              className={`btn btn-secondary btn-sm ${sortField === 'active_tasks' ? 'btn-active' : ''}`}
              onClick={() => toggleSort('active_tasks')}
            >
              Load {sortField === 'active_tasks' && (sortDirection === 'desc' ? '↓' : '↑')}
            </button>
          </div>
        </div>
      </div>

      {/* Nodes Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="card-title">Registered Cluster Nodes</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginLeft: '0.75rem' }}>
              Showing {sortedNodes.length} of {nodes.length} nodes
            </span>
          </div>
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => toggleSort('id')} style={{ cursor: 'pointer' }}>
                  Node Identity
                </th>
                <th onClick={() => toggleSort('status')} style={{ cursor: 'pointer' }}>
                  Status
                </th>
                <th>Hardware / OS</th>
                <th>GPU Accelerator</th>
                <th onClick={() => toggleSort('cpu')} style={{ cursor: 'pointer' }}>
                  Telemetry (CPU/RAM)
                </th>
                <th onClick={() => toggleSort('active_tasks')} style={{ cursor: 'pointer' }}>
                  Active Tasks
                </th>
                <th onClick={() => toggleSort('effective_score')} style={{ cursor: 'pointer' }}>
                  Sched Score
                </th>
                <th>Network RTT</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedNodes.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No cluster nodes match the specified filters.
                  </td>
                </tr>
              ) : (
                sortedNodes.map((node) => {
                  const cpuVal = Number(node.telemetry?.cpu_percent ?? 0)
                  const ramVal = Number(node.telemetry?.ram_percent ?? 0)
                  const rttVal = Number(node.telemetry?.rtt_ms_ewma ?? 0)
                  const scoreVal = Number(node.score_breakdown?.final_score ?? 0)

                  return (
                    <tr
                      key={node.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleOpenNodeDetails(node)}
                    >
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <Server size={18} color="var(--accent-blue)" />
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>
                              {node.id}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }} className="mono">
                              {node.capabilities?.hostname || 'Unknown host'} • {node.capabilities?.ip_address || '127.0.0.1'}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td>
                        <span className={`status-pill ${node.status}`}>
                          {node.status}
                        </span>
                      </td>

                      <td>
                        <div style={{ fontSize: '0.8rem' }}>
                          {node.capabilities?.cpu_cores || 0} Cores • {Math.round((node.capabilities?.ram_total_mb || 0) / 1024)}GB RAM
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                          {node.capabilities?.os} ({node.capabilities?.arch})
                        </div>
                      </td>

                      <td>
                        {node.capabilities?.has_gpu ? (
                          <div style={{ fontSize: '0.8rem', color: 'var(--accent-green)' }}>
                            <Cpu size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                            {node.capabilities.gpu_name || 'Generic GPU'}
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                              {Math.round((node.capabilities.gpu_vram_mb || 0) / 1024)}GB VRAM
                            </div>
                          </div>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>None (CPU only)</span>
                        )}
                      </td>

                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', width: '110px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                            <span>CPU</span>
                            <span className="mono">{cpuVal.toFixed(0)}%</span>
                          </div>
                          <div className="progress-bar-container" style={{ height: '4px' }}>
                            <div
                              className="progress-bar-fill"
                              style={{
                                width: `${Math.min(100, Math.max(0, cpuVal))}%`,
                                backgroundColor: cpuVal > 85 ? 'var(--status-failed)' : 'var(--accent-blue)',
                              }}
                            />
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginTop: '2px' }}>
                            <span>RAM</span>
                            <span className="mono">{ramVal.toFixed(0)}%</span>
                          </div>
                          <div className="progress-bar-container" style={{ height: '4px' }}>
                            <div
                              className="progress-bar-fill"
                              style={{
                                width: `${Math.min(100, Math.max(0, ramVal))}%`,
                                backgroundColor: ramVal > 85 ? 'var(--status-degraded)' : 'var(--accent-cyan)',
                              }}
                            />
                          </div>
                        </div>
                      </td>

                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="badge badge-blue">
                            {node.telemetry?.active_tasks || 0} active
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                            / {node.capabilities?.worker_capacity || 4} slots
                          </span>
                        </div>
                      </td>

                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className="mono" style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                            {scoreVal.toFixed(2)}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                            (bids: {node.score_breakdown?.bid_score?.toFixed(1) ?? 'N/A'})
                          </span>
                        </div>
                      </td>

                      <td>
                        <div style={{ fontSize: '0.8rem' }} className="mono">
                          {rttVal > 0 ? `${rttVal.toFixed(1)} ms` : 'Local (<0.5ms)'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                          {node.telemetry?.upload_mbps_ewma ? `${node.telemetry.upload_mbps_ewma.toFixed(1)} Mbps` : 'High Speed'}
                        </div>
                      </td>

                      <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                          {node.status === 'online' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              title="Drain node (stop accepting new tasks)"
                              onClick={() => handleDrainNode(node)}
                              disabled={!canManageNode(node.id)}
                            >
                              <Pause size={13} style={{ marginRight: '3px' }} /> Drain
                            </button>
                          )}

                          {(node.status === 'draining' || node.status === 'maintenance') && (
                            <button
                              className="btn btn-primary btn-sm"
                              title="Resume task scheduling on this node"
                              onClick={() => handleResumeNode(node)}
                              disabled={!canManageNode(node.id)}
                            >
                              <Play size={13} style={{ marginRight: '3px' }} /> Resume
                            </button>
                          )}

                          {node.status !== 'maintenance' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              title="Set node to maintenance mode"
                              onClick={() => handleMaintenanceMode(node)}
                              disabled={!canManageNode(node.id)}
                            >
                              Maint
                            </button>
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

      {/* Node Drilldown Drawer / Modal */}
      {activeNode && (
        <div className="modal-backdrop" onClick={() => { setActiveNode(null); onClearSelectedNode?.() }}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: '850px', maxHeight: '90vh', overflowY: 'auto' }}
          >
            <div className="modal-header" style={{ alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(59, 130, 246, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Server size={20} color="var(--accent-blue)" />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>
                    {activeNode.id}
                  </h3>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '2px', alignItems: 'center' }}>
                    <span className={`status-pill ${activeNode.status}`}>{activeNode.status}</span>
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      IP: {activeNode.capabilities?.ip_address || '127.0.0.1'} | OS: {activeNode.capabilities?.os} ({activeNode.capabilities?.arch})
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <a
                  href={`http://${activeNode.capabilities?.ip_address || '127.0.0.1'}:8081`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary btn-sm"
                  title="Open node's local web console in a new browser window"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <ExternalLink size={13} /> Local Console (8081)
                </a>
                <button
                  className="btn btn-secondary btn-icon"
                  onClick={() => { setActiveNode(null); onClearSelectedNode?.() }}
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Hardware Profile & Scoring */}
              <div className="grid grid-2" style={{ gap: '1rem' }}>
                <div className="card" style={{ margin: 0 }}>
                  <div className="card-title" style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                    Hardware Capabilities
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>CPU Specification:</span>
                      <span className="mono">{activeNode.capabilities?.cpu_cores} Cores @ {activeNode.capabilities?.cpu_frequency_mhz} MHz</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>RAM Capacity:</span>
                      <span className="mono">{Math.round((activeNode.capabilities?.ram_total_mb || 0) / 1024)} GB Total</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>GPU Model:</span>
                      <span className="mono">{activeNode.capabilities?.has_gpu ? activeNode.capabilities.gpu_name : 'No dedicated GPU'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>VRAM Capacity:</span>
                      <span className="mono">{activeNode.capabilities?.has_gpu ? `${activeNode.capabilities.gpu_vram_mb} MB` : 'N/A'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Concurrency Cap:</span>
                      <span className="mono">{activeNode.capabilities?.worker_capacity} concurrent tasks</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Supported Handlers:</span>
                      <span className="mono">{activeNode.capabilities?.supported_handlers?.join(', ') || 'benchmark, echo'}</span>
                    </div>
                  </div>
                </div>

                <div className="card" style={{ margin: 0 }}>
                  <div className="card-title" style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                    Multi-Factor Sched Scoring Breakdown
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Composite Score:</span>
                      <span className="mono" style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                        {Number(activeNode.score_breakdown?.final_score ?? 0).toFixed(3)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Contract Net Bid Score:</span>
                      <span className="mono">{Number(activeNode.score_breakdown?.bid_score ?? 0).toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>MWU Weight Multiplier:</span>
                      <span className="mono">{Number(activeNode.score_breakdown?.mwu_weight ?? 1.0).toFixed(3)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>DRR Deficit Allocation:</span>
                      <span className="mono">{Number(activeNode.score_breakdown?.drr_deficit ?? 0).toFixed(0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Q-Value Reward EWMA:</span>
                      <span className="mono">{Number(activeNode.score_breakdown?.q_value ?? 0).toFixed(3)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>RTT Latency EWMA:</span>
                      <span className="mono">{Number(activeNode.telemetry?.rtt_ms_ewma ?? 0).toFixed(1)} ms</span>
                    </div>
                  </div>
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
                            <td className="mono">{t.result?.execution_time_seconds ? `${Number(t.result.execution_time_seconds).toFixed(2)}s` : '-'}</td>
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
              <button
                className="btn btn-secondary"
                onClick={() => { setActiveNode(null); onClearSelectedNode?.() }}
              >
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

