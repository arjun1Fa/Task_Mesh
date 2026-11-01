import React, { useState, useEffect } from 'react'
import {
  Sliders,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle,
  Clock,
  Ban,
  Activity,
  Zap,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { WorkerPoolStatus, Task } from '@shared/types'

export const WorkerPool: React.FC = () => {
  const [poolData, setPoolData] = useState<WorkerPoolStatus | null>(null)
  const [tasksData, setTasksData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchPool = async () => {
    try {
      setLoading(true)
      const [pool, tasks] = await Promise.all([
        workerApi.getPool(),
        workerApi.getTasks().catch(() => ({ active_tasks: [] })),
      ])
      setPoolData(pool)
      setTasksData(tasks)
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
  }, [])

  const concurrency = poolData?.concurrency || 4
  const activeCount = poolData?.active_slots || 0
  const availableSlots = poolData?.available_slots ?? Math.max(0, concurrency - activeCount)
  const activeTasks: Task[] = tasksData?.active_tasks || []

  const slots = Array.from({ length: concurrency }).map((_, idx) => {
    const task = activeTasks[idx] || null
    return {
      slotIndex: idx + 1,
      isOccupied: !!task,
      task,
    }
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sliders size={20} color="var(--accent-purple)" />
            Concurrency Semaphore Slots
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Visual allocation of the local async task executor pool and thread slots
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={fetchPool} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Utilization Bar */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div>
            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Pool Capacity Utilization</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginLeft: '0.5rem' }}>
              {activeCount} of {concurrency} slots occupied
            </span>
          </div>
          <span className="mono" style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {poolData?.utilization_percent ?? ((activeCount / (concurrency || 1)) * 100).toFixed(0)}%
          </span>
        </div>

        <div className="progress-bar-container" style={{ height: '8px' }}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${Math.min(100, Math.max(0, (activeCount / (concurrency || 1)) * 100))}%`,
              backgroundColor: activeCount === concurrency ? 'var(--status-degraded)' : 'var(--accent-purple)',
            }}
          />
        </div>
      </div>

      {/* Semaphore Slot Grid */}
      <div className="grid grid-4" style={{ gap: '1rem' }}>
        {slots.map((slot) => (
          <div
            key={slot.slotIndex}
            className="card"
            style={{
              margin: 0,
              padding: '1rem',
              borderColor: slot.isOccupied ? 'var(--accent-blue)' : 'var(--border-color)',
              backgroundColor: slot.isOccupied ? 'rgba(59, 130, 246, 0.05)' : 'var(--bg-surface)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Zap size={14} color={slot.isOccupied ? 'var(--accent-blue)' : 'var(--text-dim)'} />
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Slot #{slot.slotIndex}</span>
              </div>
              <span
                className={`badge ${slot.isOccupied ? 'badge-blue' : 'badge-slate'}`}
                style={{ fontSize: '0.68rem', padding: '1px 6px' }}
              >
                {slot.isOccupied ? 'OCCUPIED' : 'IDLE'}
              </span>
            </div>

            {slot.isOccupied && slot.task ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.78rem' }}>
                <div className="mono" style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                  {slot.task.id.slice(0, 14)}...
                </div>
                <div style={{ color: 'var(--text-color)' }}>Type: {slot.task.task_type}</div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                  Started: {new Date(slot.task.scheduled_at || slot.task.created_at).toLocaleTimeString()}
                </div>
              </div>
            ) : (
              <div style={{ padding: '0.8rem 0', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                Slot ready for incoming lease
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

