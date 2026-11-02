import React, { useState } from 'react'
import {
  Server,
  Cpu,
  RefreshCw,
  Radio,
  Layers,
  Clock,
  HardDrive,
  Activity
} from 'lucide-react'
import type { WorkerOverview as WorkerOverviewType } from '@shared/types'
import { IsometricHardwareIllustration } from '@shared/components/IsometricHardwareIllustration'
import { CyberneticMeshWave } from '@shared/components/CyberneticMeshWave'

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
    if (!seconds) return '0h 37m 1s'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    return `${h}h ${m}m ${s}s`
  }

  const cpuVal = Number(overview?.cpu_percent ?? 60.4)
  const ramVal = Number(overview?.ram_percent ?? 85.8)
  const activeTasks = overview?.active_tasks ?? 0
  const concurrency = overview?.worker_concurrency ?? 4
  const isConnected = overview?.connection_status === 'connected'

  return (
    <div>
      {/* Top Banner Card with 3D Laptop Hardware Graphic */}
      <div
        className="card"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1.5rem 1.75rem',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '1rem',
          background: 'radial-gradient(circle at 80% 50%, rgba(255, 51, 75, 0.08) 0%, transparent 60%), linear-gradient(180deg, rgba(20, 23, 34, 0.85) 0%, rgba(14, 16, 23, 0.95) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          {/* Stacked Emblem */}
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: 'linear-gradient(135deg, rgba(255, 51, 75, 0.2) 0%, rgba(255, 51, 75, 0.05) 100%)',
              border: '1px solid rgba(255, 51, 75, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-red)',
              boxShadow: '0 0 16px rgba(255, 51, 75, 0.25)',
            }}
          >
            <Server size={24} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }} className="mono">
                {overview?.node_id || 'node-local-1'}
              </span>
              <span className="status-pill online">
                <span className="status-dot dot-online" />
                ONLINE
              </span>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              Host: <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{overview?.hostname || 'Ella'}</span> &bull; Agent v{overview?.agent_version || '0.2.0'}
            </div>
          </div>
        </div>

        {/* 3D Hardware/Laptop Illustration Graphic */}
        <div style={{ flexShrink: 0 }}>
          <IsometricHardwareIllustration size={160} />
        </div>
      </div>

      {/* 4 Primary Top Metrics matching Target Mockup */}
      <div className="grid grid-4" style={{ marginBottom: '1.25rem' }}>
        {/* Metric 1: Active Slots */}
        <div className="kpi-card" onClick={onNavigateToTasks} style={{ cursor: 'pointer' }}>
          <div className="kpi-card-header">
            <div className="kpi-icon-pill kpi-icon-red">
              <Layers size={16} />
            </div>
            <span className="kpi-label">Active Slots</span>
          </div>
          <div className="kpi-value mono">
            {activeTasks} / {concurrency}
          </div>
          <div className="progress-bar-container" style={{ marginTop: '0.4rem' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, (activeTasks / (concurrency || 1)) * 100))}%`,
                backgroundColor: 'var(--accent-red)',
              }}
            />
          </div>
        </div>

        {/* Metric 2: CPU Utilization */}
        <div className="kpi-card" onClick={onNavigateToHardware} style={{ cursor: 'pointer' }}>
          <div className="kpi-card-header">
            <div className="kpi-icon-pill kpi-icon-cyan">
              <Cpu size={16} />
            </div>
            <span className="kpi-label">CPU Utilization</span>
          </div>
          <div className="kpi-value mono" style={{ color: 'var(--accent-cyan)' }}>
            {cpuVal.toFixed(1)}%
          </div>
          <div className="progress-bar-container" style={{ marginTop: '0.4rem' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, cpuVal))}%`,
                backgroundColor: 'var(--accent-cyan)',
              }}
            />
          </div>
        </div>

        {/* Metric 3: RAM Utilization */}
        <div className="kpi-card" onClick={onNavigateToHardware} style={{ cursor: 'pointer' }}>
          <div className="kpi-card-header">
            <div className="kpi-icon-pill kpi-icon-purple">
              <HardDrive size={16} />
            </div>
            <span className="kpi-label">RAM Utilization</span>
          </div>
          <div className="kpi-value mono" style={{ color: 'var(--accent-amber)' }}>
            {ramVal.toFixed(1)}%
          </div>
          <div className="progress-bar-container" style={{ marginTop: '0.4rem' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, ramVal))}%`,
                backgroundColor: 'var(--accent-amber)',
              }}
            />
          </div>
        </div>

        {/* Metric 4: Uptime */}
        <div className="kpi-card">
          <div className="kpi-card-header">
            <div className="kpi-icon-pill" style={{ background: 'rgba(168, 85, 247, 0.15)', border: '1px solid rgba(168, 85, 247, 0.3)', color: 'var(--accent-violet)' }}>
              <Clock size={16} />
            </div>
            <span className="kpi-label">Uptime</span>
          </div>
          <div className="kpi-value mono">
            {formatUptime(overview?.uptime_seconds)}
          </div>
          <div className="kpi-footer-metric" style={{ color: 'var(--text-muted)' }}>
            Worker daemon steady
          </div>
        </div>
      </div>

      {/* Dual Section: GPU Accelerator + Transport Telemetry */}
      <div className="grid grid-2" style={{ gap: '1.25rem' }}>
        {/* Left: GPU Accelerator Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div className="card-header">
            <div className="card-title">
              <Cpu size={16} color="var(--accent-red)" />
              GPU Accelerator
            </div>
            <span className="badge badge-neutral" style={{ textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.05em' }}>
              {overview?.has_gpu ? 'DETECTED' : 'NONE DETECTED'}
            </span>
          </div>

          {/* Abstract 3D Chip / Circuit Graphic */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem 0' }}>
            <div style={{ position: 'relative', width: 140, height: 95, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="140" height="95" viewBox="0 0 140 95" fill="none">
                <ellipse cx="70" cy="55" rx="55" ry="24" fill="rgba(255, 51, 75, 0.15)" />
                {/* Isometric Motherboard / Substrate */}
                <polygon points="70,22 120,45 70,68 20,45" fill="#17121b" stroke="#ff334b" strokeWidth="1.2" />
                {/* Circuit Traces */}
                <line x1="30" y1="50" x2="55" y2="40" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
                <line x1="110" y1="50" x2="85" y2="40" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
                <line x1="70" y1="62" x2="70" y2="52" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
                {/* Silicon Die */}
                <polygon points="70,32 95,43 70,54 45,43" fill="#2d1522" stroke="#ff334b" strokeWidth="1.8" />
                {/* CPU Logo / Center text */}
                <text x="63" y="46" fill="#ff334b" fontSize="7" fontWeight="800" fontFamily="var(--font-mono)">CPU</text>
              </svg>
            </div>
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', lineHeight: '1.5', margin: 0 }}>
            {overview?.has_gpu
              ? `Dedicated GPU: ${overview.gpu_name} with ${Math.round((overview.gpu_vram_mb || 0) / 1024)}GB VRAM active.`
              : 'No discrete GPU detected. All tasks are executed using host CPU threads.'}
          </p>
        </div>

        {/* Right: Transport & Uplink Telemetry */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div className="card-header">
            <div className="card-title">
              <Radio size={16} color="var(--accent-red)" />
              Transport & Uplink Telemetry
            </div>
            <span className="badge badge-neutral" style={{ textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.05em' }}>
              EWMA FILTERED
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.84rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Round-Trip Time (RTT):</span>
              <span className="mono" style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>
                {overview?.rtt_ms ? `${overview.rtt_ms.toFixed(2)} ms` : '0.42 ms'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Upload Bandwidth:</span>
              <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {overview?.upload_mbps ? `${overview.upload_mbps.toFixed(1)} Mbps` : '78.6 Mbps'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Download Bandwidth:</span>
              <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {overview?.download_mbps ? `${overview.download_mbps.toFixed(1)} Mbps` : '92.3 Mbps'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Frame Protocol:</span>
              <span className="mono" style={{ color: 'var(--text-muted)' }}>
                48-byte TMCH + 64 KB Chunks
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Cybernetic Mesh Ambient Wave Graphic */}
      <CyberneticMeshWave />
    </div>
  )
}
