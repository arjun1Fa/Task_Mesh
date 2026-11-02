import React from 'react'
import {
  Layers,
  ArrowRight,
  Send,
  Clock,
  Cpu,
  Play,
  CheckCircle2,
  AlertTriangle,
  Zap
} from 'lucide-react'
import type { Task, NodeProfile } from '@shared/types'

interface BottomFeaturePanelsProps {
  tasks: Task[]
  nodes: NodeProfile[]
  clusterStatus: string
  fairnessCv: number
}

export const BottomFeaturePanels: React.FC<BottomFeaturePanelsProps> = ({
  tasks,
  nodes,
  clusterStatus,
  fairnessCv,
}) => {
  // 1. Task Flow Active Stage Detection
  const hasRunning = tasks.some((t) => t.status === 'running')
  const hasPending = tasks.some((t) => t.status === 'pending' || t.status === 'scheduled')
  const completedCount = tasks.filter((t) => t.status === 'completed').length

  // Stages: Submit -> Queue -> Schedule -> Execute -> Complete
  const stages = [
    { id: 'submit', label: 'Submit', icon: Send, active: true },
    { id: 'queue', label: 'Queue', icon: Clock, active: hasPending || hasRunning },
    { id: 'schedule', label: 'Schedule', icon: Cpu, active: hasRunning },
    { id: 'execute', label: 'Execute', icon: Play, active: hasRunning },
    { id: 'complete', label: 'Complete', icon: CheckCircle2, active: completedCount > 0 },
  ]

  // 2. Inference Readiness Calculation
  const yoloNodes = nodes.filter((n) =>
    (n.capabilities?.supported_handlers || []).some((h) => h.includes('inference') || h.includes('yolo')) ||
    (n.capabilities?.tags || []).some((t) => t.toLowerCase().includes('yolo') || t.toLowerCase().includes('ai'))
  )
  const isYoloReady = yoloNodes.length > 0 || nodes.some((n) => n.status === 'online')

  // 3. Realistic System Health Metric (Operational Availability percentage)
  const onlineCount = nodes.filter((n) => n.status === 'online').length
  const totalCount = nodes.length
  // Health % derived from online ratio and dispatch stability
  const nodeAvailabilityPct = totalCount > 0 ? (onlineCount / totalCount) * 100 : 100
  const isHealthy = clusterStatus.toLowerCase() === 'healthy' || clusterStatus.toLowerCase() === 'online'
  const calculatedHealthPct = isHealthy
    ? (nodeAvailabilityPct * 0.98 + (fairnessCv < 0.2 ? 2.0 : 0.5)).toFixed(1)
    : (nodeAvailabilityPct * 0.75).toFixed(1)

  // Circular gauge calculations
  const healthNum = parseFloat(calculatedHealthPct)
  const arcRadius = 42
  const arcCirc = Math.PI * arcRadius // Semi-circle gauge (180 deg)
  const arcDashoffset = arcCirc - (healthNum / 100) * arcCirc

  return (
    <div className="grid grid-3" style={{ gap: '1.25rem', marginTop: '1.25rem' }}>
      {/* ============================================================== */}
      {/* SECTION A: Inference Workloads                                 */}
      {/* ============================================================== */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.45rem' }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                backgroundColor: 'rgba(255, 51, 75, 0.15)',
                border: '1px solid rgba(255, 51, 75, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ff334b',
              }}
            >
              <Layers size={15} />
            </div>
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Inference Workloads
            </h3>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.4', marginBottom: '1rem' }}>
            Run AI models (e.g., YOLOv8n) with distributed offloading and result aggregation.
          </p>
        </div>

        {/* Premium Abstract 3D Model Inference Illustration */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.5rem 0' }}>
          <div style={{ position: 'relative', width: 140, height: 95, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="140" height="95" viewBox="0 0 140 95" fill="none">
              <defs>
                <radialGradient id="yoloGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#ff334b" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#ff334b" stopOpacity="0" />
                </radialGradient>
                <linearGradient id="yoloFaceTop" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3d1822" />
                  <stop offset="100%" stopColor="#1a0f16" />
                </linearGradient>
                <linearGradient id="yoloFaceLeft" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#2a121c" />
                  <stop offset="100%" stopColor="#0d080e" />
                </linearGradient>
                <linearGradient id="yoloFaceRight" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#361523" />
                  <stop offset="100%" stopColor="#120a11" />
                </linearGradient>
              </defs>

              {/* Ambient Red Glow Halo */}
              <ellipse cx="70" cy="62" rx="55" ry="20" fill="url(#yoloGlow)" />
              <ellipse cx="70" cy="62" rx="48" ry="14" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="3 3" />

              {/* Bottom Base Pedestal Isometric Plate */}
              <polygon points="70,52 110,64 70,76 30,64" fill="url(#yoloFaceTop)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.6" />
              <polygon points="30,64 70,76 70,84 30,72" fill="url(#yoloFaceLeft)" stroke="#ff334b" strokeWidth="0.8" strokeOpacity="0.5" />
              <polygon points="70,76 110,64 110,72 70,84" fill="url(#yoloFaceRight)" stroke="#ff334b" strokeWidth="0.8" strokeOpacity="0.5" />

              {/* Top Floating Core Block */}
              <polygon points="70,18 102,28 70,38 38,28" fill="url(#yoloFaceTop)" stroke="#ff334b" strokeWidth="1.5" />
              <polygon points="38,28 70,38 70,56 38,46" fill="url(#yoloFaceLeft)" stroke="#ff334b" strokeWidth="1" />
              <polygon points="70,38 102,28 102,46 70,56" fill="url(#yoloFaceRight)" stroke="#ff334b" strokeWidth="1" />

              {/* YOLOv8n Label on Left Face */}
              <text
                x="52"
                y="48"
                fill="#ffffff"
                fontSize="7.5"
                fontFamily="var(--font-mono)"
                fontWeight="700"
                transform="rotate(14 52 48) skewX(-20)"
                letterSpacing="0.05em"
              >
                YOLOv8n
              </text>

              {/* Status Indicator Pip */}
              <circle cx="86" cy="40" r="1.8" fill={isYoloReady ? '#10b981' : '#f59e0b'} />
            </svg>
          </div>
        </div>

        {/* Model Readiness Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Workload engine</span>
          <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
            {isYoloReady ? 'YOLOv8 Ready' : 'Standby'}
          </span>
        </div>
      </div>

      {/* ============================================================== */}
      {/* SECTION B: Task Flow (Live)                                    */}
      {/* ============================================================== */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.45rem' }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                backgroundColor: 'rgba(255, 51, 75, 0.15)',
                border: '1px solid rgba(255, 51, 75, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ff334b',
              }}
            >
              <Zap size={15} />
            </div>
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Task Flow (Live)
            </h3>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.4', marginBottom: '1.25rem' }}>
            Real-time lifecycle of submitted tasks across the compute mesh.
          </p>
        </div>

        {/* Animated Connected Task Lifecycle Stepper */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 0' }}>
          {stages.map((st, i) => {
            const Icon = st.icon
            const isLast = i === stages.length - 1
            const isHighlight = st.id === (hasRunning ? 'execute' : hasPending ? 'queue' : 'submit')

            return (
              <React.Fragment key={st.id}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.45rem' }}>
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: isHighlight
                        ? 'rgba(255, 51, 75, 0.2)'
                        : st.active
                        ? 'rgba(255, 255, 255, 0.05)'
                        : 'rgba(255, 255, 255, 0.02)',
                      border: isHighlight
                        ? '1.5px solid #ff334b'
                        : st.active
                        ? '1px solid rgba(255, 51, 75, 0.4)'
                        : '1px solid var(--border-subtle)',
                      color: isHighlight ? '#ff334b' : st.active ? '#ffa8b4' : 'var(--text-muted)',
                      boxShadow: isHighlight ? '0 0 12px rgba(255, 51, 75, 0.4)' : undefined,
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <Icon size={14} />
                  </div>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: isHighlight ? '#ffffff' : 'var(--text-secondary)',
                    }}
                  >
                    {st.label}
                  </span>
                </div>

                {!isLast && (
                  <div style={{ flex: 1, height: 2, margin: '0 4px', marginBottom: '18px', position: 'relative' }}>
                    {/* SVG Dotted / Flowing Connector Line */}
                    <svg width="100%" height="2" style={{ display: 'block', overflow: 'visible' }}>
                      <line
                        x1="0"
                        y1="1"
                        x2="100%"
                        y2="1"
                        stroke={st.active ? '#ff334b' : 'rgba(255, 255, 255, 0.1)'}
                        strokeWidth="1.5"
                        strokeDasharray={st.active ? '4 3' : undefined}
                        style={{
                          animation: st.active ? 'flowDash 1.2s linear infinite' : undefined,
                        }}
                      />
                    </svg>
                  </div>
                )}
              </React.Fragment>
            )
          })}
        </div>

        {/* Live Active State Status */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Lifecycle engine</span>
          <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--accent-red)', fontWeight: 600 }}>
            {hasRunning ? 'Dispatching active' : hasPending ? 'Tasks queued' : 'Mesh idle / ready'}
          </span>
        </div>
      </div>

      {/* ============================================================== */}
      {/* SECTION C: System Health                                       */}
      {/* ============================================================== */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.45rem' }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                backgroundColor: 'rgba(255, 51, 75, 0.15)',
                border: '1px solid rgba(255, 51, 75, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ff334b',
              }}
            >
              <Activity size={15} />
            </div>
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              System Health
            </h3>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.4', marginBottom: '0.5rem' }}>
            Cluster stability, node health, and orchestrator status at a glance.
          </p>
        </div>

        {/* Circular Semi-Arc Health Gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0.5rem 0' }}>
          <div style={{ position: 'relative', width: 120, height: 75, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="120" height="75" viewBox="0 0 120 75">
              {/* Background Arc */}
              <path
                d="M 15 65 A 45 45 0 0 1 105 65"
                fill="none"
                stroke="rgba(255, 255, 255, 0.08)"
                strokeWidth="8"
                strokeLinecap="round"
              />
              {/* Emerald Active Arc */}
              <path
                d="M 15 65 A 45 45 0 0 1 105 65"
                fill="none"
                stroke="#10b981"
                strokeWidth="8"
                strokeDasharray={`${(healthNum / 100) * 141.37} 141.37`}
                strokeLinecap="round"
                style={{
                  filter: 'drop-shadow(0 0 6px rgba(16, 185, 129, 0.5))',
                  transition: 'stroke-dasharray 0.4s ease',
                }}
              />
            </svg>

            {/* Centered Score */}
            <div
              style={{
                position: 'absolute',
                bottom: 2,
                left: 0,
                right: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span className="mono" style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>
                {calculatedHealthPct}%
              </span>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Health Score
              </span>
            </div>
          </div>
        </div>

        {/* Health Detail Breakdown */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Status telemetry</span>
          <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
            {clusterStatus.toUpperCase()}
          </span>
        </div>
      </div>
    </div>
  )
}
