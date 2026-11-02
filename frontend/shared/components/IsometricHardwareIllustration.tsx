import React from 'react'

export const IsometricHardwareIllustration: React.FC<{ size?: number }> = ({ size = 150 }) => {
  return (
    <div style={{ position: 'relative', width: size, height: size * 0.75, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg
        width={size}
        height={size * 0.75}
        viewBox="0 0 160 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <radialGradient id="hwRedGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ff334b" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#ff334b" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="laptopScreen" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1a0f16" />
            <stop offset="100%" stopColor="#08070b" />
          </linearGradient>
          <linearGradient id="laptopBase" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#251622" />
            <stop offset="100%" stopColor="#0f0c14" />
          </linearGradient>
        </defs>

        {/* Red Ambient Ground Projection */}
        <ellipse cx="90" cy="90" rx="60" ry="20" fill="url(#hwRedGlow)" />

        {/* Isometric Laptop Base / Keyboard Deck */}
        <polygon
          points="80,72 135,88 95,108 40,92"
          fill="url(#laptopBase)"
          stroke="#ff334b"
          strokeWidth="1.4"
        />
        {/* Trackpad */}
        <polygon
          points="80,94 95,98 86,104 71,100"
          fill="rgba(255, 51, 75, 0.15)"
          stroke="#ff334b"
          strokeWidth="0.8"
          strokeOpacity="0.6"
        />

        {/* Laptop Screen Display (Tilted) */}
        <polygon
          points="80,24 135,40 135,88 80,72"
          fill="url(#laptopScreen)"
          stroke="#ff334b"
          strokeWidth="1.5"
        />
        {/* Screen Inset Content */}
        <polygon
          points="85,32 130,45 130,82 85,69"
          fill="#0c0a10"
          stroke="#ff334b"
          strokeWidth="0.8"
          strokeOpacity="0.4"
        />

        {/* TaskMesh Stack Icon on Screen */}
        <g transform="translate(100, 48) scale(0.6)">
          <polygon points="15,0 30,8 15,16 0,8" fill="rgba(255, 51, 75, 0.3)" stroke="#ff334b" strokeWidth="1.5" />
          <polygon points="15,8 30,16 15,24 0,16" fill="rgba(255, 51, 75, 0.2)" stroke="#ff334b" strokeWidth="1.5" />
          <polygon points="15,16 30,24 15,32 0,24" fill="rgba(255, 51, 75, 0.1)" stroke="#ff334b" strokeWidth="1.5" />
        </g>
      </svg>
    </div>
  )
}
