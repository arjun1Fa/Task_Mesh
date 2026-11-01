import React, { useState, useEffect } from 'react'
import {
  Cpu,
  HardDrive,
  RefreshCw,
  Tag,
  CheckCircle,
  Zap,
  Layers,
  Scale,
  Shield,
  Activity,
} from 'lucide-react'
import { workerApi } from '../api/workerClient'
import type { WorkerHardware as WorkerHardwareType } from '@shared/types'

export const WorkerHardware: React.FC = () => {
  const [data, setData] = useState<WorkerHardwareType | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      const res = await workerApi.getHardware()
      setData(res)
    } catch (err) {
      console.error('Failed to load worker hardware:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const hw = data?.detected_hardware || ({} as any)
  const sched = data?.scheduler_registered || ({} as any)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Cpu size={20} color="var(--accent-purple)" />
            Local Hardware Profile & Registered Capabilities
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Host physical specifications probed by TaskMesh agent daemon vs capabilities registered in the central scheduler
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={fetchData} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-2" style={{ gap: '1.25rem', marginBottom: '1.25rem' }}>
        {/* Physical Probed Hardware */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <HardDrive size={16} color="var(--accent-blue)" />
              <span className="card-title">Probed Physical Hardware</span>
            </div>
            <span className="badge badge-blue">Local System</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>CPU Logical Cores:</span>
              <span className="mono" style={{ fontWeight: 600 }}>{hw.cpu_cores || 0} Cores</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>CPU Base Frequency:</span>
              <span className="mono">{hw.cpu_frequency_mhz ? `${hw.cpu_frequency_mhz} MHz` : 'Dynamic'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Total System Memory:</span>
              <span className="mono">{Math.round((hw.ram_total_mb || 0) / 1024)} GB</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Operating System:</span>
              <span className="mono">{hw.os || 'Unknown OS'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>CPU Architecture:</span>
              <span className="mono">{hw.arch || 'x86_64'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>GPU Accelerator:</span>
              <span className="mono" style={{ color: hw.has_gpu ? 'var(--accent-green)' : 'var(--text-dim)' }}>
                {hw.has_gpu ? `${hw.gpu_name} (${Math.round((hw.gpu_vram_mb || 0) / 1024)}GB VRAM)` : 'No GPU'}
              </span>
            </div>
          </div>
        </div>

        {/* Scheduler Profile Registration */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Scale size={16} color="var(--accent-purple)" />
              <span className="card-title">Scheduler Advertised Capabilities</span>
            </div>
            <span className="badge badge-purple">Advertised</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Worker Concurrency Slots:</span>
              <span className="mono" style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                {sched.worker_capacity || 4} parallel tasks
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-dim)' }}>Cluster Node Placement:</span>
              <span className="mono">{sched.is_local ? 'Local Orchestrator Host' : 'Remote Network Worker'}</span>
            </div>

            <div>
              <div style={{ color: 'var(--text-dim)', marginBottom: '0.35rem' }}>Supported Handlers:</div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {(sched.supported_handlers || ['benchmark', 'echo']).map((handler: string) => (
                  <span key={handler} className="badge badge-blue">
                    {handler}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--text-dim)', marginBottom: '0.35rem' }}>Capability Tags:</div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {(sched.tags && sched.tags.length > 0 ? sched.tags : ['cpu_general', 'edge_worker']).map(
                  (tag: string) => (
                    <span key={tag} className="badge badge-slate">
                      <Tag size={10} style={{ marginRight: '3px' }} />
                      {tag}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

