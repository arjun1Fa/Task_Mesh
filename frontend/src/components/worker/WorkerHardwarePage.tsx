import React, { useState, useEffect } from 'react'
import {
  Cpu,
  HardDrive,
  RefreshCw,
  Tag,
  CheckCircle,
  HelpCircle,
  Zap,
  Layers,
  Scale
} from 'lucide-react'
import { api } from '../../api/client'

interface WorkerHardwareProps {
  nodeId: string
}

export const WorkerHardwarePage: React.FC<WorkerHardwareProps> = ({ nodeId }) => {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      const res = await api.getWorkerHardware(nodeId)
      setData(res)
    } catch (err) {
      console.error('Failed to load worker hardware:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [nodeId])

  const caps = data?.capabilities || {}
  const scheduler = data?.scheduler_derived || {}

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
            <Cpu className="text-cyan-400" size={24} />
            Hardware Profile & Capabilities
          </h1>
          <p className="page-description">
            Physical host hardware detection versus adaptive scheduler-derived scores and DRR fairness counters.
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

      {/* Hardware Profile Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Detected Hardware Factsheet */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-4 flex items-center gap-2">
            <Cpu size={16} className="text-blue-400" /> Physical Detected Hardware
          </h2>

          <div className="space-y-3 text-xs font-mono">
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Processor Cores:</span>
              <span className="text-white font-bold">{caps.cpu_cores || 'N/A'} Cores</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">CPU Frequency:</span>
              <span className="text-white font-bold">
                {caps.cpu_frequency_mhz ? `${caps.cpu_frequency_mhz} MHz` : 'Dynamic scaling'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Total System RAM:</span>
              <span className="text-white font-bold">
                {caps.ram_total_mb ? `${(caps.ram_total_mb / 1024).toFixed(1)} GB (${caps.ram_total_mb} MB)` : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Operating System / Arch:</span>
              <span className="text-white font-bold">
                {caps.os || 'Windows'} / {caps.arch || 'x86_64'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Discrete GPU:</span>
              <span className={caps.has_gpu ? 'text-purple-400 font-bold' : 'text-gray-400'}>
                {caps.has_gpu ? caps.gpu_name || 'Present' : 'Not Detected'}
              </span>
            </div>
            {caps.has_gpu && (
              <div className="flex justify-between py-2 border-b border-[#23272f]">
                <span className="text-secondary">GPU VRAM:</span>
                <span className="text-purple-300 font-bold">{caps.gpu_vram_mb || 0} MB</span>
              </div>
            )}
            <div className="flex justify-between py-2">
              <span className="text-secondary">Worker Concurrency Limit:</span>
              <span className="text-cyan-400 font-bold">{caps.worker_capacity || 4} slots</span>
            </div>
          </div>
        </div>

        {/* Scheduler-Derived Values */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-4 flex items-center gap-2">
            <Scale size={16} className="text-purple-400" /> Scheduler-Derived Metrics & Fairness
          </h2>

          <div className="space-y-3 text-xs font-mono">
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Base Score:</span>
              <span className="text-cyan-300 font-bold">
                {scheduler.base_score !== undefined ? Number(scheduler.base_score).toFixed(4) : '1.0000'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Performance Multiplier:</span>
              <span className="text-purple-300 font-bold">
                {scheduler.performance_multiplier !== undefined
                  ? Number(scheduler.performance_multiplier).toFixed(4)
                  : '1.0000'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Effective Dispatch Score:</span>
              <span className="text-emerald-400 font-bold">
                {scheduler.effective_score !== undefined
                  ? Number(scheduler.effective_score).toFixed(4)
                  : '1.0000'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">DRR Deficit Counter:</span>
              <span className="text-amber-300 font-bold">
                {scheduler.drr_deficit ?? 0} (Quantum: 1000)
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Total Assigned Tasks:</span>
              <span className="text-white font-bold">{scheduler.total_assigned ?? 0}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#23272f]">
              <span className="text-secondary">Total Completed:</span>
              <span className="text-green-400 font-bold">{scheduler.total_completed ?? 0}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-secondary">Total Failed:</span>
              <span className="text-red-400 font-bold">{scheduler.total_failed ?? 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Supported Handlers & Tags */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Handlers */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
            <Zap size={16} className="text-amber-400" /> Supported Workload Handlers
          </h2>
          <div className="flex flex-wrap gap-2">
            {(caps.supported_handlers || ['benchmark', 'echo']).map((handler: string) => (
              <span
                key={handler}
                className="bg-[#0f1013] border border-[#2d3139] text-gray-200 px-3 py-1.5 rounded-md text-xs font-mono font-semibold"
              >
                {handler}
              </span>
            ))}
          </div>
        </div>

        {/* Capability Tags */}
        <div className="card bg-[#14161b]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
            <Tag size={16} className="text-pink-400" /> Capability Tags & Match Criteria
          </h2>
          <div className="flex flex-wrap gap-2">
            {(caps.tags && caps.tags.length > 0
              ? caps.tags
              : ['general-compute', caps.has_gpu ? 'gpu-accelerated' : 'cpu-only']
            ).map((tag: string) => (
              <span
                key={tag}
                className="bg-[#0f1013] border border-pink-900/40 text-pink-300 px-3 py-1.5 rounded-md text-xs font-mono"
              >
                #{tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

