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
  RotateCcw,
  Pause,
  Play,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { WorkerOverview } from '@shared/types'
import { ConfirmationModal } from '@shared/components/ConfirmationModal'

interface WorkerSettingsProps {
  overview: WorkerOverview | null
  onRefresh: () => void
}

export const WorkerSettings: React.FC<WorkerSettingsProps> = ({
  overview,
  onRefresh,
}) => {
  const [loading, setLoading] = useState(false)
  const [concurrencyInput, setConcurrencyInput] = useState<number>(
    overview?.worker_concurrency || 4
  )
  const [isUpdatingConcurrency, setIsUpdatingConcurrency] = useState(false)

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean
    title: string
    message: string
    affectedComponents: string[]
    isDangerous: boolean
    action: () => Promise<void>
  }>({
    isOpen: false,
    title: '',
    message: '',
    affectedComponents: [],
    isDangerous: false,
    action: async () => {},
  })

  const [feedback, setFeedback] = useState<string | null>(null)

  useEffect(() => {
    if (overview?.worker_concurrency) {
      setConcurrencyInput(overview.worker_concurrency)
    }
  }, [overview?.worker_concurrency])

  const showFeedback = (msg: string) => {
    setFeedback(msg)
    setTimeout(() => setFeedback(null), 4000)
  }

  const handleDrain = () => {
    setConfirmModal({
      isOpen: true,
      title: 'Drain Local Worker Node',
      message:
        'Instruct this worker agent to reject new task leases while continuing to finish existing active executions?',
      affectedComponents: ['Local Async Pool', 'Orchestrator Heartbeat Status'],
      isDangerous: true,
      action: async () => {
        await workerApi.drain()
        showFeedback('Worker placed in DRAINING mode.')
        onRefresh()
      },
    })
  }

  const handleResume = () => {
    setConfirmModal({
      isOpen: true,
      title: 'Resume Local Worker Node',
      message:
        'Restore this worker agent to ONLINE status? The central orchestrator will immediately resume dispatching tasks to this node.',
      affectedComponents: ['Local Async Pool', 'Orchestrator Dispatcher'],
      isDangerous: false,
      action: async () => {
        await workerApi.resume()
        showFeedback('Worker restored to ONLINE state.')
        onRefresh()
      },
    })
  }

  const handleToggleMaintenance = () => {
    const isMaint = overview?.status === 'maintenance'
    setConfirmModal({
      isOpen: true,
      title: isMaint ? 'Exit Maintenance Mode' : 'Enter Maintenance Mode',
      message: isMaint
        ? 'Re-enable this node and notify the orchestrator that maintenance is concluded?'
        : 'Take this node offline for hardware servicing, driver installation, or debugging?',
      affectedComponents: ['Local Worker Daemon', 'Orchestrator Health Watchdog'],
      isDangerous: !isMaint,
      action: async () => {
        await workerApi.setMaintenance(!isMaint)
        showFeedback(isMaint ? 'Worker exited maintenance mode.' : 'Worker entered maintenance mode.')
        onRefresh()
      },
    })
  }

  const handleUpdateConcurrency = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsUpdatingConcurrency(true)
    try {
      await workerApi.updateConcurrency(concurrencyInput)
      showFeedback(`Worker concurrency updated to ${concurrencyInput} slots.`)
      onRefresh()
    } catch (err: any) {
      alert(`Failed to update concurrency: ${err.message}`)
    } finally {
      setIsUpdatingConcurrency(false)
    }
  }

  const handleTogglePause = async () => {
    try {
      const res = await workerApi.togglePause()
      showFeedback(
        res.paused_assignments
          ? 'Task assignments temporarily paused.'
          : 'Task assignments resumed.'
      )
      onRefresh()
    } catch (err: any) {
      alert(`Failed to toggle pause: ${err.message}`)
    }
  }

  const isDraining = overview?.status === 'draining'
  const isMaintenance = overview?.status === 'maintenance'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Settings size={20} color="var(--accent-purple)" />
            Local Node Management & Controls
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Operational controls for local worker daemon: drain, resume, maintenance, and concurrency limit
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      {feedback && (
        <div
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1.25rem',
            color: 'var(--accent-green)',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle size={16} />
          <span>{feedback}</span>
        </div>
      )}

      {/* Operational State Actions */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="card-header">
          <span className="card-title">Node Lifecycle State Controls</span>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
          {!isDraining ? (
            <button className="btn btn-secondary" onClick={handleDrain}>
              <Pause size={14} style={{ marginRight: '6px' }} />
              Drain Node (Graceful Stop)
            </button>
          ) : (
            <button className="btn btn-primary" onClick={handleResume}>
              <Play size={14} style={{ marginRight: '6px' }} />
              Resume Node Scheduling
            </button>
          )}

          <button
            className={`btn ${isMaintenance ? 'btn-primary' : 'btn-secondary'}`}
            onClick={handleToggleMaintenance}
          >
            <Wrench size={14} style={{ marginRight: '6px' }} />
            {isMaintenance ? 'Exit Maintenance Mode' : 'Enter Maintenance Mode'}
          </button>

          <button className="btn btn-secondary" onClick={handleTogglePause}>
            <Sliders size={14} style={{ marginRight: '6px' }} />
            Toggle Fast Assignment Pause
          </button>
        </div>
      </div>

      {/* Concurrency Adjustment Form */}
      <div className="card" style={{ maxWidth: '480px' }}>
        <div className="card-header">
          <span className="card-title">Worker Concurrency Limit</span>
        </div>

        <form onSubmit={handleUpdateConcurrency}>
          <div className="form-group">
            <label className="form-label">Concurrent Execution Slots (1 - 64)</label>
            <input
              type="number"
              min={1}
              max={64}
              className="form-input"
              value={concurrencyInput}
              onChange={(e) => setConcurrencyInput(parseInt(e.target.value) || 1)}
              required
            />
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
              Adjusts the local asyncio Semaphore capacity and advertises the new limit to the central orchestrator.
            </span>
          </div>

          <button type="submit" className="btn btn-primary btn-sm" disabled={isUpdatingConcurrency}>
            {isUpdatingConcurrency ? 'Applying...' : 'Apply Concurrency'}
          </button>
        </form>
      </div>

      {/* Confirmation Modal */}
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

