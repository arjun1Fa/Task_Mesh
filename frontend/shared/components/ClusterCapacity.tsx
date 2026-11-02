import React from 'react'

interface ClusterCapacityProps {
  totalNodes: number
  usedCpuCores: number
  totalCpuCores: number
  usedRamGb: number
  totalRamGb: number
  activeSlots: number
  totalSlots: number
}

export const ClusterCapacity: React.FC<ClusterCapacityProps> = ({
  totalNodes,
  usedCpuCores,
  totalCpuCores,
  usedRamGb,
  totalRamGb,
  activeSlots,
  totalSlots,
}) => {
  const cpuPct = totalCpuCores > 0 ? Math.round((usedCpuCores / totalCpuCores) * 100) : 0
  const ramPct = totalRamGb > 0 ? Math.round((usedRamGb / totalRamGb) * 100) : 0
  const slotsPct = totalSlots > 0 ? Math.round((activeSlots / totalSlots) * 100) : 0

  // SVG Circular Ring parameters
  const size = 120
  const strokeW = 10
  const radius = (size - strokeW) / 2
  const circ = 2 * Math.PI * radius
  const cpuStrokeDash = (cpuPct / 100) * circ

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
        Cluster Capacity
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flex: 1 }}>
        {/* Multi-layered Circular Progress Gauge */}
        <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {/* Background Track Ring */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.06)"
              strokeWidth={strokeW}
            />

            {/* Neon Red CPU Utilization Arc */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#ff334b"
              strokeWidth={strokeW}
              strokeDasharray={`${cpuStrokeDash} ${circ - cpuStrokeDash}`}
              strokeDashoffset={circ / 4}
              strokeLinecap="round"
              style={{
                filter: 'drop-shadow(0 0 6px rgba(255, 51, 75, 0.5))',
                transition: 'stroke-dasharray 0.4s ease',
              }}
            />

            {/* Inner Cyan/Violet Accent Ring */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius - 12}
              fill="none"
              stroke="#06b6d4"
              strokeWidth={4}
              strokeDasharray={`${(ramPct / 100) * (2 * Math.PI * (radius - 12))} ${2 * Math.PI * (radius - 12)}`}
              strokeDashoffset={(2 * Math.PI * (radius - 12)) / 4}
              strokeLinecap="round"
              strokeOpacity={0.8}
            />
          </svg>

          {/* Centered Node Count */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
            }}
          >
            <span className="mono" style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
              {totalNodes}
            </span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginTop: '2px' }}>
              Nodes
            </span>
          </div>
        </div>

        {/* Legend Metrics List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', flex: 1, minWidth: 140 }}>
          {/* CPU Allocation */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.76rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ff334b', flexShrink: 0 }} />
              <span style={{ color: 'var(--text-secondary)' }}>CPU ({usedCpuCores}/{totalCpuCores})</span>
            </div>
            <span className="mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
              {cpuPct}%
            </span>
          </div>

          {/* RAM Allocation */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.76rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#a855f7', flexShrink: 0 }} />
              <span style={{ color: 'var(--text-secondary)' }}>RAM ({usedRamGb}/{totalRamGb} GB)</span>
            </div>
            <span className="mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
              {ramPct}%
            </span>
          </div>

          {/* Slots Allocation */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.76rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#06b6d4', flexShrink: 0 }} />
              <span style={{ color: 'var(--text-secondary)' }}>Slots ({activeSlots}/{totalSlots})</span>
            </div>
            <span className="mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
              {slotsPct}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
