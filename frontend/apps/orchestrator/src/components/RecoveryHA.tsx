import React, { useState, useEffect } from 'react'
import {
  ShieldAlert,
  RefreshCw,
  Server,
  Zap,
  CheckCircle,
  AlertTriangle,
  Database,
  ArrowRight,
  Activity,
  Layers
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'

export const RecoveryHA: React.FC = () => {
  const { can } = useAuth()
  const [standbyStatus, setStandbyStatus] = useState<any>(null)
  const [snapshot, setSnapshot] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // Promotion action
  const [promoteModalOpen, setPromoteModalOpen] = useState(false)
  const [promoting, setPromoting] = useState(false)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [statusRes, snapshotRes] = await Promise.all([
        api.getStandbyStatus().catch(() => null),
        api.getStandbySnapshot().catch(() => null),
      ])
      setStandbyStatus(statusRes)
      setSnapshot(snapshotRes)
    } catch (err) {
      console.error('Failed to load HA data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 4000)
    return () => clearInterval(interval)
  }, [])

  const handlePromote = async () => {
    try {
      setPromoting(true)
      await api.promoteStandby()
      setPromoteModalOpen(false)
      await fetchData()
    } catch (err: any) {
      alert(`Promotion failed: ${err.message}`)
    } finally {
      setPromoting(false)
    }
  }

  const isStandby = standbyStatus?.standby_mode ?? false

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <ShieldAlert className="text-amber-400" size={24} />
            High Availability & Standby Replication
          </h1>
          <p className="page-description">
            Primary/Standby cluster redundancy, state snapshot synchronization, and zero-downtime failover controls.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* HA Architecture Status Card */}
      <div className="card mb-6 bg-[#16181e] border-[#2d3139]">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#2d3139]">
          <div className="flex items-center gap-3">
            <Server size={22} className="text-blue-400" />
            <div>
              <div className="text-xs text-secondary uppercase font-semibold">Instance Operational Role</div>
              <div className="text-xl font-bold font-mono text-white flex items-center gap-2">
                {isStandby ? 'STANDBY REPLICA' : 'ACTIVE PRIMARY ORCHESTRATOR'}
                <span
                  className={`text-xs px-2 py-0.5 rounded font-mono ${
                    isStandby
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  }`}
                >
                  {isStandby ? 'PASSIVE SYNC' : 'SERVING TRAFFIC'}
                </span>
              </div>
            </div>
          </div>

          <div>
            {isStandby ? (
              <button
                onClick={() => setPromoteModalOpen(true)}
                disabled={!can('standby:promote')}
                className="btn btn-primary bg-amber-600 hover:bg-amber-500 text-white flex items-center gap-2 text-xs"
              >
                <Zap size={14} /> Promote Standby to Primary
              </button>
            ) : (
              <div className="text-xs font-mono text-emerald-400 flex items-center gap-1.5 bg-emerald-950/40 px-3 py-1.5 rounded border border-emerald-800">
                <CheckCircle size={14} /> Active Master Leader
              </div>
            )}
          </div>
        </div>

        {/* Sync Parameters */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4 text-xs font-mono">
          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">Primary Target URL:</span>
            <span className="text-white font-bold truncate block">
              {standbyStatus?.primary_url || 'Self (Primary)'}
            </span>
          </div>

          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">Snapshot Interval:</span>
            <span className="text-white font-bold">
              {standbyStatus?.snapshot_interval_seconds ?? 5.0}s periodic
            </span>
          </div>

          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">State Replication:</span>
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <CheckCircle size={13} /> Active In-Memory Sync
            </span>
          </div>

          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">Snapshot Node Count:</span>
            <span className="text-blue-400 font-bold">
              {snapshot?.nodes ? Object.keys(snapshot.nodes).length : 'N/A'} registered
            </span>
          </div>
        </div>
      </div>

      {/* Replicated Snapshot Inspection */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <Database className="text-purple-400" size={18} />
            <h2 className="font-semibold text-sm text-white">Latest Cluster State Snapshot</h2>
          </div>
          <span className="text-xs text-secondary font-mono">
            {snapshot?.timestamp ? `Captured ${new Date(snapshot.timestamp).toLocaleTimeString()}` : 'Live'}
          </span>
        </div>

        <div className="bg-[#0f1013] border border-[#2d3139] p-4 rounded-lg font-mono text-xs max-h-96 overflow-y-auto">
          {snapshot ? (
            <pre className="text-gray-300">{JSON.stringify(snapshot, null, 2)}</pre>
          ) : (
            <div className="text-center py-12 text-secondary">
              No snapshot data currently available
            </div>
          )}
        </div>
      </div>

      {/* Promotion Confirmation Modal */}
      <ConfirmationModal
        isOpen={promoteModalOpen}
        title="Promote Standby to Primary Orchestrator?"
        message="This will immediately promote this standby instance to active Primary Orchestrator, enabling the dispatch loop and registering task listeners. Proceed only if the previous primary has failed or is undergoing maintenance."
        confirmLabel="Promote to Primary"
        loading={promoting}
        onConfirm={handlePromote}
        onCancel={() => setPromoteModalOpen(false)}
      />
    </div>
  )
}

