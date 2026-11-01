import React, { useState, useEffect } from 'react'
import {
  Settings,
  RefreshCw,
  Save,
  CheckCircle,
  AlertTriangle,
  Sliders,
  ShieldAlert
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'

export const SystemConfig: React.FC = () => {
  const { can } = useAuth()
  const [config, setConfig] = useState<Record<string, any>>({})
  const [editableConfig, setEditableConfig] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const fetchConfig = async () => {
    try {
      setLoading(true)
      const data = await api.getSystemConfig()
      setConfig(data)
      setEditableConfig(data)
    } catch (err) {
      console.error('Failed to load system config:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConfig()
  }, [])

  const handleChange = (key: string, value: any) => {
    setEditableConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setSuccessMsg(null)
      const res = await api.updateSystemConfig(editableConfig)
      setConfig(res)
      setEditableConfig(res)
      setIsEditing(false)
      setShowConfirmModal(false)
      setSuccessMsg('System configuration updated successfully and recorded in audit trail.')
    } catch (err: any) {
      alert(`Failed to update config: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Settings className="text-gray-300" size={24} />
            System Configuration & Runtime Parameters
          </h1>
          <p className="page-description">
            Cluster timeouts, dispatch intervals, retry boundaries, and dynamic orchestrator thresholds.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {can('config:manage') && (
            <>
              {isEditing ? (
                <>
                  <button
                    onClick={() => {
                      setEditableConfig(config)
                      setIsEditing(false)
                    }}
                    className="btn btn-secondary text-xs"
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => setShowConfirmModal(true)}
                    className="btn btn-primary flex items-center gap-1.5 text-xs"
                    disabled={saving}
                  >
                    <Save size={14} /> Save Changes
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setIsEditing(true)}
                  className="btn btn-primary flex items-center gap-1.5 text-xs"
                >
                  <Sliders size={14} /> Edit Configuration
                </button>
              )}
            </>
          )}
          <button
            onClick={fetchConfig}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs p-3 rounded mb-4 flex items-center gap-2">
          <CheckCircle size={15} /> {successMsg}
        </div>
      )}

      {/* Main Parameters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Timing and Heartbeats */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-4 flex items-center gap-2">
            Timing & Node Lifecycle Thresholds
          </h2>

          <div className="space-y-4 text-xs font-mono">
            <div>
              <label className="text-secondary block mb-1">Heartbeat Timeout (seconds):</label>
              <input
                type="number"
                step="0.5"
                disabled={!isEditing}
                value={editableConfig.heartbeat_timeout_seconds ?? 10.0}
                onChange={(e) => handleChange('heartbeat_timeout_seconds', Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Time before a silent node transitions to DEGRADED state.
              </span>
            </div>

            <div>
              <label className="text-secondary block mb-1">Dead Node Timeout (seconds):</label>
              <input
                type="number"
                step="1"
                disabled={!isEditing}
                value={editableConfig.dead_node_timeout_seconds ?? 30.0}
                onChange={(e) => handleChange('dead_node_timeout_seconds', Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Time before a non-responsive node is marked OFFLINE and its active tasks re-queued.
              </span>
            </div>

            <div>
              <label className="text-secondary block mb-1">Dispatch Loop Interval (seconds):</label>
              <input
                type="number"
                step="0.05"
                disabled={!isEditing}
                value={editableConfig.dispatch_loop_interval_seconds ?? 0.1}
                onChange={(e) => handleChange('dispatch_loop_interval_seconds', Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Frequency at which the orchestrator evaluates pending priority tasks for assignment.
              </span>
            </div>
          </div>
        </div>

        {/* Task Reliability and DLQ */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-4 flex items-center gap-2">
            Task Reliability & DLQ Thresholds
          </h2>

          <div className="space-y-4 text-xs font-mono">
            <div>
              <label className="text-secondary block mb-1">Task Lease Timeout (seconds):</label>
              <input
                type="number"
                step="1"
                disabled={!isEditing}
                value={editableConfig.task_lease_timeout_seconds ?? 30.0}
                onChange={(e) => handleChange('task_lease_timeout_seconds', Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Maximum time a node holds a task lease without progress before automatic reclamation.
              </span>
            </div>

            <div>
              <label className="text-secondary block mb-1">Maximum Retry Count:</label>
              <input
                type="number"
                step="1"
                disabled={!isEditing}
                value={editableConfig.max_task_retries ?? 3}
                onChange={(e) => handleChange('max_task_retries', Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Number of retry attempts before a failed task is moved to the Dead Letter Queue.
              </span>
            </div>

            <div>
              <label className="text-secondary block mb-1">Dead Letter Queue Capacity:</label>
              <input
                type="number"
                step="10"
                disabled={!isEditing}
                value={editableConfig.dlq_max_size ?? 1000}
                onChange={(e) => handleChange('dlq_max_size', Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Maximum number of poisoned tasks retained in memory DLQ ring buffer.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={showConfirmModal}
        title="Apply Runtime System Configuration Changes?"
        message="These parameter updates will take immediate effect across the running orchestrator and dispatch workers. An entry will be permanently logged in the audit trail."
        confirmLabel="Apply Changes"
        loading={saving}
        onConfirm={handleSave}
        onCancel={() => setShowConfirmModal(false)}
      />
    </div>
  )
}

