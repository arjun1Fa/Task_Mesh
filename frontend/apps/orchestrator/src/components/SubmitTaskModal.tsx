import React, { useState, useEffect, useRef } from 'react'
import {
  PlusCircle,
  Cpu,
  Layers,
  Zap,
  X,
  CheckCircle2,
  Copy,
  Check,
  Clock,
  ArrowRight,
  Shield,
  Activity,
  AlertCircle,
  Upload,
  Image as ImageIcon,
  Palette,
  Sliders,
  Trash2,
} from 'lucide-react'
import { api } from '../api/client'
import type { Task } from '@shared/types'

interface SubmitTaskModalProps {
  isOpen: boolean
  onClose: () => void
  onTaskSubmitted: () => void
  onNavigateToTasks?: () => void
}

export const SubmitTaskModal: React.FC<SubmitTaskModalProps> = ({
  isOpen,
  onClose,
  onTaskSubmitted,
  onNavigateToTasks,
}) => {
  const [taskType, setTaskType] = useState('cpu_test')
  const [priority, setPriority] = useState(5)
  const [offloadPolicy, setOffloadPolicy] = useState('remote_allowed')
  const [timeoutSeconds, setTimeoutSeconds] = useState(60.0)
  const [requiresGpu, setRequiresGpu] = useState(false)
  const [requiredMemoryMb, setRequiredMemoryMb] = useState(256)

  // Workload-specific config states
  const [cpuIterations, setCpuIterations] = useState(5000000)
  const [matrixDim, setMatrixDim] = useState(64)
  const [logMessage, setLogMessage] = useState('TaskMesh production test message')
  const [sleepDuration, setSleepDuration] = useState(1.0)
  const [aiModel, setAiModel] = useState('yolov8n')
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null)
  const [imageMeta, setImageMeta] = useState<{ width: number; height: number; sizeBytes: number } | null>(null)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.25)
  const [paletteSize, setPaletteSize] = useState(8)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      processFile(file)
    }
  }

  const processFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file (JPEG or PNG)')
      return
    }
    if (file.size > 25 * 1024 * 1024) {
      setError('Image file must be under 25 MB')
      return
    }
    setError(null)
    setSelectedImageFile(file)
    const url = URL.createObjectURL(file)
    setImagePreviewUrl(url)
    const img = new Image()
    img.onload = () => {
      setImageMeta({ width: img.naturalWidth, height: img.naturalHeight, sizeBytes: file.size })
    }
    img.src = url
  }

  const clearSelectedImage = () => {
    setSelectedImageFile(null)
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl)
    }
    setImagePreviewUrl(null)
    setImageMeta(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const [payloadText, setPayloadText] = useState('')
  const [customPayloadMode, setCustomPayloadMode] = useState(false)

  const [availableHandlers, setAvailableHandlers] = useState<string[]>([
    'cpu_test',
    'image_inference',
    'matrix_multiply',
    'echo',
    'sleep',
    'log',
  ])

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submittedTask, setSubmittedTask] = useState<Task | null>(null)
  const [copiedId, setCopiedId] = useState(false)

  // Fetch registered handlers from backend on open
  useEffect(() => {
    if (isOpen) {
      setSubmittedTask(null)
      setError(null)
      api.getSupportedHandlers()
        .then((res) => {
          if (res.supported_handlers && res.supported_handlers.length > 0) {
            setAvailableHandlers(res.supported_handlers)
          }
        })
        .catch(() => {
          // Keep defaults
        })
    }
  }, [isOpen])

  // Sync payload when inputs change
  useEffect(() => {
    if (!customPayloadMode) {
      let p: Record<string, any> = {}
      if (taskType === 'cpu_test') {
        p = { iterations: cpuIterations }
      } else if (taskType === 'matrix_multiply') {
        p = { dim: matrixDim }
      } else if (taskType === 'image_inference') {
        p = { model: aiModel, batch_size: 1 }
      } else if (taskType === 'log') {
        p = { message: logMessage }
      } else if (taskType === 'echo') {
        p = { message: logMessage, echo_timestamp: Date.now() }
      } else if (taskType === 'sleep') {
        p = { duration: sleepDuration }
      }
      setPayloadText(JSON.stringify(p, null, 2))
    }
  }, [taskType, cpuIterations, matrixDim, logMessage, sleepDuration, aiModel, customPayloadMode])

  if (!isOpen) return null

  const handleTaskTypeChange = (type: string) => {
    setTaskType(type)
    setCustomPayloadMode(false)
    if (type === 'image_inference') {
      setRequiresGpu(false)
      setRequiredMemoryMb(512)
    } else if (type === 'cpu_test') {
      setRequiresGpu(false)
      setRequiredMemoryMb(256)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (priority < 1 || priority > 10) {
      setError('Priority must be between 1 and 10')
      return
    }
    if (timeoutSeconds <= 0) {
      setError('Timeout must be greater than 0 seconds')
      return
    }

    if (taskType === 'image_inference') {
      if (!selectedImageFile) {
        setError('Please select or upload an image file (JPEG or PNG) for YOLO colour analysis')
        return
      }
      try {
        setSubmitting(true)
        const formData = new FormData()
        formData.append('file', selectedImageFile)
        formData.append('model', aiModel)
        formData.append('confidence_threshold', confidenceThreshold.toString())
        formData.append('palette_size', paletteSize.toString())
        formData.append('priority', priority.toString())
        formData.append('offload_policy', offloadPolicy)
        formData.append('requires_gpu', requiresGpu ? 'true' : 'false')

        const created = await api.submitBinaryTask(formData)
        setSubmittedTask(created)
        onTaskSubmitted()
      } catch (err: any) {
        setError(err.message || 'Failed to submit binary image workload to cluster')
      } finally {
        setSubmitting(false)
      }
      return
    }

    if (taskType === 'cpu_test' && (!cpuIterations || cpuIterations < 1)) {
      setError('Iterations count must be an integer greater than 0')
      return
    }

    let parsedPayload: Record<string, any> = {}
    try {
      parsedPayload = JSON.parse(payloadText)
    } catch {
      setError('Payload must be valid JSON syntax')
      return
    }

    try {
      setSubmitting(true)
      const created = await api.submitTask({
        task_type: taskType,
        payload: parsedPayload,
        priority,
        offload_policy: offloadPolicy,
        requires_gpu: requiresGpu,
        required_memory_mb: requiredMemoryMb,
      })

      setSubmittedTask(created)
      onTaskSubmitted()
    } catch (err: any) {
      setError(err.message || 'Failed to submit task to cluster')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCopyId = () => {
    if (submittedTask) {
      navigator.clipboard.writeText(submittedTask.id)
      setCopiedId(true)
      setTimeout(() => setCopiedId(false), 2000)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 1100 }}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '580px', width: '95%' }}>
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
                Multi-Node Cluster Scheduling & Dispatch
              </p>
            </div>
          </div>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {submittedTask ? (
          /* Submission Confirmation Screen */
          <div className="modal-body" style={{ padding: '1.5rem', textAlign: 'center' }}>
            <div
              style={{
                width: 54,
                height: 54,
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem',
              }}
            >
              <CheckCircle2 size={32} color="var(--accent-green)" />
            </div>

            <h4 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.35rem' }}>
              Workload Successfully Dispatched
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', maxWidth: '420px', margin: '0 auto 1.25rem' }}>
              Task registered to cluster priority queue. The adaptive scheduler will allocate an eligible worker node automatically.
            </p>

            <div
              style={{
                backgroundColor: 'var(--bg-main)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.85rem 1rem',
                textAlign: 'left',
                marginBottom: '1.5rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Generated Task ID:</span>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={handleCopyId}
                  style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem' }}
                >
                  {copiedId ? <Check size={12} color="var(--accent-green)" /> : <Copy size={12} />}
                  <span>{copiedId ? 'Copied' : 'Copy ID'}</span>
                </button>
              </div>
              <div className="mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {submittedTask.id}
              </div>

              <div className="grid grid-3" style={{ gap: '0.5rem', marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
                <div>
                  <span style={{ color: 'var(--text-dim)' }}>Type: </span>
                  <span className="badge badge-blue">{submittedTask.task_type}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)' }}>Priority: </span>
                  <span className="mono" style={{ fontWeight: 600 }}>P{submittedTask.priority}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)' }}>Status: </span>
                  <span className={`status-pill ${submittedTask.status}`}>{submittedTask.status}</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setSubmittedTask(null)
                  setError(null)
                }}
              >
                Submit Another Workload
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  onClose()
                  if (onNavigateToTasks) onNavigateToTasks()
                }}
              >
                <span>View in Task Queue</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        ) : (
          /* Submission Form */
          <form onSubmit={handleSubmit}>
            <div className="modal-body" style={{ maxHeight: '75vh', overflowY: 'auto' }}>
              {error && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.65rem 0.85rem',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: '1rem',
                    color: 'var(--status-failed)',
                    fontSize: '0.8rem',
                  }}
                >
                  <AlertCircle size={16} style={{ flexShrink: 0 }} />
                  <span>{error}</span>
                </div>
              )}

              {/* Task Type & Priority */}
              <div className="grid grid-2" style={{ gap: '0.75rem', marginBottom: '1rem' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Task Type / Handler</label>
                  <select
                    className="form-input"
                    value={taskType}
                    onChange={(e) => handleTaskTypeChange(e.target.value)}
                  >
                    {availableHandlers.map((h) => (
                      <option key={h} value={h}>
                        {h === 'cpu_test'
                          ? 'CPU Test (Math Benchmark)'
                          : h === 'image_inference'
                          ? 'Image Colour Analysis (YOLOv8 + OpenCV)'
                          : h === 'matrix_multiply'
                          ? 'Matrix Multiply (Square Matrix)'
                          : h === 'echo'
                          ? 'Echo (Payload Verification)'
                          : h === 'sleep'
                          ? 'Sleep (Async Delay)'
                          : h === 'log'
                          ? 'Log (System Event)'
                          : h}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Priority (1 = Low, 10 = Urgent)</label>
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

              {/* Dynamic Inputs based on taskType */}
              {taskType === 'cpu_test' && (
                <div
                  style={{
                    backgroundColor: 'rgba(56, 189, 248, 0.05)',
                    border: '1px solid rgba(56, 189, 248, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.85rem',
                    marginBottom: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
                    <Cpu size={15} color="var(--accent-cyan)" />
                    <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                      CPU Math Workload Parameters
                    </span>
                  </div>

                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Computation Iteration Count</label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        type="number"
                        min={1000}
                        step={50000}
                        className="form-input"
                        value={cpuIterations}
                        onChange={(e) => setCpuIterations(parseInt(e.target.value) || 50000)}
                      />
                      <button
                        type="button"
                        className={`btn btn-sm ${cpuIterations === 5000000 ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setCpuIterations(5000000)}
                        style={{ fontSize: '0.72rem', whiteSpace: 'nowrap' }}
                      >
                        5,000,000 Iterations
                      </button>
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                      Executes math checksum calculation: &Sigma; &radic;i &bull; sin(i) in worker thread pool.
                    </span>
                  </div>
                </div>
              )}

              {taskType === 'matrix_multiply' && (
                <div
                  style={{
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    border: '1px solid rgba(168, 85, 247, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.85rem',
                    marginBottom: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
                    <Zap size={15} color="var(--accent-purple)" />
                    <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-purple)' }}>
                      Matrix Multiplication Parameters
                    </span>
                  </div>

                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Square Matrix Dimension (N &times; N)</label>
                    <select
                      className="form-input"
                      value={matrixDim}
                      onChange={(e) => setMatrixDim(parseInt(e.target.value) || 64)}
                    >
                      <option value={32}>32 &times; 32 (Lightweight)</option>
                      <option value={64}>64 &times; 64 (Standard Benchmark)</option>
                      <option value={128}>128 &times; 128 (Heavy Compute)</option>
                      <option value={256}>256 &times; 256 (Stress Test)</option>
                    </select>
                  </div>
                </div>
              )}

              {taskType === 'image_inference' && (
                <div
                  style={{
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.85rem',
                    marginBottom: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
                    <Activity size={15} color="var(--accent-green)" />
                    <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-green)' }}>
                      Computer Vision & Colour Analysis Workload
                    </span>
                  </div>

                  {/* Image Upload Dropzone */}
                  <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                    <label className="form-label">Input Image (JPEG or PNG, Max 25 MB)</label>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/jpeg,image/png,image/jpg"
                      onChange={handleFileChange}
                      style={{ display: 'none' }}
                    />

                    {imagePreviewUrl ? (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem',
                          padding: '0.65rem',
                          backgroundColor: 'var(--bg-main)',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <img
                          src={imagePreviewUrl}
                          alt="Input preview"
                          style={{
                            width: 64,
                            height: 64,
                            objectFit: 'cover',
                            borderRadius: 'var(--radius-xs)',
                            border: '1px solid var(--border-color)',
                          }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: '0.82rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {selectedImageFile?.name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                            {imageMeta ? `${imageMeta.width} × ${imageMeta.height} px • ` : ''}
                            {selectedImageFile ? `${(selectedImageFile.size / 1024).toFixed(1)} KB` : ''}
                          </div>
                          <div style={{ display: 'flex', gap: '0.4rem', marginTop: '4px' }}>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => fileInputRef.current?.click()}
                              style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                            >
                              Replace Image
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={clearSelectedImage}
                              style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem', color: 'var(--status-failed)' }}
                            >
                              <Trash2 size={11} style={{ marginRight: 3 }} />
                              Remove
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div
                        onClick={() => fileInputRef.current?.click()}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => {
                          e.preventDefault()
                          if (e.dataTransfer.files?.[0]) processFile(e.dataTransfer.files[0])
                        }}
                        style={{
                          border: '2px dashed rgba(16, 185, 129, 0.4)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '1.25rem 1rem',
                          textAlign: 'center',
                          cursor: 'pointer',
                          backgroundColor: 'rgba(0, 0, 0, 0.2)',
                          transition: 'border-color 0.15s ease',
                        }}
                      >
                        <Upload size={24} color="var(--accent-green)" style={{ margin: '0 auto 0.4rem' }} />
                        <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>Click or Drag Image Here</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                          Supports JPEG, PNG up to 25 MB for distributed YOLOv8 & OpenCV analysis
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Architecture & Confidence Threshold */}
                  <div className="grid grid-2" style={{ gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">Model Architecture</label>
                      <select
                        className="form-input"
                        value={aiModel}
                        onChange={(e) => setAiModel(e.target.value)}
                      >
                        <option value="yolov8n">YOLOv8n (Nano - Pinned Cached Model)</option>
                      </select>
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <label className="form-label" style={{ margin: 0 }}>Confidence Threshold</label>
                        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)' }}>
                          {(confidenceThreshold * 100).toFixed(0)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.05"
                        max="0.95"
                        step="0.05"
                        value={confidenceThreshold}
                        onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                        style={{ width: '100%', marginTop: '0.4rem' }}
                      />
                    </div>
                  </div>

                  {/* Palette Size Slider */}
                  <div className="form-group" style={{ margin: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <label className="form-label" style={{ margin: 0 }}>Dominant Colours Palette Size</label>
                      <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--accent-green)' }}>
                        {paletteSize} Colours (K-Means CIELAB)
                      </span>
                    </div>
                    <input
                      type="range"
                      min="3"
                      max="12"
                      step="1"
                      value={paletteSize}
                      onChange={(e) => setPaletteSize(parseInt(e.target.value))}
                      style={{ width: '100%', marginTop: '0.4rem' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      <span>3 (Minimal)</span>
                      <span>8 (Standard)</span>
                      <span>12 (Fine-grained)</span>
                    </div>
                  </div>
                </div>
              )}

              {(taskType === 'log' || taskType === 'echo') && (
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Message String</label>
                  <input
                    type="text"
                    className="form-input"
                    value={logMessage}
                    onChange={(e) => setLogMessage(e.target.value)}
                    placeholder="Enter diagnostic payload text..."
                  />
                </div>
              )}

              {taskType === 'sleep' && (
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Delay Duration (Seconds)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.1"
                    max="60"
                    className="form-input"
                    value={sleepDuration}
                    onChange={(e) => setSleepDuration(parseFloat(e.target.value) || 1.0)}
                  />
                </div>
              )}

              {/* Cluster Offload Policy & Timeout */}
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
                    <option value="local_only">Local Execution Only</option>
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Timeout (Seconds)</label>
                  <input
                    type="number"
                    min={5}
                    max={600}
                    className="form-input"
                    value={timeoutSeconds}
                    onChange={(e) => setTimeoutSeconds(parseFloat(e.target.value) || 60.0)}
                  />
                </div>
              </div>

              {/* Hardware Requirements */}
              <div className="grid grid-2" style={{ gap: '0.75rem', marginBottom: '1rem' }}>
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

                <div className="form-group" style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.82rem', marginTop: '1.25rem' }}>
                    <input
                      type="checkbox"
                      checked={requiresGpu}
                      onChange={(e) => setRequiresGpu(e.target.checked)}
                    />
                    <span>Requires Discrete GPU</span>
                  </label>
                </div>
              </div>

              {/* Advanced JSON View Toggle */}
              <div style={{ marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <label className="form-label" style={{ margin: 0 }}>
                    Payload Arguments (JSON)
                  </label>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}
                    onClick={() => setCustomPayloadMode(!customPayloadMode)}
                  >
                    {customPayloadMode ? 'Use Form Inputs' : 'Edit Raw JSON'}
                  </button>
                </div>
                <textarea
                  className="form-input code-font"
                  rows={customPayloadMode ? 4 : 3}
                  value={payloadText}
                  onChange={(e) => {
                    setPayloadText(e.target.value)
                    setCustomPayloadMode(true)
                  }}
                  style={{ resize: 'vertical', fontSize: '0.78rem' }}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} disabled={submitting}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary btn-sm" disabled={submitting}>
                {submitting ? 'Dispatching...' : 'Dispatch Task to Cluster'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
