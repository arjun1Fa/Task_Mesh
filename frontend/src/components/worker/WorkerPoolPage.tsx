import React, { useState, useEffect } from 'react'
import {
  Users,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle,
  Clock,
  Ban,
  Activity
} from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import type { Task } from '../../types'

interface WorkerPoolProps {
  nodeId: string
}

export const WorkerPoolPage: React.FC<WorkerPoolProps> = ({ nodeId }) => {
  const { can } = useAuth()
  const [poolData, setPoolData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchPool = async () => {
    try {
      setLoading(true)
      const res = await api.getWorkerPool(nodeId)
      setPoolData(res)
    } catch (err) {
      console.error('Failed to load worker pool data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPool()
    const interval = setInterval(fetchPool, 3000)
    return () => clearInterval(interval)
  }, [nodeId])

  const concurrency = poolData?.concurrency || 4
  const activeCount = poolData?.active_count || 0
  const availableSlots = Math.max(0, concurrency - activeCount)
  const activeTasks: Task[] = poolData?.active_tasks || []

  // Create an array representing slots
  const slots = Array.from({ length: concurrency }).map((_, idx) => {
    const task = activeTasks[idx] || null
    return {
      slotIndex: idx + 1,
      isOccupied: !!task,
      task,
    }
  })

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
            <Users className="text-cyan-400" size={24} />
            Execution & Worker Pool
          </h1>
          <p className="page-description">
            Local concurrency semaphore state, slot capacity allocations, and thread worker statuses.
          </p>
        </div>
        <button
          onClick={fetchPool}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid mb-6">
        <div className="kpi-card">
          <div className="kpi-label">Configured Concurrency</div>
          <div className="kpi-value text-white">{concurrency} Slots</div>
          <div className="kpi-change text-secondary">Local worker semaphore capacity</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Active Running Slots</div>
          <div className="kpi-value text-blue-400">{activeCount}</div>
          <div className="kpi-change text-secondary">Occupied execution threads</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Available Slots</div>
          <div className="kpi-value text-emerald-400">{availableSlots}</div>
          <div className="kpi-change text-secondary">Ready for immediate dispatch</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Pool Utilization</div>
          <div className="kpi-value text-purple-400">
            {concurrency > 0 ? ((activeCount / concurrency) * 100).toFixed(1) : 0}%
          </div>
          <div className="progress-bar mt-2">
            <div
              className="progress-fill bg-purple-500"
              style={{
                width: `${Math.min(concurrency > 0 ? (activeCount / concurrency) * 100 : 0, 100)}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Visual Slot Allocator */}
      <div className="card mb-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-4 flex items-center gap-2">
          <Activity size={16} className="text-cyan-400" /> Semaphore Execution Slots
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {slots.map((slot) => (
            <div
              key={slot.slotIndex}
              className={`p-4 rounded-lg border flex flex-col justify-between ${
                slot.isOccupied
                  ? 'bg-blue-950/20 border-blue-800 text-blue-200'
                  : 'bg-[#121418] border-[#23272f] text-gray-400'
              }`}
            >
              <div className="flex justify-between items-center mb-3">
                <span className="font-mono text-xs font-bold">Slot #{slot.slotIndex}</span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                    slot.isOccupied
                      ? 'bg-blue-900/60 text-blue-300 border border-blue-700'
                      : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  {slot.isOccupied ? 'OCCUPIED' : 'IDLE'}
                </span>
              </div>

              {slot.isOccupied && slot.task ? (
                <div className="text-xs font-mono space-y-1">
                  <div className="text-white font-bold truncate">
                    {slot.task.id.slice(0, 12)}...
                  </div>
                  <div className="text-secondary">{slot.task.task_type}</div>
                  <div className="text-[11px] text-blue-300">P{slot.task.priority} Priority</div>
                </div>
              ) : (
                <div className="text-xs text-secondary italic py-2">
                  Waiting for task assignment...
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

