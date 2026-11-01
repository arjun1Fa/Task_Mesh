import React, { useState } from 'react'
import { PlusCircle, Cpu, Layers, Zap, X } from 'lucide-react'
import { api } from '../api/client'

interface SubmitTaskModalProps {
  isOpen: boolean
  onClose: () => void
  onTaskSubmitted: () => void
}

export const SubmitTaskModal: React.FC<SubmitTaskModalProps> = ({
  isOpen,
  onClose,
  onTaskSubmitted,
}) => {
  const [taskType, setTaskType] = useState('benchmark')
  const [priority, setPriority] = useState(5)
  const [offloadPolicy, setOffloadPolicy] = useState('remote_allowed')
  const [requiresGpu, setRequiresGpu] = useState(false)
  const [requiredMemoryMb, setRequiredMemoryMb] = useState(512)
  const [payloadText, setPayloadText] = useState(
    JSON.stringify({ matrix_size: 500, iterations: 5 }, null, 2)
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleTaskTypeChange = (type: string) => {
    setTaskType(type)
    if (type === 'benchmark') {
      setPayloadText(JSON.stringify({ matrix_size: 500, iterations: 5 }, null, 2))
      setRequiresGpu(false)
    } else if (type === 'object_detection' || type === 'yolo_inference') {
      setPayloadText(JSON.stringify({ confidence_threshold: 0.5, model: 'yolov8n' }, null, 2))
      setRequiresGpu(true)
    } else if (type === 'echo') {
      setPayloadText(JSON.stringify({ message: 'Hello from TaskMesh control console' }, null, 2))
      setRequiresGpu(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      setSubmitting(true)
      let parsedPayload = {}
      try {
        parsedPayload = JSON.parse(payloadText)
      } catch (err) {
        throw new Error('Payload must be valid JSON')
      }

      await api.submitTask({
        task_type: taskType,
        payload: parsedPayload,
        priority,
        offload_policy: offloadPolicy,
        requires_gpu: requiresGpu,
        required_memory_mb: requiredMemoryMb,
      })

      onTaskSubmitted()
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to submit task')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <PlusCircle size={18} color="var(--accent-blue)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Submit Workload to TaskMesh</h3>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                Adaptive Multi-Node Dispatch
              </p>
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
                  padding: '0.6rem 0.8rem',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '1rem',
                  color: 'var(--status-failed)',
                  fontSize: '0.8rem',
                }}
              >
                {error}
              </div>
            )}

            <div className="grid grid-2" style={{ gap: '0.75rem', marginBottom: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Task Type</label>
                <select
                  className="form-input"
                  value={taskType}
                  onChange={(e) => handleTaskTypeChange(e.target.value)}
                >
                  <option value="benchmark">CPU Benchmark (Matrix Math)</option>
                  <option value="object_detection">AI Inference (YOLOv8n)</option>
                  <option value="echo">Echo (Diagnostic Round-trip)</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Priority (1-10)</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  className="form-input"
                  value={priority}
                  onChange={(e) => setPriority(parseInt(e.target.value) || 5)}
                />
              </div>
            </div>

            <div className="grid grid-2" style={{ gap: '0.75rem', marginBottom: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Offload Policy</label>
                <select
                  className="form-input"
                  value={offloadPolicy}
                  onChange={(e) => setOffloadPolicy(e.target.value)}
                >
                  <option value="remote_allowed">Remote Allowed (Full Cluster)</option>
                  <option value="wireless_allowed">Wireless Channels Allowed</option>
                  <option value="local_only">Local Only</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Required RAM (MB)</label>
                <input
                  type="number"
                  min={64}
                  step={64}
                  className="form-input"
                  value={requiredMemoryMb}
                  onChange={(e) => setRequiredMemoryMb(parseInt(e.target.value) || 256)}
                />
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                <input
                  type="checkbox"
                  checked={requiresGpu}
                  onChange={(e) => setRequiresGpu(e.target.checked)}
                />
                <span>Requires GPU Acceleration (CUDA / DirectML)</span>
              </label>
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <label className="form-label" style={{ margin: 0 }}>Task Payload (JSON)</label>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Arguments passed to worker</span>
              </div>
              <textarea
                className="form-input code-font"
                rows={4}
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                style={{ resize: 'vertical', fontSize: '0.8rem' }}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Dispatch Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

