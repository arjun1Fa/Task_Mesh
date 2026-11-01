import React, { useState, useEffect } from 'react'
import {
  Settings,
  RefreshCw,
  PlayCircle,
  PauseCircle,
  Wrench,
  Wifi,
  Sliders,
  CheckCircle,
  AlertTriangle,
  RotateCcw
} from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { ConfirmationModal } from '../common/ConfirmationModal'

interface WorkerSettingsProps {
  nodeId: string
}

export const WorkerSettingsPage: React.FC<WorkerSettingsProps> = ({ nodeId }) => {
  const { can, user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [nodeData, setNodeData] = useState<any>(null)

  // Actions
  const [actionType, setActionType] = useState<'drain' | 'resume' | 'maintenance' | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const fetchNode = async () => {
    try {
      setLoading(true)
      const res = await api.getNode(nodeId)
      setNodeData(res)
    } catch (err) {
      console.error('Failed to load node info:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNode()
  }, [nodeId])

  // RBAC scope check: if worker_operator, must match node_scope or be cluster-wide
  const hasNodeAccess =
    user?.role === 'super_admin' ||
    user?.role === 'orchestrator_operator' ||
    (user?.role === 'worker_operator' && (!user.node_scope || user.node_scope === nodeId))

  const handleConfirmAction = async () => {
    if (!actionType) return
    try {
      setActionLoading(true)
      setSuccessMsg(null)
      if (actionType === 'drain') {
        await api.workerDrain(nodeId)
        setSuccessMsg(`Node ${nodeId} is now DRAINING. In-flight tasks will finish gracefully.`)
      } else if (actionType === 'resume') {
        await api.workerResume(nodeId)
        setSuccessMsg(`Node ${nodeId} has resumed and is now accepting task dispatches.`)
      } else if (actionType === 'maintenance') {
        const isMaint = nodeData?.status === 'maintenance'
        await api.workerMaintenance(nodeId, !isMaint)
        setSuccessMsg(`Node ${nodeId} maintenance status set to ${!isMaint}.`)
      }
      setActionType(null)
      await fetchNode()
    } catch (err: any) {
      alert(`Action failed: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const isDraining = nodeData?.status === 'draining'
  const isMaintenance = nodeData?.status === 'maintenance'

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono uppercase tracking-wider text-secondary">
              Worker Agent Console
            </span>
            <span className="text-gray-600">&bull;</span>
            <span className="text-xs font-mono text-cyan-400 font-bold">{nodeId}</span>
          </div>
          <h1 className="page-title flex items-center gap-2">
            <Settings className="text-cyan-400" size={24} />
            Worker Settings & Operations
          </h1>
          <p className="page-description">
            Drain/resume transitions, servicing mode toggles, local concurrency limits, and orchestrator connectivity.
          </p>
        </div>
        <button
          onClick={fetchNode}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {successMsg && (
        <div className="bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs p-3 rounded mb-4 flex items-center gap-2">
          <CheckCircle size={15} /> {successMsg}
        </div>
      )}

      {!hasNodeAccess && (
        <div className="bg-amber-950/60 border border-amber-800 text-amber-300 text-xs p-3 rounded mb-4 flex items-center gap-2">
          <AlertTriangle size={15} /> Your account ({user?.role}) does not have administrative write permissions for node {nodeId}. Controls are view-only.
        </div>
      )}

      {/* Operations Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Drain / Resume Controls */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
            <Sliders size={16} className="text-blue-400" /> Lifecycle & Dispatch Controls
          </h2>
          <p className="text-xs text-secondary mb-4 leading-relaxed">
            Draining allows active jobs to finish cleanly while instructing the orchestrator not to allocate new tasks to this machine.
          </p>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-[#0f1013] rounded border border-[#23272f]">
              <div>
                <span className="text-xs font-bold font-mono text-white block">Drain Dispatch</span>
                <span className="text-[11px] text-gray-500">Current status: {nodeData?.status?.toUpperCase() || 'UNKNOWN'}</span>
              </div>
              {isDraining ? (
                <button
                  onClick={() => setActionType('resume')}
                  disabled={!hasNodeAccess}
                  className="btn btn-secondary text-xs text-green-400 hover:text-green-300 flex items-center gap-1.5"
                >
                  <PlayCircle size={14} /> Resume Node
                </button>
              ) : (
                <button
                  onClick={() => setActionType('drain')}
                  disabled={!hasNodeAccess}
                  className="btn btn-secondary text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1.5"
                >
                  <PauseCircle size={14} /> Drain Node
                </button>
              )}
            </div>

            <div className="flex items-center justify-between p-3 bg-[#0f1013] rounded border border-[#23272f]">
              <div>
                <span className="text-xs font-bold font-mono text-white block">Maintenance Servicing</span>
                <span className="text-[11px] text-gray-500">
                  {isMaintenance ? 'Under active maintenance' : 'Standard operational mode'}
                </span>
              </div>
              <button
                onClick={() => setActionType('maintenance')}
                disabled={!hasNodeAccess}
                className={`btn btn-secondary text-xs flex items-center gap-1.5 ${
                  isMaintenance ? 'text-green-400' : 'text-gray-300'
                }`}
              >
                <Wrench size={14} /> {isMaintenance ? 'Exit Maintenance' : 'Enter Maintenance'}
              </button>
            </div>
          </div>
        </div>

        {/* Local Agent Parameters */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
            <Wifi size={16} className="text-cyan-400" /> Agent Parameters & Reconnection
          </h2>
          <p className="text-xs text-secondary mb-4 leading-relaxed">
            Worker daemon configuration parameters registered during bootstrap.
          </p>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 bg-[#0f1013] rounded border border-[#23272f] space-y-1">
              <div className="flex justify-between">
                <span className="text-secondary">Node ID:</span>
                <span className="text-white font-bold">{nodeId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Max Concurrency:</span>
                <span className="text-cyan-400 font-bold">{nodeData?.capabilities?.worker_capacity || 4} slots</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Heartbeat Rate:</span>
                <span className="text-white">5.0s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Binary Chunk Size:</span>
                <span className="text-pink-400">64 KB (65,536 Bytes)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {actionType && (
        <ConfirmationModal
          isOpen={true}
          title={
            actionType === 'drain'
              ? `Drain Node ${nodeId}?`
              : actionType === 'resume'
              ? `Resume Node ${nodeId}?`
              : `Toggle Maintenance for ${nodeId}?`
          }
          message={
            actionType === 'drain'
              ? 'The orchestrator will stop assigning new tasks to this worker while running tasks finish execution.'
              : actionType === 'resume'
              ? 'This node will immediately return to the active dispatch pool.'
              : 'Maintenance mode pauses all activity on this node for servicing.'
          }
          confirmLabel={actionType === 'drain' ? 'Drain Node' : actionType === 'resume' ? 'Resume Node' : 'Confirm'}
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionType(null)}
        />
      )}
    </div>
  )
}

