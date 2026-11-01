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
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                backgroundColor: danger ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={18} color={danger ? 'var(--status-failed)' : 'var(--status-degraded)'} />
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{title}</h3>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onCancel} disabled={loading}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: '1.45' }}>{message}</p>

          {affectedComponents.length > 0 && (
            <div
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.75rem',
              }}
            >
              <div
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: 'var(--text-dim)',
                  marginBottom: '0.4rem',
                }}
              >
                Directly Affected Components
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-color)' }}>
                {affectedComponents.map((c, idx) => (
                  <li key={idx} style={{ marginBottom: '0.2rem' }}>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {danger && (
            <div
              style={{
                padding: '0.6rem 0.8rem',
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.75rem',
                color: 'var(--status-failed)',
              }}
            >
              <strong>Caution:</strong> This operation changes runtime scheduling or operational availability.
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary btn-sm" onClick={onCancel} disabled={loading}>
            {cancelText}
          </button>
          <button
            className={`btn btn-sm ${danger ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Executing...' : buttonLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

