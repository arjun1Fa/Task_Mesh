import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface ConfirmationModalProps {
  isOpen: boolean
  title: string
  message: string
  affectedComponents?: string[]
  confirmText?: string
  confirmLabel?: string
  cancelText?: string
  isDangerous?: boolean
  isDanger?: boolean
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  title,
  message,
  affectedComponents = [],
  confirmText,
  confirmLabel,
  cancelText = 'Cancel',
  isDangerous = false,
  isDanger = false,
  loading = false,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null
  const danger = isDangerous || isDanger
  const buttonLabel = confirmLabel || confirmText || 'Confirm'

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              backgroundColor: isDangerous ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <AlertTriangle size={18} color={isDangerous ? 'var(--accent-rose)' : 'var(--accent-amber)'} />
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{title}</h3>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onCancel}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '1rem' }}>
            {message}
          </p>

          {affectedComponents.length > 0 && (
            <div style={{
              backgroundColor: 'rgba(0, 0, 0, 0.25)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-main)',
            }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                Affected Subsystems & Components:
              </div>
              <ul style={{ paddingLeft: '1.2rem', fontSize: '0.82rem', color: 'var(--text-main)' }}>
                {affectedComponents.map((comp, i) => (
                  <li key={i}>{comp}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>
            {cancelText}
          </button>
          <button
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Processing...' : buttonLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
