/* TaskMesh Cybernetic Mesh Wave Footer Graphic */
import React from 'react'

export const CyberneticMeshWave: React.FC = () => {
  return (
    <div
      style={{
        width: '100%',
        height: 64,
        position: 'relative',
        overflow: 'hidden',
        marginTop: '1.5rem',
        opacity: 0.85,
        pointerEvents: 'none',
      }}
    >
      <svg
        width="100%"
        height="64"
        viewBox="0 0 1200 64"
        preserveAspectRatio="none"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="waveRedGlow" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ff334b" stopOpacity="0.1" />
            <stop offset="25%" stopColor="#ff334b" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#ff4d63" stopOpacity="0.95" />
            <stop offset="75%" stopColor="#a855f7" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#ff334b" stopOpacity="0.15" />
          </linearGradient>

          <linearGradient id="waveFillGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ff334b" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#ff334b" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Ambient bottom red mesh glow */}
        <path
          d="M 0 45 C 150 15, 300 60, 450 30 C 600 0, 750 50, 900 25 C 1050 5, 1150 40, 1200 35 L 1200 64 L 0 64 Z"
          fill="url(#waveFillGrad)"
        />

        {/* Dense glowing wireframe sine waves */}
        <path
          d="M 0 52 C 160 22, 320 62, 480 32 C 640 5, 800 52, 960 26 C 1080 8, 1160 38, 1200 34"
          stroke="url(#waveRedGlow)"
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        <path
          d="M 0 48 C 140 32, 280 58, 420 38 C 580 16, 740 48, 900 28 C 1040 12, 1140 42, 1200 38"
          stroke="#ff334b"
          strokeWidth="1.2"
          strokeOpacity="0.65"
          strokeDasharray="4 3"
        />

        <path
          d="M 0 42 C 180 12, 360 52, 540 22 C 720 -2, 900 42, 1080 18 C 1140 8, 1180 26, 1200 24"
          stroke="#ff4d63"
          strokeWidth="1"
          strokeOpacity="0.45"
        />

        <path
          d="M 0 58 C 200 36, 400 56, 600 40 C 800 22, 1000 46, 1200 42"
          stroke="#a855f7"
          strokeWidth="1"
          strokeOpacity="0.35"
        />
      </svg>
    </div>
  )
}
