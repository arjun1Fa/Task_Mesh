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
  HardDrive
} from 'lucide-react'
import { api } from '../../api/client'

interface WorkerNetworkProps {
  nodeId: string
}

export const WorkerNetworkPage: React.FC<WorkerNetworkProps> = ({ nodeId }) => {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      const res = await api.getWorkerNetwork(nodeId)
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
  }, [nodeId])

  const wsConnected = data?.websocket_connected ?? true
  const rtt = data?.rtt_ms_ewma ?? 0
  const upload = data?.upload_mbps_ewma ?? 0
  const download = data?.download_mbps_ewma ?? 0
  const binaryStats = data?.binary_transport || {}

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
            <Wifi className="text-cyan-400" size={24} />
            Network & Orchestrator Communication
          </h1>
          <p className="page-description">
            WebSocket channel state, periodic heartbeat telemetry, and TMCH 48-byte binary chunk streaming.
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

      {/* WebSocket Connection Status Banner */}
      <div className="card mb-6 bg-[#16181e] border-[#2d3139]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`status-dot ${wsConnected ? 'status-online' : 'status-offline'} w-4 h-4`} />
            <div>
              <div className="text-xs text-secondary uppercase font-semibold">Orchestrator WS Link</div>
              <div className="text-lg font-bold font-mono text-white flex items-center gap-2">
                {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
                <span className="text-xs font-normal text-cyan-300 font-mono">
                  &bull; Endpoint: {data?.orchestrator_url || 'ws://127.0.0.1:8000/v1/ws/nodes'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-secondary block">Heartbeat Interval:</span>
              <span className="text-white font-bold">{data?.heartbeat_interval_seconds ?? 5.0}s</span>
            </div>
            <div>
              <span className="text-secondary block">Last Heartbeat:</span>
              <span className="text-green-400 font-bold">
                {data?.last_heartbeat ? new Date(data.last_heartbeat).toLocaleTimeString() : 'Live'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Network Metrics Cards */}
      <div className="kpi-grid mb-6">
        <div className="kpi-card">
          <div className="kpi-label">Round-Trip Latency (EWMA)</div>
          <div className="kpi-value text-white">
            {rtt > 0 ? `${Number(rtt).toFixed(2)} ms` : 'Local loopback'}
          </div>
          <div className="kpi-change text-secondary">Smoothed with &alpha; = 0.2 factor</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Upload Bandwidth (EWMA)</div>
          <div className="kpi-value text-green-400">
            {upload > 0 ? `${Number(upload).toFixed(1)} Mbps` : 'Unrated'}
          </div>
          <div className="kpi-change text-secondary">Outbound inference result pipe</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Download Bandwidth (EWMA)</div>
          <div className="kpi-value text-cyan-400">
            {download > 0 ? `${Number(download).toFixed(1)} Mbps` : 'Unrated'}
          </div>
          <div className="kpi-change text-secondary">Inbound chunk stream rate</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Transfer Failures</div>
          <div className={`kpi-value ${data?.transfer_failures > 0 ? 'text-red-400' : 'text-gray-300'}`}>
            {data?.transfer_failures ?? 0}
          </div>
          <div className="kpi-change text-secondary">Packet re-transmissions recorded</div>
        </div>
      </div>

      {/* Binary Transport Protocol & Assembly Engine */}
      <div className="card bg-[#14161b]">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
          <ShieldCheck size={16} className="text-pink-400" /> TMCH Binary Chunk Stream Receiver
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">Framing Protocol:</span>
            <span className="text-pink-400 font-bold">TMCH v1 (48-Byte Packed)</span>
            <span className="text-[11px] text-gray-500 block mt-1">
              Zero-copy direct binary framing over WebSocket
            </span>
          </div>

          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">Integrity Verification:</span>
            <span className="text-emerald-400 font-bold">CRC32 + SHA-256</span>
            <span className="text-[11px] text-gray-500 block mt-1">
              Corrupted chunks dropped and re-requested
            </span>
          </div>

          <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
            <span className="text-secondary block">Chunk Assembly Window:</span>
            <span className="text-white font-bold">64 KB Chunks &bull; Reordering Buffer</span>
            <span className="text-[11px] text-gray-500 block mt-1">
              Assembled in-memory prior to AI handler execution
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

