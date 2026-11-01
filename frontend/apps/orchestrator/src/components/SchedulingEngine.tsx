import React, { useState, useEffect } from 'react'
import {
  Cpu,
  Sliders,
  Activity,
  Zap,
  BarChart2,
  RefreshCw,
  Check,
  AlertCircle,
  HelpCircle,
  TrendingUp,
  Scale,
  DollarSign,
  Wifi,
  ChevronRight,
  Info
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { SchedulerDecision, SchedulerMode } from '@shared/types'

export const SchedulingEngine: React.FC = () => {
  const { can } = useAuth()
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<any>(null)
  const [diagnostics, setDiagnostics] = useState<any>(null)
  const [decisions, setDecisions] = useState<SchedulerDecision[]>([])
  const [selectedDecision, setSelectedDecision] = useState<SchedulerDecision | null>(null)

  // Mode change
  const [modeChanging, setModeChanging] = useState(false)
  const [selectedMode, setSelectedMode] = useState<SchedulerMode>('adaptive')

  // Adaptive Toggles
  const [toggles, setToggles] = useState<Record<string, boolean>>({
    rl_enabled: true,
    drr_fairness_enabled: true,
    contract_net_enabled: true,
    ewma_enabled: true,
    multi_armed_bandit_enabled: true,
    wireless_inference_enabled: true,
  })
  const [toggleLoading, setToggleLoading] = useState(false)

  // Interactive Wireless Estimator State
  const [simPayloadKb, setSimPayloadKb] = useState<number>(512)
  const [simRttMs, setSimRttMs] = useState<number>(35)
  const [simBandwidthMbps, setSimBandwidthMbps] = useState<number>(45)
  const [simLocalInferenceMs, setSimLocalInferenceMs] = useState<number>(350)
  const [simRemoteInferenceMs, setSimRemoteInferenceMs] = useState<number>(45)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [st, diag, dec] = await Promise.all([
        api.getSchedulerStatus().catch(() => null),
        api.getSchedulerDiagnostics().catch(() => null),
        api.getSchedulerDecisions(30).catch(() => []),
      ])

      if (st) {
        setStatus(st)
        if (st.mode) setSelectedMode(st.mode)
        if (st.adaptive_toggles) setToggles(st.adaptive_toggles)
      }
      if (diag) setDiagnostics(diag)
      if (dec) setDecisions(dec)
    } catch (err) {
      console.error('Error fetching scheduler data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 4000)
    return () => clearInterval(interval)
  }, [])

  const handleModeChange = async (mode: SchedulerMode) => {
    if (!can('scheduler:change_mode')) return
    try {
      setModeChanging(true)
      await api.changeSchedulerMode(mode)
      setSelectedMode(mode)
      await fetchData()
    } catch (err: any) {
      alert(`Failed to change mode: ${err.message}`)
    } finally {
      setModeChanging(false)
    }
  }

  const handleToggle = async (key: string) => {
    if (!can('scheduler:configure')) return
    const newToggles = { ...toggles, [key]: !toggles[key] }
    setToggles(newToggles)
    try {
      setToggleLoading(true)
      await api.updateAdaptiveToggles(newToggles)
      await fetchData()
    } catch (err: any) {
      alert(`Failed to update toggles: ${err.message}`)
      setToggles(toggles) // rollback
    } finally {
      setToggleLoading(false)
    }
  }

  // Wireless Offloading Calculator (TMCH / Wireless Model)
  // upload_time = (payload_bytes * 8) / (bandwidth_mbps * 1e6) * 1000 + (rtt / 2)
  const payloadBytes = simPayloadKb * 1024
  const uploadMs = (payloadBytes * 8) / (Math.max(simBandwidthMbps, 0.1) * 1000) + simRttMs / 2
  const downloadMs = (1024 * 8) / (Math.max(simBandwidthMbps, 0.1) * 1000) + simRttMs / 2 // small result payload ~1KB
  const remoteTotalMs = uploadMs + simRemoteInferenceMs + downloadMs
  const offloadDecision = remoteTotalMs < simLocalInferenceMs ? 'REMOTE' : 'LOCAL'
  const timeSavedMs = Math.abs(simLocalInferenceMs - remoteTotalMs)

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Cpu className="text-purple-400" size={24} />
            Adaptive AI Scheduling Engine
          </h1>
          <p className="page-description">
            Reinforcement learning, Contract Net bidding, DRR fairness, EWMA telemetry, and wireless inference cost modeling.
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

      {/* Mode Switcher Banner */}
      <div className="card mb-6 bg-[#16181e] border-purple-900/40">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Sliders size={20} className="text-purple-400" />
            <div>
              <div className="text-xs text-secondary uppercase font-semibold">Active Dispatch Policy</div>
              <div className="text-lg font-bold font-mono text-white flex items-center gap-2">
                {selectedMode.toUpperCase()}
                <span className="text-xs font-normal text-purple-300 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800">
                  {selectedMode === 'adaptive' ? '6-Component Hybrid RL' : 'Static Fallback Policy'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {(['adaptive', 'round_robin', 'least_loaded', 'highest_bid'] as SchedulerMode[]).map((m) => (
              <button
                key={m}
                onClick={() => handleModeChange(m)}
                disabled={modeChanging || !can('scheduler:change_mode')}
                className={`px-3 py-1.5 text-xs font-mono rounded-md border transition-all ${
                  selectedMode === m
                    ? 'bg-purple-600/30 border-purple-500 text-purple-200 font-bold shadow-sm'
                    : 'bg-[#181a1f] border-[#2d3139] text-gray-400 hover:border-gray-500 disabled:opacity-50'
                }`}
              >
                {m.replace('_', ' ').toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 6 Adaptive Subsystems & Toggles */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3 flex items-center gap-2">
          <Activity size={16} className="text-blue-400" />
          Adaptive Engine Subsystem Toggles
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Subsystem 1: EWMA */}
          <div className="card bg-[#14161b] flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="font-semibold text-sm text-white flex items-center gap-1.5">
                  <TrendingUp size={16} className="text-blue-400" /> 1. EWMA Telemetry Tracking
                </span>
                <input
                  type="checkbox"
                  checked={toggles.ewma_enabled ?? true}
                  onChange={() => handleToggle('ewma_enabled')}
                  disabled={!can('scheduler:configure') || toggleLoading}
                  className="rounded cursor-pointer"
                />
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Maintains rolling exponential moving averages of node RTT, upload/download bandwidth, and failure penalties to filter transient noise.
              </p>
            </div>
            <div className="text-[11px] font-mono text-gray-400 bg-[#0f1013] p-2 rounded border border-[#23272f]">
              Smoothing factor &alpha; = 0.2 &bull; Active
            </div>
          </div>

          {/* Subsystem 2: DRR Fairness */}
          <div className="card bg-[#14161b] flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="font-semibold text-sm text-white flex items-center gap-1.5">
                  <Scale size={16} className="text-emerald-400" /> 2. Deficit Round-Robin (DRR)
                </span>
                <input
                  type="checkbox"
                  checked={toggles.drr_fairness_enabled ?? true}
                  onChange={() => handleToggle('drr_fairness_enabled')}
                  disabled={!can('scheduler:configure') || toggleLoading}
                  className="rounded cursor-pointer"
                />
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Enforces cluster-wide fairness using deficit counters, preventing starved nodes while penalizing over-allocated workers. Target CV &lt; 0.25.
              </p>
            </div>
            <div className="text-[11px] font-mono text-gray-400 bg-[#0f1013] p-2 rounded border border-[#23272f]">
              Fairness CV Target: &le; 0.25 &bull; Quantum: 1000
            </div>
          </div>

          {/* Subsystem 3: Contract Net */}
          <div className="card bg-[#14161b] flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="font-semibold text-sm text-white flex items-center gap-1.5">
                  <DollarSign size={16} className="text-amber-400" /> 3. Contract Net Bidding (CNP)
                </span>
                <input
                  type="checkbox"
                  checked={toggles.contract_net_enabled ?? true}
                  onChange={() => handleToggle('contract_net_enabled')}
                  disabled={!can('scheduler:configure') || toggleLoading}
                  className="rounded cursor-pointer"
                />
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Decentralized bidding evaluating 5 weighted factors: Latency, Resource Load, Capability Tag match, Reliability, and Transfer Cost.
              </p>
            </div>
            <div className="text-[11px] font-mono text-gray-400 bg-[#0f1013] p-2 rounded border border-[#23272f]">
              Weights: Latency (0.25), Load (0.25), Reliability (0.25)
            </div>
          </div>

          {/* Subsystem 4: Multi-Armed Bandit MWU */}
          <div className="card bg-[#14161b] flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="font-semibold text-sm text-white flex items-center gap-1.5">
                  <BarChart2 size={16} className="text-cyan-400" /> 4. MWU / Multi-Armed Bandit
                </span>
                <input
                  type="checkbox"
                  checked={toggles.multi_armed_bandit_enabled ?? true}
                  onChange={() => handleToggle('multi_armed_bandit_enabled')}
                  disabled={!can('scheduler:configure') || toggleLoading}
                  className="rounded cursor-pointer"
                />
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Hedge multiplicative weights update algorithm adapting exploration vs exploitation over historical task outcomes without stationary bias.
              </p>
            </div>
            <div className="text-[11px] font-mono text-gray-400 bg-[#0f1013] p-2 rounded border border-[#23272f]">
              Learning rate &eta; = 0.15 &bull; Softmax normalization
            </div>
          </div>

          {/* Subsystem 5: Q-Learning */}
          <div className="card bg-[#14161b] flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="font-semibold text-sm text-white flex items-center gap-1.5">
                  <Zap size={16} className="text-purple-400" /> 5. Q-Learning Tuning
                </span>
                <input
                  type="checkbox"
                  checked={toggles.rl_enabled ?? true}
                  onChange={() => handleToggle('rl_enabled')}
                  disabled={!can('scheduler:configure') || toggleLoading}
                  className="rounded cursor-pointer"
                />
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Tabular Q-learning mapping cluster states (load bin, queue size bin, network state) to policy adjustment actions with reward shaping.
              </p>
            </div>
            <div className="text-[11px] font-mono text-gray-400 bg-[#0f1013] p-2 rounded border border-[#23272f]">
              States: 27 bins &bull; Actions: 4 policies &bull; &gamma; = 0.95
            </div>
          </div>

          {/* Subsystem 6: Wireless Inference Offloading */}
          <div className="card bg-[#14161b] flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="font-semibold text-sm text-white flex items-center gap-1.5">
                  <Wifi size={16} className="text-pink-400" /> 6. Wireless Inference Offload
                </span>
                <input
                  type="checkbox"
                  checked={toggles.wireless_inference_enabled ?? true}
                  onChange={() => handleToggle('wireless_inference_enabled')}
                  disabled={!can('scheduler:configure') || toggleLoading}
                  className="rounded cursor-pointer"
                />
              </div>
              <p className="text-xs text-secondary leading-relaxed mb-3">
                Calculates bandwidth/RTT penalty against remote GPU acceleration advantage to decide whether to run local or offload over TMCH binary stream.
              </p>
            </div>
            <div className="text-[11px] font-mono text-gray-400 bg-[#0f1013] p-2 rounded border border-[#23272f]">
              TMCH binary chunking: 64KB &bull; CRC32 + SHA-256
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Wireless Offloading Cost Estimator */}
      <div className="card mb-6 bg-[#16181e] border-pink-900/30">
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#2d3139]">
          <div className="flex items-center gap-2">
            <Wifi className="text-pink-400" size={18} />
            <h2 className="font-semibold text-sm text-white">
              Adaptive Wireless Inference Cost Estimator
            </h2>
          </div>
          <span className="text-xs text-secondary font-mono">
            T_remote = T_upload + T_inference + T_download vs T_local
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-center">
          {/* Controls */}
          <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="text-secondary block mb-1">Payload Size (KB):</label>
              <input
                type="number"
                value={simPayloadKb}
                onChange={(e) => setSimPayloadKb(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-1.5 rounded w-full font-mono text-xs"
              />
            </div>
            <div>
              <label className="text-secondary block mb-1">Network RTT (ms):</label>
              <input
                type="number"
                value={simRttMs}
                onChange={(e) => setSimRttMs(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-1.5 rounded w-full font-mono text-xs"
              />
            </div>
            <div>
              <label className="text-secondary block mb-1">Bandwidth (Mbps):</label>
              <input
                type="number"
                value={simBandwidthMbps}
                onChange={(e) => setSimBandwidthMbps(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-1.5 rounded w-full font-mono text-xs"
              />
            </div>
            <div>
              <label className="text-secondary block mb-1">Local CPU Exec (ms):</label>
              <input
                type="number"
                value={simLocalInferenceMs}
                onChange={(e) => setSimLocalInferenceMs(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-1.5 rounded w-full font-mono text-xs"
              />
            </div>
            <div>
              <label className="text-secondary block mb-1">Remote GPU Exec (ms):</label>
              <input
                type="number"
                value={simRemoteInferenceMs}
                onChange={(e) => setSimRemoteInferenceMs(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-1.5 rounded w-full font-mono text-xs"
              />
            </div>
          </div>

          {/* Decision Outcome */}
          <div className="lg:col-span-2 bg-[#0f1013] border border-[#2d3139] p-4 rounded-lg flex flex-col justify-between">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-secondary uppercase font-semibold">Engine Offload Verdict</span>
              <span
                className={`px-2.5 py-0.5 rounded text-xs font-bold font-mono ${
                  offloadDecision === 'REMOTE'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}
              >
                OFFLOAD {offloadDecision}
              </span>
            </div>
            <div className="text-xs font-mono space-y-1 text-gray-300">
              <div className="flex justify-between">
                <span>Upload + Transmit:</span>
                <span className="text-white font-semibold">{uploadMs.toFixed(1)} ms</span>
              </div>
              <div className="flex justify-between">
                <span>Remote GPU Execution:</span>
                <span className="text-white font-semibold">{simRemoteInferenceMs.toFixed(1)} ms</span>
              </div>
              <div className="flex justify-between">
                <span>Download Result:</span>
                <span className="text-white font-semibold">{downloadMs.toFixed(1)} ms</span>
              </div>
              <div className="flex justify-between border-t border-[#23272f] pt-1 font-bold">
                <span>Total Remote Latency:</span>
                <span className={remoteTotalMs < simLocalInferenceMs ? 'text-green-400' : 'text-red-400'}>
                  {remoteTotalMs.toFixed(1)} ms
                </span>
              </div>
              <div className="flex justify-between">
                <span>Local CPU Latency:</span>
                <span className="text-gray-400">{simLocalInferenceMs.toFixed(1)} ms</span>
              </div>
            </div>
            <div className="mt-3 text-[11px] text-purple-300 bg-purple-950/40 p-1.5 rounded border border-purple-900/50">
              {offloadDecision === 'REMOTE'
                ? `Offloading saves ~${timeSavedMs.toFixed(1)} ms (${((timeSavedMs / simLocalInferenceMs) * 100).toFixed(0)}% speedup)`
                : `Local execution is ~${timeSavedMs.toFixed(1)} ms faster than wireless transfer`}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Decisions & Explainability Log */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <Activity className="text-blue-400" size={18} />
            <h2 className="font-semibold text-sm text-white">Recent Dispatch Decisions & Explainability Audit</h2>
          </div>
          <span className="text-xs text-secondary font-mono">{decisions.length} recorded events</span>
        </div>

        <div className="table-wrapper max-h-96 overflow-y-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Policy Used</th>
                <th>Selected Node</th>
                <th>Offload Decision</th>
                <th>Candidate Count</th>
                <th>Timestamp</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {decisions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-secondary">
                    No recent scheduler decisions recorded
                  </td>
                </tr>
              ) : (
                decisions.map((dec, idx) => (
                  <tr key={dec.task_id || idx} className="hover:bg-[#1a1d24]">
                    <td className="font-mono text-xs text-blue-400 font-semibold">
                      {dec.task_id ? `${dec.task_id.slice(0, 12)}...` : 'N/A'}
                    </td>
                    <td>
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#181a1f] border border-[#2d3139] text-gray-300">
                        {dec.policy_used}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-green-400 font-bold">
                      {dec.selected_node_id}
                    </td>
                    <td>
                      <span
                        className={`text-xs font-mono font-semibold ${
                          dec.offload_decision === 'remote' ? 'text-pink-400' : 'text-gray-300'
                        }`}
                      >
                        {dec.offload_decision?.toUpperCase() || 'LOCAL'}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-gray-400">
                      {dec.candidate_node_ids?.length || 0} nodes
                    </td>
                    <td className="font-mono text-xs text-secondary">
                      {new Date(dec.timestamp).toLocaleTimeString()}
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedDecision(dec)}
                        className="btn btn-secondary px-2 py-1 text-xs"
                      >
                        Explain
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Decision Drilldown Modal */}
      {selectedDecision && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="card max-w-2xl w-full max-h-[85vh] flex flex-col bg-[#14161b] border-[#2d3139]">
            <div className="flex justify-between items-center pb-3 border-b border-[#2d3139]">
              <div>
                <h3 className="font-semibold text-lg text-white font-mono">
                  Decision Breakdown: {selectedDecision.task_id}
                </h3>
                <span className="text-xs text-secondary font-mono">
                  Policy: {selectedDecision.policy_used} &bull; Selected: {selectedDecision.selected_node_id}
                </span>
              </div>
              <button
                onClick={() => setSelectedDecision(null)}
                className="text-gray-400 hover:text-white font-mono text-lg px-2"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto p-4 space-y-4 text-xs font-mono">
              <div className="bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                <div className="font-bold text-white mb-2">Candidate Bids & Scores:</div>
                <div className="space-y-1">
                  {Object.entries(selectedDecision.candidate_scores || {}).map(([nodeId, score]) => (
                    <div
                      key={nodeId}
                      className={`flex justify-between p-1.5 rounded ${
                        nodeId === selectedDecision.selected_node_id
                          ? 'bg-green-950/40 border border-green-800 text-green-300'
                          : 'bg-[#0f1013] text-gray-400'
                      }`}
                    >
                      <span>{nodeId} {nodeId === selectedDecision.selected_node_id ? '✓ (WINNER)' : ''}</span>
                      <span>Score: {Number(score).toFixed(4)} | Bid: {selectedDecision.bids?.[nodeId] ?? 'N/A'}</span>
                    </div>
                  ))}
                </div>
              </div>

              {selectedDecision.offload_reason && (
                <div className="bg-[#181a1f] p-3 rounded border border-[#2d3139]">
                  <div className="font-bold text-purple-300 mb-1">Offload Decision Rationale:</div>
                  <p className="text-gray-300">{selectedDecision.offload_reason}</p>
                </div>
              )}

              {selectedDecision.fallback_reason && (
                <div className="bg-amber-950/40 border border-amber-800/60 p-3 rounded text-amber-300">
                  <div className="font-bold mb-1">Fallback Reason:</div>
                  <p>{selectedDecision.fallback_reason}</p>
                </div>
              )}

              <div>
                <span className="text-secondary block font-bold mb-1">Raw Decision Data:</span>
                <pre className="bg-[#0f1013] border border-[#2d3139] p-3 rounded text-gray-300 max-h-48 overflow-y-auto">
                  {JSON.stringify(selectedDecision, null, 2)}
                </pre>
              </div>
            </div>

            <div className="p-3 border-t border-[#2d3139] flex justify-end bg-[#181a1f]">
              <button onClick={() => setSelectedDecision(null)} className="btn btn-secondary text-xs">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

