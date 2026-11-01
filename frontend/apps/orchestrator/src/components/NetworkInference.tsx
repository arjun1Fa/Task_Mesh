import React, { useState, useEffect } from 'react'
import {
  Wifi,
  Network,
  RefreshCw,
  HardDrive,
  Cpu,
  Layers,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle2,
  FileCode,
  Activity,
  Zap,
  ShieldCheck
} from 'lucide-react'
import { api } from '../api/client'
import type { NodeProfile } from '@shared/types'

export const NetworkInference: React.FC = () => {
  const [nodes, setNodes] = useState<NodeProfile[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [activeTab, setActiveTab] = useState<'network' | 'tmch' | 'inference'>('network')

  const fetchNetworkData = async () => {
    try {
      setLoading(true)
      const data = await api.listNodes()
      setNodes(data)
    } catch (err) {
      console.error('Failed to load node network data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNetworkData()
    const interval = setInterval(fetchNetworkData, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Wifi className="text-pink-400" size={24} />
            Network Topology & Binary Inference
          </h1>
          <p className="page-description">
            Wireless link quality, TMCH 48-byte chunked streaming protocol, and distributed AI offloading telemetry.
          </p>
        </div>
        <button
          onClick={fetchNetworkData}
          className="btn btn-secondary flex items-center gap-2 text-sm"
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* View Switcher Tabs */}
      <div className="flex border-b border-[#2d3139] mb-6">
        <button
          onClick={() => setActiveTab('network')}
          className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'network'
              ? 'border-pink-500 text-pink-400 bg-pink-950/20'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <Network size={14} /> Node Network Telemetry
        </button>
        <button
          onClick={() => setActiveTab('tmch')}
          className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'tmch'
              ? 'border-pink-500 text-pink-400 bg-pink-950/20'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <FileCode size={14} /> TMCH Protocol (48-Byte Header)
        </button>
        <button
          onClick={() => setActiveTab('inference')}
          className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'inference'
              ? 'border-pink-500 text-pink-400 bg-pink-950/20'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <Zap size={14} /> Distributed Inference & AI Handlers
        </button>
      </div>

      {/* Tab 1: Node Network Telemetry */}
      {activeTab === 'network' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nodes.length === 0 ? (
              <div className="col-span-3 card text-center py-10 text-secondary">
                No active nodes registered in the cluster
              </div>
            ) : (
              nodes.map((node) => {
                const telem = node.telemetry
                const rtt = telem?.rtt_ms_ewma ?? telem?.network_latency_ms ?? 0
                const upload = telem?.upload_mbps_ewma ?? 0
                const download = telem?.download_mbps_ewma ?? 0
                const failures = telem?.transfer_failures ?? 0

                return (
                  <div key={node.id} className="card bg-[#14161b] flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <div className="font-mono text-sm font-bold text-white flex items-center gap-2">
                            {node.id}
                            {node.capabilities.is_local && (
                              <span className="text-[10px] bg-blue-950/80 text-blue-300 px-1.5 py-0.5 rounded border border-blue-800">
                                LOCAL
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-secondary font-mono">
                            {node.capabilities.hostname || 'Unknown host'} &bull; {node.capabilities.ip_address || '127.0.0.1'}
                          </div>
                        </div>
                        <span className={`badge badge-${node.status}`}>{node.status.toUpperCase()}</span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 bg-[#0f1013] p-3 rounded-lg border border-[#23272f] mb-3">
                        <div>
                          <span className="text-[11px] text-secondary flex items-center gap-1">
                            <Activity size={12} className="text-blue-400" /> RTT (EWMA)
                          </span>
                          <span className="text-base font-bold font-mono text-white">
                            {rtt > 0 ? `${Number(rtt).toFixed(2)} ms` : 'Local loop'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-secondary flex items-center gap-1">
                            <ArrowUpRight size={12} className="text-green-400" /> Upload
                          </span>
                          <span className="text-base font-bold font-mono text-white">
                            {upload > 0 ? `${Number(upload).toFixed(1)} Mbps` : 'Unrated'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-secondary flex items-center gap-1">
                            <ArrowDownLeft size={12} className="text-cyan-400" /> Download
                          </span>
                          <span className="text-base font-bold font-mono text-white">
                            {download > 0 ? `${Number(download).toFixed(1)} Mbps` : 'Unrated'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-secondary flex items-center gap-1">
                            <HardDrive size={12} className="text-amber-400" /> Failures
                          </span>
                          <span
                            className={`text-base font-bold font-mono ${
                              failures > 0 ? 'text-red-400' : 'text-gray-300'
                            }`}
                          >
                            {failures}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-between items-center text-[11px] font-mono text-secondary pt-2 border-t border-[#23272f]">
                      <span>Effective Score: {(node.effective_score ?? 1.0).toFixed(3)}</span>
                      <span>DRR Deficit: {node.drr_deficit ?? 0}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 2: TMCH Binary Chunking Protocol */}
      {activeTab === 'tmch' && (
        <div className="space-y-6">
          <div className="card bg-[#14161b]">
            <h2 className="font-semibold text-base text-white mb-2 flex items-center gap-2">
              <ShieldCheck className="text-pink-400" size={18} />
              TaskMesh Chunk Header (TMCH) Binary Architecture
            </h2>
            <p className="text-xs text-secondary leading-relaxed mb-4">
              To support high-throughput wireless tensor streaming without JSON encoding overhead, TaskMesh employs the 
              proprietary <strong>48-byte binary framing header</strong> for all large inference payloads (images, weights, embeddings).
            </p>

            {/* Header Structure Diagram */}
            <div className="bg-[#0f1013] border border-[#2d3139] p-4 rounded-lg overflow-x-auto">
              <div className="text-xs font-mono text-secondary mb-2 font-semibold">
                TMCH 48-BYTE STRUCT PACK FORMAT (<span className="text-pink-400">&gt;4s B B H 16s I I I 8s I I</span>):
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 text-xs font-mono">
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-pink-400 block font-bold">0x00 - 0x03 (4B)</span>
                  <span className="text-white">Magic: 'TMCH'</span>
                  <span className="text-[10px] text-gray-500 block">0x54 0x4D 0x43 0x48</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-blue-400 block font-bold">0x04 (1B)</span>
                  <span className="text-white">Version: 0x01</span>
                  <span className="text-[10px] text-gray-500 block">Protocol version</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-purple-400 block font-bold">0x05 (1B)</span>
                  <span className="text-white">Workload Type</span>
                  <span className="text-[10px] text-gray-500 block">YOLO, ResNet, etc.</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-amber-400 block font-bold">0x06 - 0x07 (2B)</span>
                  <span className="text-white">Flags</span>
                  <span className="text-[10px] text-gray-500 block">Compression / Enc</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-emerald-400 block font-bold">0x08 - 0x17 (16B)</span>
                  <span className="text-white">Task UUID</span>
                  <span className="text-[10px] text-gray-500 block">Raw binary 128-bit</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-cyan-400 block font-bold">0x18 - 0x1B (4B)</span>
                  <span className="text-white">Chunk Index</span>
                  <span className="text-[10px] text-gray-500 block">uint32 sequential</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-cyan-400 block font-bold">0x1C - 0x1F (4B)</span>
                  <span className="text-white">Total Chunks</span>
                  <span className="text-[10px] text-gray-500 block">uint32 count</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-indigo-400 block font-bold">0x20 - 0x23 (4B)</span>
                  <span className="text-white">Chunk Length</span>
                  <span className="text-[10px] text-gray-500 block">Payload bytes (64KB)</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-gray-400 block font-bold">0x24 - 0x2B (8B)</span>
                  <span className="text-white">Reserved</span>
                  <span className="text-[10px] text-gray-500 block">Zero-padded alignment</span>
                </div>
                <div className="bg-[#181a1f] p-2.5 rounded border border-[#2d3139]">
                  <span className="text-red-400 block font-bold">0x2C - 0x2F (4B)</span>
                  <span className="text-white">Header CRC32</span>
                  <span className="text-[10px] text-gray-500 block">Integrity checksum</span>
                </div>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                <div className="font-bold text-xs text-white mb-1">Standard Chunk Size</div>
                <div className="font-mono text-lg text-pink-400">65,536 Bytes (64 KB)</div>
                <p className="text-[11px] text-secondary mt-1">
                  Optimized for MTU sliding windows across typical 802.11ac/ax Wi-Fi networks.
                </p>
              </div>
              <div className="bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                <div className="font-bold text-xs text-white mb-1">Integrity Verification</div>
                <div className="font-mono text-lg text-emerald-400">SHA-256 + CRC32</div>
                <p className="text-[11px] text-secondary mt-1">
                  Every chunk validated by CRC32; entire assembled payload verified by SHA-256.
                </p>
              </div>
              <div className="bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                <div className="font-bold text-xs text-white mb-1">Payload Reassembly Engine</div>
                <div className="font-mono text-lg text-blue-400">OutOfOrder Buffered</div>
                <p className="text-[11px] text-secondary mt-1">
                  Handles packet reordering and drops with idempotent chunk re-transmission.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Distributed Inference & AI Handlers */}
      {activeTab === 'inference' && (
        <div className="space-y-6">
          <div className="card bg-[#14161b]">
            <h2 className="font-semibold text-base text-white mb-2 flex items-center gap-2">
              <Cpu className="text-purple-400" size={18} />
              Registered AI Inference Handlers
            </h2>
            <p className="text-xs text-secondary leading-relaxed mb-4">
              Workloads capable of adaptive split execution or offloaded remote GPU acceleration.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-[#0f1013] border border-[#2d3139] p-4 rounded-lg">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold font-mono text-sm text-white">yolo_inference / object_detection</span>
                  <span className="badge badge-running">Active</span>
                </div>
                <p className="text-xs text-secondary mb-3">
                  Ultralytics YOLOv8 object detection with bounding-box generation and class confidence scoring.
                </p>
                <div className="text-xs font-mono space-y-1 text-gray-300 bg-[#181a1f] p-2 rounded">
                  <div className="flex justify-between">
                    <span>Input Mime:</span>
                    <span className="text-purple-300">image/jpeg, image/png</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Target Acceleration:</span>
                    <span className="text-green-400">CUDA GPU / TensorRT</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Inference Time:</span>
                    <span className="text-white">~35ms (GPU) vs ~420ms (CPU)</span>
                  </div>
                </div>
              </div>

              <div className="bg-[#0f1013] border border-[#2d3139] p-4 rounded-lg">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold font-mono text-sm text-white">benchmark / matrix_mult</span>
                  <span className="badge badge-running">Active</span>
                </div>
                <p className="text-xs text-secondary mb-3">
                  CPU and GPU computational capacity benchmarking via high-dimensional matrix dot products.
                </p>
                <div className="text-xs font-mono space-y-1 text-gray-300 bg-[#181a1f] p-2 rounded">
                  <div className="flex justify-between">
                    <span>Payload:</span>
                    <span className="text-purple-300">JSON matrix parameters</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Target Acceleration:</span>
                    <span className="text-gray-400">Any Available Worker</span>
                  </div>
                  <div className="flex justify-between">
                    <span>FLOPS Estimation:</span>
                    <span className="text-white">Derived dynamically</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

