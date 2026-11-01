import React, { useState } from 'react'
import { Shield, X, AlertCircle } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

interface LoginModalProps {
  isOpen: boolean
  onClose: () => void
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const { login } = useAuth()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(username, password)
      onClose()
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '420px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(6, 182, 212, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Shield size={18} color="var(--accent-cyan)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Authenticate to TaskMesh</h3>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Orchestrator RBAC</p>
            </div>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.6rem 0.8rem',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '1rem',
                  color: 'var(--status-failed)',
                  fontSize: '0.8rem',
                }}
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                type="text"
                className="form-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin, operator, or viewer"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                marginTop: '0.75rem',
                backgroundColor: 'var(--bg-surface-elevated)',
                padding: '0.65rem 0.85rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-main)',
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.45rem' }}>
                One-Click Role Authentication:
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.7rem', padding: '0.2rem 0.6rem' }}
                  onClick={async () => {
                    setUsername('admin')
                    setPassword('admin123')
                    setIsSubmitting(true)
                    setError(null)
                    try {
                      await login('admin', 'admin123')
                      onClose()
                    } catch (err: any) {
                      setError(err.message || 'Login failed')
                    } finally {
                      setIsSubmitting(false)
                    }
                  }}
                  disabled={isSubmitting}
                >
                  <Shield size={12} color="var(--accent-blue)" />
                  <span>Sign In as Admin</span>
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.7rem', padding: '0.2rem 0.6rem' }}
                  onClick={async () => {
                    setUsername('operator')
                    setPassword('operator123')
                    setIsSubmitting(true)
                    setError(null)
                    try {
                      await login('operator', 'operator123')
                      onClose()
                    } catch (err: any) {
                      setError(err.message || 'Login failed')
                    } finally {
                      setIsSubmitting(false)
                    }
                  }}
                  disabled={isSubmitting}
                >
                  <Shield size={12} color="var(--accent-purple)" />
                  <span>Sign In as Operator</span>
                </button>
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                Or manually enter custom credentials or cluster service tokens configured in your deployment.
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={isSubmitting}>
              {isSubmitting ? 'Authenticating...' : 'Sign In'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

