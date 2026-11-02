import React, { useState, useEffect } from 'react'

interface ResourceHistoryPoint {
  time: string
  cpu: number
  ram: number
}

interface ClusterResourceUtilizationProps {
  currentCpu: number
  currentRam: number
}

export const ClusterResourceUtilization: React.FC<ClusterResourceUtilizationProps> = ({
  currentCpu,
  currentRam,
}) => {
  const [history, setHistory] = useState<ResourceHistoryPoint[]>([])

  useEffect(() => {
    // Generate initial realistic curve history if empty
    const now = Date.now()
    const initialPoints: ResourceHistoryPoint[] = []
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now - i * 5 * 60 * 1000)
      const timeStr = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
      // gentle wave fluctuation around current values
      const cpuOffset = Math.sin(i * 1.2) * 15
      const ramOffset = Math.cos(i * 0.9) * 10
      initialPoints.push({
        time: timeStr,
        cpu: Math.min(95, Math.max(10, (currentCpu || 45) + cpuOffset)),
        ram: Math.min(95, Math.max(20, (currentRam || 65) + ramOffset)),
      })
    }
    setHistory(initialPoints)
  }, [])

  useEffect(() => {
    // Periodic live update with latest telemetry
    const d = new Date()
    const timeStr = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    setHistory((prev) => {
      if (prev.length === 0) return prev
      const updated = [...prev.slice(1), { time: timeStr, cpu: currentCpu, ram: currentRam }]
      return updated
    })
  }, [currentCpu, currentRam])

  // SVG Chart Dimensions
  const width = 460
  const height = 150
  const padLeft = 36
  const padBottom = 26
  const chartW = width - padLeft - 10
  const chartH = height - padBottom - 10

  const getPoints = (key: 'cpu' | 'ram') => {
    if (history.length < 2) return ''
    return history
      .map((pt, idx) => {
        const x = padLeft + (idx / (history.length - 1)) * chartW
        const y = 10 + chartH - (pt[key] / 100) * chartH
        return `${x},${y}`
      })
      .join(' ')
  }

  const getAreaPath = (key: 'cpu' | 'ram') => {
    if (history.length < 2) return ''
    const points = history.map((pt, idx) => {
      const x = padLeft + (idx / (history.length - 1)) * chartW
      const y = 10 + chartH - (pt[key] / 100) * chartH
      return { x, y }
    })

    let d = `M ${points[0].x} ${points[0].y}`
    for (let i = 1; i < points.length; i++) {
      // Smooth bezier curves
      const prev = points[i - 1]
      const curr = points[i]
      const cpX1 = prev.x + (curr.x - prev.x) / 2
      const cpY1 = prev.y
      const cpX2 = prev.x + (curr.x - prev.x) / 2
      const cpY2 = curr.y
      d += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${curr.x} ${curr.y}`
    }
    // Close bottom
    const last = points[points.length - 1]
    d += ` L ${last.x} ${10 + chartH} L ${points[0].x} ${10 + chartH} Z`
    return d
  }

  const getSmoothLine = (key: 'cpu' | 'ram') => {
    if (history.length < 2) return ''
    const points = history.map((pt, idx) => {
      const x = padLeft + (idx / (history.length - 1)) * chartW
      const y = 10 + chartH - (pt[key] / 100) * chartH
      return { x, y }
    })

    let d = `M ${points[0].x} ${points[0].y}`
    for (let i = 1; i < points.length; i++) {
      const prev = points[i - 1]
      const curr = points[i]
      const cpX1 = prev.x + (curr.x - prev.x) / 2
      const cpY1 = prev.y
      const cpX2 = prev.x + (curr.x - prev.x) / 2
      const cpY2 = curr.y
      d += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${curr.x} ${curr.y}`
    }
    return d
  }

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Legend & Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
        <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
          Cluster Resource Utilization
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.76rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ff334b', display: 'inline-block' }} />
            <span style={{ color: 'var(--text-secondary)' }}>CPU ({currentCpu}%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#a855f7', display: 'inline-block' }} />
            <span style={{ color: 'var(--text-secondary)' }}>RAM ({currentRam}%)</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div style={{ width: '100%', position: 'relative' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
        >
          <defs>
            {/* CPU Neon Red Area Gradient */}
            <linearGradient id="cpuGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ff334b" stopOpacity="0.38" />
              <stop offset="100%" stopColor="#ff334b" stopOpacity="0.0" />
            </linearGradient>

            {/* RAM Violet Area Gradient */}
            <linearGradient id="ramGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#a855f7" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Horizontal Gridlines & Y-Axis Labels */}
          {[100, 75, 50, 25, 0].map((val) => {
            const y = 10 + chartH - (val / 100) * chartH
            return (
              <g key={val}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - 10}
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.05)"
                  strokeWidth="1"
                  strokeDasharray={val === 0 ? undefined : '2 3'}
                />
                <text
                  x={padLeft - 6}
                  y={y + 3}
                  textAnchor="end"
                  fill="#64748b"
                  fontSize="8.5"
                  fontFamily="var(--font-mono)"
                >
                  {val}%
                </text>
              </g>
            )
          })}

          {/* RAM Area & Stroke (Violet) */}
          <path d={getAreaPath('ram')} fill="url(#ramGrad)" />
          <path
            d={getSmoothLine('ram')}
            fill="none"
            stroke="#a855f7"
            strokeWidth="2"
            strokeLinecap="round"
          />

          {/* CPU Area & Stroke (Neon Red) */}
          <path d={getAreaPath('cpu')} fill="url(#cpuGrad)" />
          <path
            d={getSmoothLine('cpu')}
            fill="none"
            stroke="#ff334b"
            strokeWidth="2.2"
            strokeLinecap="round"
          />

          {/* Time Labels on X-Axis */}
          {history.map((pt, idx) => {
            const x = padLeft + (idx / (history.length - 1)) * chartW
            return (
              <text
                key={idx}
                x={x}
                y={height - 6}
                textAnchor="middle"
                fill="#64748b"
                fontSize="8.5"
                fontFamily="var(--font-mono)"
              >
                {pt.time}
              </text>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
