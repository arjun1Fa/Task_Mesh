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
  Zap
} from 'lucide-react'
import { api } from '../../api/client'
import type { WorkerOverview } from '../../types'

interface WorkerOverviewProps {
  nodeId: string
}

export const WorkerOverviewPage: React.FC<WorkerOverviewProps> = ({ nodeId }) => {
  const [data, setData] = useState<WorkerOverview | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      const res = await api.getWorkerOverview(nodeId)
      setData(res)
    } catch (err) {
      console.error('Failed to load worker overview:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [nodeId])

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'Unavailable'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    return `${h}h ${m}m ${s}s`
  }

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
            <Server className="text-cyan-400" size={24} />
            Worker Node Overview
          </h1>
          <p className="page-description">
            Telemetry, hardware load, local task execution status, and network connection to orchestrator.
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

      {/* Node Status Banner */}
      <div className="card mb-6 bg-[#16181e] border-[#2d3139]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`status-dot status-${data?.status || 'offline'} w-4 h-4`} />
            <div>
              <div className="text-xs text-secondary uppercase font-semibold">Node Status</div>
              <div className="text-lg font-bold font-mono text-white flex items-center gap-2">
                {(data?.status || 'OFFLINE').toUpperCase()}
                <span className="text-xs font-normal text-gray-400 font-mono">
                  &bull; Agent v{data?.agent_version || '1.0.0'}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <span className="text-secondary block">Hostname:</span>
              <span className="text-white font-bold">{data?.hostname || 'Not reported'}</span>
            </div>
            <div>
              <span className="text-secondary block">Uptime:</span>
              <span className="text-white font-bold">{formatUptime(data?.uptime_seconds)}</span>
            </div>
            <div>
              <span className="text-secondary block">Orchestrator URL:</span>
              <span className="text-cyan-400 font-bold truncate block max-w-xs">
                {data?.orchestrator_url || 'ws://127.0.0.1:8000/v1/ws/nodes'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid mb-6">
        <div className="kpi-card">
          <div className="kpi-label">Active Task Slots</div>
          <div className="kpi-value text-blue-400">
            {data?.active_tasks ?? 0} / {data?.worker_concurrency ?? 4}
          </div>
          <div className="progress-bar mt-2">
            <div
              className="progress-fill bg-blue-500"
              style={{
                width: `${Math.min(
                  ((data?.active_tasks ?? 0) / (data?.worker_concurrency ?? 4)) * 100,
                  100
                )}%`,
              }}
            />
          </div>
          <div className="kpi-change text-secondary mt-1">
            Capacity Utilization: {data?.capacity_utilization !== undefined ? `${Number(data.capacity_utilization).toFixed(1)}%` : '0%'}
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">CPU Utilization</div>
          <div className="kpi-value text-white">
            {data?.cpu_percent !== undefined ? `${Number(data.cpu_percent).toFixed(1)}%` : 'Unavailable'}
          </div>
          <div className="progress-bar mt-2">
            <div
              className="progress-fill bg-purple-500"
              style={{ width: `${Math.min(data?.cpu_percent ?? 0, 100)}%` }}
            />
          </div>
          <div className="kpi-change text-secondary mt-1">Host processor load</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">RAM Utilization</div>
          <div className="kpi-value text-white">
            {data?.ram_percent !== undefined ? `${Number(data.ram_percent).toFixed(1)}%` : 'Unavailable'}
          </div>
          <div className="progress-bar mt-2">
            <div
              className="progress-fill bg-cyan-500"
              style={{ width: `${Math.min(data?.ram_percent ?? 0, 100)}%` }}
            />
          </div>
          <div className="kpi-change text-secondary mt-1">System memory footprint</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">GPU Utilization</div>
          <div className="kpi-value text-purple-400">
            {data?.has_gpu
              ? data.gpu_percent !== undefined
                ? `${Number(data.gpu_percent).toFixed(1)}%`
                : '0.0%'
              : 'Not Present'}
          </div>
          <div className="kpi-change text-secondary mt-1">
            {data?.has_gpu
              ? `${data.gpu_name || 'GPU'} (${data.gpu_vram_mb || 0} MB VRAM)`
              : 'CPU only execution profile'}
          </div>
        </div>
      </div>

      {/* Secondary Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Task Counters */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
            <Layers size={16} className="text-cyan-400" /> Local Task Execution Statistics
          </h2>
          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Completed Successfully:</span>
              <span className="text-lg font-bold text-emerald-400">{data?.completed_tasks ?? 0}</span>
            </div>
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Execution Failures:</span>
              <span className="text-lg font-bold text-red-400">{data?.failed_tasks ?? 0}</span>
            </div>
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Queued on Node:</span>
              <span className="text-lg font-bold text-amber-400">{data?.queued_tasks ?? 0}</span>
            </div>
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Assignment State:</span>
              <span className={data?.paused_assignments ? 'text-amber-400 font-bold' : 'text-green-400 font-bold'}>
                {data?.paused_assignments ? 'PAUSED' : 'ACCEPTING TASKS'}
              </span>
            </div>
          </div>
        </div>

        {/* Network & Scheduler Valuation */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
            <Wifi size={16} className="text-pink-400" /> Network Link & Scheduler Valuation
          </h2>
          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Round-Trip Time (RTT):</span>
              <span className="text-base font-bold text-white">
                {data?.rtt_ms !== undefined && data.rtt_ms > 0
                  ? `${Number(data.rtt_ms).toFixed(2)} ms`
                  : 'Loopback / Local'}
              </span>
            </div>
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Upload Throughput:</span>
              <span className="text-base font-bold text-white">
                {data?.upload_mbps !== undefined && data.upload_mbps > 0
                  ? `${Number(data.upload_mbps).toFixed(1)} Mbps`
                  : 'Not reported'}
              </span>
            </div>
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Scheduler Base Score:</span>
              <span className="text-base font-bold text-cyan-300">
                {data?.base_score !== undefined ? Number(data.base_score).toFixed(3) : '1.000'}
              </span>
            </div>
            <div className="bg-[#0f1013] p-3 rounded border border-[#23272f]">
              <span className="text-secondary block">Effective Multiplier:</span>
              <span className="text-base font-bold text-purple-300">
                {data?.performance_multiplier !== undefined ? Number(data.performance_multiplier).toFixed(3) : '1.000'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

