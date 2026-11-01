import React, { useState, useEffect } from 'react'
import {
  Users,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle,
  PlayCircle,
  PauseCircle,
  Wrench,
  AlertCircle
} from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import type { NodeProfile } from '../../types'
import { ConfirmationModal } from '../common/ConfirmationModal'

export const WorkersView: React.FC = () => {
  const { can } = useAuth()
  const [nodes, setNodes] = useState<NodeProfile[]>([])
  const [loading, setLoading] = useState(true)

  // Action state
  const [actionNode, setActionNode] = useState<{ node: NodeProfile; action: 'drain' | 'resume' | 'maintenance' } | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchWorkers = async () => {
    try {
      setLoading(true)
      const data = await api.listNodes()
      setNodes(data)
    } catch (err) {
      console.error('Failed to load workers:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkers()
    const interval = setInterval(fetchWorkers, 4000)
    return () => clearInterval(interval)
  }, [])

  const handleConfirmAction = async () => {
    if (!actionNode) return
    try {
      setActionLoading(true)
      if (actionNode.action === 'drain') {
        await api.drainNode(actionNode.node.id)
      } else if (actionNode.action === 'resume') {
        await api.resumeNode(actionNode.node.id)
      } else if (actionNode.action === 'maintenance') {
        await api.setMaintenance(actionNode.node.id, actionNode.node.status !== 'maintenance')
      }
      setActionNode(null)
      await fetchWorkers()
    } catch (err: any) {
      alert(`Action failed: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  // Calculate cluster totals
  const totalSlots = nodes.reduce((sum, n) => sum + (n.capabilities.worker_capacity || 4), 0)
  const activeSlots = nodes.reduce((sum, n) => sum + (n.telemetry?.active_tasks || 0), 0)
  const availableSlots = Math.max(0, totalSlots - activeSlots)
  const utilization = totalSlots > 0 ? (activeSlots / totalSlots) * 100 : 0

  // Collect all unique handlers
  const allHandlers = Array.from(new Set(nodes.flatMap((n) => n.capabilities.supported_handlers || [])))

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Users className="text-cyan-400" size={24} />
            Cluster Workers & Execution Pool
          </h1>
          <p className="page-description">
            Cluster-wide concurrency limits, active worker threads, slot capacity, and supported capability matrices.
          </p>
        </div>
        <button
          onClick={fetchWorkers}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Aggregate KPI Grid */}
      <div className="kpi-grid mb-6">
        <div className="kpi-card">
          <div className="kpi-label">Total Execution Capacity</div>
          <div className="kpi-value text-white">{totalSlots}</div>
          <div className="kpi-change text-secondary">Concurrent slots across {nodes.length} nodes</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Active Running Slots</div>
          <div className="kpi-value text-blue-400">{activeSlots}</div>
          <div className="kpi-change text-secondary">Currently occupied threads</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Available Free Capacity</div>
          <div className="kpi-value text-emerald-400">{availableSlots}</div>
          <div className="kpi-change text-secondary">Instant dispatch readiness</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Cluster Slot Utilization</div>
          <div className="kpi-value text-purple-400">{utilization.toFixed(1)}%</div>
          <div className="progress-bar mt-2">
            <div className="progress-fill bg-purple-500" style={{ width: `${Math.min(utilization, 100)}%` }} />
          </div>
        </div>
      </div>

      {/* Per Worker Card Grid */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3">
          Participating Worker Nodes
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {nodes.map((node) => {
            const cap = node.capabilities.worker_capacity || 4
            const active = node.telemetry?.active_tasks || 0
            const queued = node.telemetry?.queued_tasks || 0
            const pct = cap > 0 ? (active / cap) * 100 : 0

            return (
              <div key={node.id} className="card bg-[#14161b] flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="font-mono text-sm font-bold text-white flex items-center gap-1.5">
                        {node.id}
                        {node.capabilities.has_gpu && (
                          <span className="text-[10px] bg-purple-950 text-purple-300 px-1.5 py-0.5 rounded border border-purple-800">
                            GPU
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-secondary font-mono">
                        {node.capabilities.hostname || 'Worker'} &bull; {node.capabilities.cpu_cores} Cores
                      </div>
                    </div>
                    <span className={`badge badge-${node.status}`}>{node.status.toUpperCase()}</span>
                  </div>

                  {/* Slot progress */}
                  <div className="bg-[#0f1013] p-3 rounded-lg border border-[#23272f] mb-3">
                    <div className="flex justify-between text-xs font-mono mb-1">
                      <span className="text-secondary">Concurrency Slots:</span>
                      <span className="text-white font-bold">{active} / {cap}</span>
                    </div>
                    <div className="progress-bar mb-2">
                      <div
                        className={`progress-fill ${
                          pct > 80 ? 'bg-red-500' : pct > 50 ? 'bg-amber-500' : 'bg-cyan-500'
                        }`}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[11px] font-mono text-secondary">
                      <span>Queued on node: {queued}</span>
                      <span>Utilization: {pct.toFixed(0)}%</span>
                    </div>
                  </div>

                  {/* Handlers tags */}
                  <div className="mb-3">
                    <span className="text-[11px] text-secondary block mb-1">Handlers:</span>
                    <div className="flex flex-wrap gap-1">
                      {(node.capabilities.supported_handlers || ['benchmark', 'echo']).map((h) => (
                        <span
                          key={h}
                          className="text-[10px] font-mono bg-[#181a1f] text-gray-300 px-2 py-0.5 rounded border border-[#2d3139]"
                        >
                          {h}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Worker Ops Buttons */}
                <div className="pt-3 border-t border-[#23272f] flex justify-between items-center gap-2">
                  <div className="text-[11px] font-mono text-secondary">
                    Completed: <span className="text-white">{node.total_completed}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {node.status === 'draining' ? (
                      <button
                        onClick={() => setActionNode({ node, action: 'resume' })}
                        disabled={!can('node:drain_resume')}
                        className="btn btn-secondary px-2 py-1 text-xs text-green-400"
                        title="Resume Node"
                      >
                        <PlayCircle size={13} />
                      </button>
                    ) : (
                      <button
                        onClick={() => setActionNode({ node, action: 'drain' })}
                        disabled={!can('node:drain_resume')}
                        className="btn btn-secondary px-2 py-1 text-xs text-amber-400"
                        title="Drain Node"
                      >
                        <PauseCircle size={13} />
                      </button>
                    )}
                    <button
                      onClick={() => setActionNode({ node, action: 'maintenance' })}
                      disabled={!can('node:drain_resume')}
                      className={`btn btn-secondary px-2 py-1 text-xs ${
                        node.status === 'maintenance' ? 'text-amber-400' : 'text-gray-400'
                      }`}
                      title="Toggle Maintenance"
                    >
                      <Wrench size={13} />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Cluster Handlers Capability Matrix */}
      <div className="card">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3">
          Cluster Handlers Capability Matrix
        </h2>
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Handler Name</th>
                {nodes.map((n) => (
                  <th key={n.id} className="font-mono text-xs text-center">
                    {n.id}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {allHandlers.map((handler) => (
                <tr key={handler}>
                  <td className="font-mono text-xs font-semibold text-white">{handler}</td>
                  {nodes.map((n) => {
                    const supports = (n.capabilities.supported_handlers || []).includes(handler)
                    return (
                      <td key={n.id} className="text-center">
                        {supports ? (
                          <span className="text-green-400 font-bold">✓</span>
                        ) : (
                          <span className="text-gray-600">-</span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Confirmation Modal */}
      {actionNode && (
        <ConfirmationModal
          isOpen={true}
          title={
            actionNode.action === 'drain'
              ? `Drain Node ${actionNode.node.id}?`
              : actionNode.action === 'resume'
              ? `Resume Node ${actionNode.node.id}?`
              : `Toggle Maintenance for ${actionNode.node.id}?`
          }
          message={
            actionNode.action === 'drain'
              ? 'Draining stops new task assignments while permitting in-flight tasks to complete gracefully.'
              : actionNode.action === 'resume'
              ? 'Resuming returns this node to the active dispatch pool immediately.'
              : 'Maintenance mode sets the node into offline servicing status.'
          }
          confirmLabel={
            actionNode.action === 'drain' ? 'Drain Node' : actionNode.action === 'resume' ? 'Resume' : 'Update'
          }
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionNode(null)}
        />
      )}
    </div>
  )
}

