import React from 'react'

export const IsometricClusterMesh: React.FC<{ size?: number }> = ({ size = 160 }) => {
  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Radial Red Glow */}
          <radialGradient id="meshGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ff334b" stopOpacity="0.5" />
            <stop offset="60%" stopColor="#ff334b" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#ff334b" stopOpacity="0" />
          </radialGradient>

          {/* Central Cube Gradients */}
          <linearGradient id="cubeTop" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2c1a24" />
            <stop offset="100%" stopColor="#15121b" />
          </linearGradient>
          <linearGradient id="cubeLeft" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1e131d" />
            <stop offset="100%" stopColor="#0d0b13" />
          </linearGradient>
          <linearGradient id="cubeRight" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#2a1420" />
            <stop offset="100%" stopColor="#110c16" />
          </linearGradient>

          {/* Satellite Cube Gradients */}
          <linearGradient id="satTop" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#251622" />
            <stop offset="100%" stopColor="#131018" />
          </linearGradient>
        </defs>

        {/* Outer Glow Halo Ring */}
        <circle cx="100" cy="115" r="75" fill="url(#meshGlow)" />
        <ellipse cx="100" cy="118" rx="68" ry="24" stroke="#ff334b" strokeWidth="1.2" strokeOpacity="0.5" strokeDasharray="4 3" />
        <ellipse cx="100" cy="118" rx="52" ry="18" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.75" />

        {/* Orbit Connection Rays */}
        <line x1="100" y1="110" x2="38" y2="92" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="3 3" />
        <line x1="100" y1="110" x2="162" y2="92" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="3 3" />
        <line x1="100" y1="110" x2="65" y2="135" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="3 3" />
        <line x1="100" y1="110" x2="138" y2="138" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="3 3" />

        {/* SATELLITE NODE 1 (Left Top) */}
        <g transform="translate(24, 75) scale(0.55)">
          <polygon points="25,0 50,14 25,28 0,14" fill="url(#satTop)" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
          <polygon points="0,14 25,28 25,56 0,42" fill="url(#cubeLeft)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <polygon points="25,28 50,14 50,42 25,56" fill="url(#cubeRight)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          {/* LED lights */}
          <line x1="5" y1="22" x2="20" y2="30" stroke="#06b6d4" strokeWidth="1.5" strokeOpacity="0.8" />
          <line x1="5" y1="30" x2="20" y2="38" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
        </g>

        {/* SATELLITE NODE 2 (Right Top) */}
        <g transform="translate(150, 75) scale(0.55)">
          <polygon points="25,0 50,14 25,28 0,14" fill="url(#satTop)" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
          <polygon points="0,14 25,28 25,56 0,42" fill="url(#cubeLeft)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <polygon points="25,28 50,14 50,42 25,56" fill="url(#cubeRight)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <line x1="5" y1="22" x2="20" y2="30" stroke="#10b981" strokeWidth="1.5" strokeOpacity="0.8" />
          <line x1="5" y1="30" x2="20" y2="38" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
        </g>

        {/* SATELLITE NODE 3 (Left Bottom) */}
        <g transform="translate(50, 122) scale(0.52)">
          <polygon points="25,0 50,14 25,28 0,14" fill="url(#satTop)" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
          <polygon points="0,14 25,28 25,56 0,42" fill="url(#cubeLeft)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <polygon points="25,28 50,14 50,42 25,56" fill="url(#cubeRight)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <line x1="5" y1="22" x2="20" y2="30" stroke="#a855f7" strokeWidth="1.5" strokeOpacity="0.8" />
        </g>

        {/* SATELLITE NODE 4 (Right Bottom) */}
        <g transform="translate(126, 124) scale(0.52)">
          <polygon points="25,0 50,14 25,28 0,14" fill="url(#satTop)" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
          <polygon points="0,14 25,28 25,56 0,42" fill="url(#cubeLeft)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <polygon points="25,28 50,14 50,42 25,56" fill="url(#cubeRight)" stroke="#ff334b" strokeWidth="1" strokeOpacity="0.5" />
          <line x1="5" y1="22" x2="20" y2="30" stroke="#ff334b" strokeWidth="1.5" strokeOpacity="0.8" />
        </g>

        {/* MAIN PRIMARY ORCHESTRATOR ISOMETRIC CUBE */}
        <g transform="translate(72, 45)">
          {/* Top Diamond Face */}
          <polygon points="28,0 56,16 28,32 0,16" fill="url(#cubeTop)" stroke="#ff334b" strokeWidth="2" />

          {/* Left Vertical Face */}
          <polygon points="0,16 28,32 28,72 0,56" fill="url(#cubeLeft)" stroke="#ff334b" strokeWidth="1.5" />

          {/* Right Vertical Face */}
          <polygon points="28,32 56,16 56,56 28,72" fill="url(#cubeRight)" stroke="#ff334b" strokeWidth="1.5" />

          {/* Top Face Emblem */}
          <path
            d="M 28 8 L 44 17 L 28 26 L 12 17 Z"
            fill="none"
            stroke="#ff334b"
            strokeWidth="1.5"
            strokeOpacity="0.8"
          />
          <circle cx="28" cy="17" r="3" fill="#ff334b" />

          {/* Left Face Server Rack Slots */}
          <line x1="5" y1="26" x2="23" y2="36" stroke="#ff334b" strokeWidth="1.8" strokeOpacity="0.9" />
          <line x1="5" y1="36" x2="23" y2="46" stroke="#ff334b" strokeWidth="1.8" strokeOpacity="0.9" />
          <line x1="5" y1="46" x2="23" y2="56" stroke="#ff334b" strokeWidth="1.8" strokeOpacity="0.9" />

          {/* Right Face LED Indicators */}
          <circle cx="34" cy="38" r="1.8" fill="#10b981" />
          <circle cx="40" cy="35" r="1.8" fill="#06b6d4" />
          <circle cx="46" cy="32" r="1.8" fill="#ff334b" />

          <circle cx="34" cy="48" r="1.8" fill="#ff334b" />
          <circle cx="40" cy="45" r="1.8" fill="#10b981" />
          <circle cx="46" cy="42" r="1.8" fill="#a855f7" />

          <circle cx="34" cy="58" r="1.8" fill="#10b981" />
          <circle cx="40" cy="55" r="1.8" fill="#10b981" />
          <circle cx="46" cy="52" r="1.8" fill="#06b6d4" />
        </g>
      </svg>
    </div>
  )
}
