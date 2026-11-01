import React, { useState, useEffect } from 'react'
import {
  Wifi,
  RefreshCw,
  Activity,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle,
  AlertTriangle,
  Layers,
  ShieldCheck,
  HardDrive,
  Radio,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { WorkerNetworkStatus } from '@shared/types'

export const WorkerNetwork: React.FC = () => {
  const [data, setData] = useState<WorkerNetworkStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      const res = await workerApi.getNetwork()
      setData(res)
    } catch (err) {
      console.error('Failed to load worker network data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [])

  const wsConnected = data?.websocket_status === 'connected'
  const rtt = data?.rtt_ms_ewma ?? 0
  const upload = data?.upload_mbps_ewma ?? 0
  const download = data?.download_mbps_ewma ?? 0

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Wifi size={20} color="var(--accent-purple)" />
            Network Transport & TMCH Protocol
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            WebSocket duplex channel to orchestrator, EWMA latency tracking, and binary chunk receiver
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={fetchData} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Uplink Metrics */}
      <div className="grid grid-3" style={{ marginBottom: '1.25rem' }}>
        <div className="stat-card">
          <div className="stat-label">Round-Trip Time (EWMA)</div>
          <div className="stat-value mono" style={{ color: 'var(--accent-cyan)' }}>
            {rtt.toFixed(2)} ms
          </div>
          <div className="stat-hint">Calculated with alpha = 0.2 filter</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Estimated Upload Speed</div>
          <div className="stat-value mono" style={{ color: 'var(--accent-green)' }}>
            {upload.toFixed(2)} Mbps
          </div>
          <div className="stat-hint">To orchestrator cluster endpoint</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Estimated Download Speed</div>
          <div className="stat-value mono" style={{ color: 'var(--accent-blue)' }}>
            {download.toFixed(2)} Mbps
          </div>
          <div className="stat-hint">Payload chunk intake bandwidth</div>
        </div>
      </div>

      <div className="grid grid-2" style={{ gap: '1.25rem' }}>
        {/* Connection State */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Radio size={16} color="var(--accent-blue)" />
              <span className="card-title">Orchestrator WebSocket Channel</span>
            </div>
            <span className={`status-pill ${wsConnected ? 'online' : 'offline'}`}>
              {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Primary Endpoint:</span>
              <span className="mono" style={{ color: 'var(--accent-cyan)' }}>
                {data?.orchestrator_url || 'ws://127.0.0.1:8000/v1/ws/nodes'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Standby Replica Endpoint:</span>
              <span className="mono">
                {data?.standby_url || 'None configured'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Frame Sequence Number:</span>
              <span className="mono">#{data?.sequence_number ?? 0}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Wire Security:</span>
              <span className="mono" style={{ color: 'var(--accent-green)' }}>
                HMAC-SHA256 Token Auth + TLS/WSS
              </span>
            </div>
          </div>
        </div>

        {/* TMCH Framing Protocol */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <HardDrive size={16} color="var(--accent-purple)" />
              <span className="card-title">TMCH Binary Framing Protocol</span>
            </div>
            <span className="badge badge-purple">48-Byte Header</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Magic Bytes:</span>
              <span className="mono" style={{ color: 'var(--accent-purple)' }}>0x544D4348 ("TMCH")</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Chunk Frame Size:</span>
              <span className="mono">{data?.chunk_size_bytes ? `${data.chunk_size_bytes / 1024} KB` : '64 KB'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Max Payload Ceiling:</span>
              <span className="mono">{data?.max_payload_size_bytes ? `${data.max_payload_size_bytes / (1024 * 1024)} MB` : '100 MB'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Payload Integrity:</span>
              <span className="mono">Per-chunk SHA-256 + Stream Reconstruction</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

