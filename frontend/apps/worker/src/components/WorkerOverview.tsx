import React, { useState, useEffect } from 'react'
import {
  Server,
  Activity,
  Cpu,
  HardDrive,
  RefreshCw,
  Clock,
  Layers,
  CheckCircle,
  AlertTriangle,
  Wifi,
  ArrowUpRight,
  ArrowDownLeft,
  Radio,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { WorkerOverview as WorkerOverviewType } from '@shared/types'

interface WorkerOverviewProps {
  overview: WorkerOverviewType | null
  onRefresh: () => void
  onNavigateToHardware: () => void
  onNavigateToTasks: () => void
  onNavigateToSettings: () => void
}

export const WorkerOverview: React.FC<WorkerOverviewProps> = ({
  overview,
  onRefresh,
  onNavigateToHardware,
  onNavigateToTasks,
  onNavigateToSettings,
}) => {
  const [loading, setLoading] = useState(false)

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await onRefresh()
    } finally {
      setLoading(false)
    }
  }

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '0s'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    return `${h}h ${m}m ${s}s`
  }

  const cpuVal = Number(overview?.cpu_percent ?? 0)
  const ramVal = Number(overview?.ram_percent ?? 0)
  const gpuVal = Number(overview?.gpu_percent ?? 0)
  const activeTasks = overview?.active_tasks ?? 0
  const concurrency = overview?.worker_concurrency ?? 4
  const completedTasks = overview?.completed_tasks ?? 0
  const failedTasks = overview?.failed_tasks ?? 0
  const isConnected = overview?.connection_status === 'connected'

  return (
    <div>
      {/* Title & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Server size={20} color="var(--accent-purple)" />
            Local Node Overview
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Real-time telemetry, hardware capacity, and orchestrator uplink for worker daemon <span className="mono" style={{ color: 'var(--accent-cyan)' }}>{overview?.node_id || 'local'}</span>
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={handleRefresh} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Local Node Identity & Daemon Status Banner */}
      <div className="card" style={{ marginBottom: '1.25rem', borderColor: 'var(--border-color)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(168, 85, 247, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Server size={22} color="var(--accent-purple)" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 700 }} className="mono">
                  {overview?.node_id || 'node-agent'}
                </span>
                <span className={`status-pill ${overview?.status || 'offline'}`}>
                  {overview?.status || 'OFFLINE'}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                Host: <span className="mono">{overview?.hostname || 'localhost'}</span> • Agent v{overview?.agent_version || '0.2.0'} • Local Execution Daemon
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Uplink Status</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '2px' }}>
                <Radio size={13} color={isConnected ? 'var(--status-online)' : 'var(--status-failed)'} />
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: isConnected ? 'var(--status-online)' : 'var(--status-failed)' }}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Target Orchestrator</div>
              <div className="mono" style={{ fontSize: '0.82rem', color: 'var(--accent-cyan)', marginTop: '2px' }}>
                {overview?.orchestrator_url || 'ws://127.0.0.1:8000/v1/ws/nodes'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Uptime</div>
              <div className="mono" style={{ fontSize: '0.82rem', marginTop: '2px' }}>
                {formatUptime(overview?.uptime_seconds)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top 4 KPI Cards */}
      <div className="grid grid-4" style={{ marginBottom: '1.25rem' }}>
        <div className="stat-card" style={{ cursor: 'pointer' }} onClick={onNavigateToTasks}>
          <div className="stat-label">Active Task Slots</div>
          <div className="stat-value" style={{ color: 'var(--accent-blue)' }}>
            {activeTasks} / {concurrency}
          </div>
          <div className="progress-bar-container" style={{ marginTop: '0.5rem', height: '5px' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, (activeTasks / (concurrency || 1)) * 100))}%`,
                backgroundColor: 'var(--accent-blue)',
              }}
            />
          </div>
          <div className="stat-hint" style={{ marginTop: '0.35rem' }}>
            {concurrency - activeTasks} slots available
          </div>
        </div>

        <div className="stat-card" style={{ cursor: 'pointer' }} onClick={onNavigateToHardware}>
          <div className="stat-label">CPU Utilization</div>
          <div className="stat-value mono" style={{ color: cpuVal > 85 ? 'var(--status-failed)' : 'var(--accent-cyan)' }}>
            {cpuVal.toFixed(1)}%
          </div>
          <div className="progress-bar-container" style={{ marginTop: '0.5rem', height: '5px' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, cpuVal))}%`,
                backgroundColor: cpuVal > 85 ? 'var(--status-failed)' : 'var(--accent-cyan)',
              }}
            />
          </div>
          <div className="stat-hint" style={{ marginTop: '0.35rem' }}>
            Host Processor Core Load
          </div>
        </div>

        <div className="stat-card" style={{ cursor: 'pointer' }} onClick={onNavigateToHardware}>
          <div className="stat-label">RAM Utilization</div>
          <div className="stat-value mono" style={{ color: ramVal > 85 ? 'var(--status-degraded)' : 'var(--accent-green)' }}>
            {ramVal.toFixed(1)}%
          </div>
          <div className="progress-bar-container" style={{ marginTop: '0.5rem', height: '5px' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, ramVal))}%`,
                backgroundColor: ramVal > 85 ? 'var(--status-degraded)' : 'var(--accent-green)',
              }}
            />
          </div>
          <div className="stat-hint" style={{ marginTop: '0.35rem' }}>
            System Physical Memory
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Completed / Failed Tasks</div>
          <div className="stat-value mono">
            <span style={{ color: 'var(--accent-green)' }}>{completedTasks}</span>
            <span style={{ color: 'var(--text-dim)', margin: '0 4px' }}>/</span>
            <span style={{ color: failedTasks > 0 ? 'var(--status-failed)' : 'var(--text-dim)' }}>{failedTasks}</span>
          </div>
          <div className="stat-hint" style={{ marginTop: '0.5rem' }}>
            Local execution history
          </div>
        </div>
      </div>

      {/* GPU & Network Details */}
      <div className="grid grid-2" style={{ gap: '1.25rem' }}>
        {/* GPU Status Card */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Cpu size={16} color="var(--accent-green)" />
              <span className="card-title">GPU Accelerator</span>
            </div>
            {overview?.has_gpu ? (
              <span className="badge badge-emerald">Active</span>
            ) : (
              <span className="badge badge-slate">None Detected</span>
            )}
          </div>

          {overview?.has_gpu ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-dim)' }}>GPU Model:</span>
                <span className="mono" style={{ fontWeight: 600 }}>{overview.gpu_name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-dim)' }}>VRAM Capacity:</span>
                <span className="mono">{Math.round((overview.gpu_vram_mb || 0) / 1024)} GB</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-dim)' }}>GPU Core Load:</span>
                <span className="mono">{gpuVal.toFixed(1)}%</span>
              </div>
              <div className="progress-bar-container" style={{ height: '5px' }}>
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${Math.min(100, Math.max(0, gpuVal))}%`,
                    backgroundColor: 'var(--accent-green)',
                  }}
                />
              </div>
            </div>
          ) : (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
              No discrete GPU accelerator detected on this system.
              <br />
              All compute tasks are dispatched using CPU threads.
            </div>
          )}
        </div>

        {/* Network & Uplink EWMA Telemetry */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Wifi size={16} color="var(--accent-cyan)" />
              <span className="card-title">Transport & Uplink Telemetry</span>
            </div>
            <span className="badge badge-blue">EWMA Filtered</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Round-Trip Time (RTT):</span>
              <span className="mono" style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                {overview?.rtt_ms !== undefined ? `${overview.rtt_ms.toFixed(2)} ms` : 'Local (<0.5ms)'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Upload Bandwidth:</span>
              <span className="mono">
                {overview?.upload_mbps !== undefined ? `${overview.upload_mbps.toFixed(2)} Mbps` : 'N/A'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Download Bandwidth:</span>
              <span className="mono">
                {overview?.download_mbps !== undefined ? `${overview.download_mbps.toFixed(2)} Mbps` : 'N/A'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Frame Protocol:</span>
              <span className="mono" style={{ color: 'var(--text-color)' }}>
                48-byte TMCH Header + 64KB Chunks
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

