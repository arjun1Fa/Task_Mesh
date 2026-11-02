import React, { useState, useEffect } from 'react'
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Cpu,
  Server,
  Zap,
  Copy,
  Check,
  AlertTriangle,
  Activity,
  FileCode,
  Calendar,
  Hash,
  Terminal,
  Download,
  Image as ImageIcon,
  Palette,
  Eye,
  Sliders,
  ExternalLink,
} from 'lucide-react'
import type { Task } from '../types'

interface TaskDetailsDrawerProps {
  task: Task | any | null
  isOpen: boolean
  onClose: () => void
  onRetry?: (taskId: string) => void
  onCancel?: (taskId: string) => void
}

export const TaskDetailsDrawer: React.FC<TaskDetailsDrawerProps> = ({
  task,
  isOpen,
  onClose,
  onRetry,
  onCancel,
}) => {
  const [copiedId, setCopiedId] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'result' | 'payload' | 'timeline'>('overview')

  if (!isOpen || !task) return null

  const taskId = task.id || task.task_id || 'unknown'
  const taskType = task.task_type || 'unknown'
  const status = task.status || 'unknown'
  const priority = task.priority ?? 0
  const assignedNode = task.assigned_node_id || task.node_id || task.result?.node_id || null
  const currentAttempt = task.current_attempt || (task.attempt_id ? task.attempt_id.split('-A')[1] : 1) || 1
  const maxAttempts = task.retry_policy?.max_attempts || 3

  // Result & Output extraction
  const resultObj = task.result || task
  const output = resultObj.output || (typeof task.output === 'object' ? task.output : null) || {}
  const metrics = resultObj.metrics || task.metrics || {}
  const errorMessage = task.error_message || resultObj.error || task.error || null

  // Execution timings
  const executionTime =
    resultObj.execution_time_seconds ??
    task.execution_time_seconds ??
    output.computation_time_seconds ??
    output.computation_duration ??
    null

  const createdAt = task.created_at ? new Date(task.created_at) : null
  const startedAt = resultObj.started_at
    ? new Date(resultObj.started_at)
    : task.started_at
    ? new Date(task.started_at)
    : null
  const completedAt = resultObj.completed_at
    ? new Date(resultObj.completed_at)
    : task.completed_at
    ? new Date(task.completed_at)
    : task.updated_at
    ? new Date(task.updated_at)
    : null

  // Queue wait calculation
  let queueWaitSeconds: string = 'N/A'
  if (createdAt && startedAt && startedAt >= createdAt) {
    queueWaitSeconds = ((startedAt.getTime() - createdAt.getTime()) / 1000).toFixed(3) + 's'
  } else if (createdAt && completedAt && executionTime !== null && completedAt >= createdAt) {
    const totalSec = (completedAt.getTime() - createdAt.getTime()) / 1000
    const wait = Math.max(0, totalSec - Number(executionTime))
    queueWaitSeconds = wait.toFixed(3) + 's'
  }

  // Worker Hostname
  const workerHostname = resultObj.worker_hostname || task.worker_hostname || task.hostname || null

  // CPU Test fields
  const requestedIterations = output.requested_iterations ?? output.iterations ?? task.payload?.iterations ?? null
  const actualIterations = output.actual_iterations ?? output.iterations ?? null
  const checksum = output.checksum ?? null
  const computationDuration = output.computation_duration ?? output.computation_time_seconds ?? null

  // Matrix Multiply fields
  const matrixDim = output.dimension ?? task.payload?.dim ?? null
  const matrixOps = output.operations_count ?? null

  // AI Inference fields
  const aiModel = output.model ?? metrics.model ?? task.payload?.model ?? task.ai_metadata?.model ?? null
  const aiLatency = output.inference_latency_ms ?? metrics.inference_time_ms ?? task.ai_metadata?.inference_latency_ms ?? null
  const aiDetections = output.detections ? output.detections.length : (task.ai_metadata?.detections_count ?? null)

  const handleCopyId = () => {
    navigator.clipboard.writeText(taskId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 2000)
  }

  // Vision Inference Output Extraction
  const detections: any[] = Array.isArray(output.detections) ? output.detections : []
  const dominantColors: any[] = Array.isArray(output.dominant_colors) ? output.dominant_colors : []
  const timings = output.timings || {}
  const imgMeta = output.image_metadata || {}

  const [imageTab, setImageTab] = useState<'annotated' | 'original' | 'split'>('annotated')
  const [annotatedImgUrl, setAnnotatedImgUrl] = useState<string | null>(null)
  const [inputImgUrl, setInputImgUrl] = useState<string | null>(null)
  const [loadingImages, setLoadingImages] = useState(false)
  const [copiedHex, setCopiedHex] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !task || taskType !== 'image_inference') return

    let isMounted = true
    let annRevoke: string | null = null
    let inRevoke: string | null = null

    async function loadImages() {
      setLoadingImages(true)
      const token = localStorage.getItem('taskmesh_token') || ''
      const headers: Record<string, string> = {}
      if (token) headers['Authorization'] = `Bearer ${token}`

      // Load Annotated Image
      const annUrls = [
        `/v1/tasks/${taskId}/annotated-image`,
        `/api/worker/tasks/${taskId}/annotated-image`,
        output.artifacts?.annotated_image?.direct_url,
        output.artifacts?.annotated_image?.url,
      ].filter(Boolean)

      for (const u of annUrls) {
        try {
          const res = await fetch(u, { headers })
          if (res.ok) {
            const blob = await res.blob()
            if (isMounted) {
              const objUrl = URL.createObjectURL(blob)
              annRevoke = objUrl
              setAnnotatedImgUrl(objUrl)
            }
            break
          }
        } catch {}
      }

      // Load Input Image
      const inUrls = [
        `/v1/tasks/${taskId}/input-image`,
        `/api/worker/tasks/${taskId}/input-image`,
      ]

      for (const u of inUrls) {
        try {
          const res = await fetch(u, { headers })
          if (res.ok) {
            const blob = await res.blob()
            if (isMounted) {
              const objUrl = URL.createObjectURL(blob)
              inRevoke = objUrl
              setInputImgUrl(objUrl)
            }
            break
          }
        } catch {}
      }

      if (isMounted) setLoadingImages(false)
    }

    loadImages()

    return () => {
      isMounted = false
      if (annRevoke) URL.revokeObjectURL(annRevoke)
      if (inRevoke) URL.revokeObjectURL(inRevoke)
    }
  }, [isOpen, taskId, taskType])

  const handleDownloadAnnotated = () => {
    if (!annotatedImgUrl) return
    const a = document.createElement('a')
    a.href = annotatedImgUrl
    a.download = `annotated_${taskId}.jpg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const handleCopyHex = (hex: string) => {
    navigator.clipboard.writeText(hex)
    setCopiedHex(hex)
    setTimeout(() => setCopiedHex(null), 1500)
  }

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 1100 }}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '780px',
          width: '95%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--bg-card)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Header */}
        <div className="modal-header" style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: 0 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 'var(--radius-sm)',
                backgroundColor: status === 'completed' ? 'rgba(16, 185, 129, 0.15)' : status === 'failed' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {status === 'completed' ? (
                <CheckCircle2 size={20} color="var(--accent-green)" />
              ) : status === 'failed' ? (
                <XCircle size={20} color="var(--status-failed)" />
              ) : (
                <Activity size={20} color="var(--accent-cyan)" />
              )}
            </div>

            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className="mono" style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-color)' }}>
                  {taskId}
                </span>
                <button
                  className="btn btn-secondary btn-icon"
                  style={{ width: 22, height: 22, padding: 0 }}
                  onClick={handleCopyId}
                  title="Copy Task ID"
                >
                  {copiedId ? <Check size={12} color="var(--accent-green)" /> : <Copy size={12} />}
                </button>
                <span className={`status-pill ${status}`}>{status}</span>
                <span className="badge badge-blue">{taskType}</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                Priority P{priority} &bull; Attempt {currentAttempt} of {maxAttempts}
              </p>
            </div>
          </div>

          <button className="btn btn-secondary btn-icon" onClick={onClose} style={{ flexShrink: 0 }}>
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            padding: '0.65rem 1.25rem',
            borderBottom: '1px solid var(--border-color)',
            backgroundColor: 'rgba(0,0,0,0.2)',
          }}
        >
          <button
            className={`btn btn-sm ${activeTab === 'overview' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('overview')}
            style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}
          >
            Overview & Execution
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'result' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('result')}
            style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}
          >
            Structured Output
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'timeline' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('timeline')}
            style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}
          >
            Execution Timeline
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'payload' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('payload')}
            style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}
          >
            Raw Payload JSON
          </button>
        </div>

        {/* Body Container */}
        <div className="modal-body" style={{ padding: '1.25rem', overflowY: 'auto', flex: 1 }}>
          {/* Error Banner */}
          {errorMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.75rem',
                padding: '0.85rem 1rem',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '1rem',
                color: 'var(--status-failed)',
              }}
            >
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.2rem' }}>
                  Execution Failure Details:
                </div>
                <div className="mono code-font" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
                  {errorMessage}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Top KPI Cards */}
              <div className="grid grid-4" style={{ gap: '0.75rem' }}>
                <div className="stat-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="stat-label">Execution Duration</div>
                  <div className="stat-value mono" style={{ color: 'var(--accent-green)', fontSize: '1.25rem' }}>
                    {executionTime !== null ? `${Number(executionTime).toFixed(4)}s` : status === 'running' ? 'Active' : '-'}
                  </div>
                  <div className="stat-hint">Worker thread compute time</div>
                </div>

                <div className="stat-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="stat-label">Queue Wait Time</div>
                  <div className="stat-value mono" style={{ color: 'var(--accent-cyan)', fontSize: '1.25rem' }}>
                    {queueWaitSeconds}
                  </div>
                  <div className="stat-hint">Dispatch scheduling delay</div>
                </div>

                <div className="stat-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="stat-label">Assigned Worker</div>
                  <div className="stat-value mono" style={{ color: 'var(--accent-blue)', fontSize: '1rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {assignedNode || 'Unassigned'}
                  </div>
                  <div className="stat-hint">{workerHostname ? `Host: ${workerHostname}` : 'Cluster Node'}</div>
                </div>

                <div className="stat-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="stat-label">Task Status</div>
                  <div className="stat-value" style={{ fontSize: '1rem', textTransform: 'uppercase' }}>
                    <span className={`status-pill ${status}`}>{status}</span>
                  </div>
                  <div className="stat-hint">Attempt {currentAttempt} of {maxAttempts}</div>
                </div>
              </div>

              {/* Task Details Section */}
              <div className="card" style={{ margin: 0, padding: '1rem' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Layers size={16} color="var(--accent-blue)" />
                  Task Configuration & Requirements
                </div>

                <div className="grid grid-2" style={{ gap: '0.75rem', fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--border-color)' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Offload Policy:</span>
                    <span className="mono" style={{ fontWeight: 600 }}>{task.offload_policy || 'wireless_allowed'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--border-color)' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Timeout Limit:</span>
                    <span className="mono" style={{ fontWeight: 600 }}>{task.timeout_seconds || 60}s</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--border-color)' }}>
                    <span style={{ color: 'var(--text-dim)' }}>GPU Acceleration:</span>
                    <span className="mono" style={{ fontWeight: 600 }}>{task.requires_gpu ? 'Required' : 'CPU Only'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--border-color)' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Required RAM:</span>
                    <span className="mono" style={{ fontWeight: 600 }}>{task.required_memory_mb || 0} MB</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Submitted At:</span>
                    <span className="mono">{createdAt ? createdAt.toLocaleString() : 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Completed At:</span>
                    <span className="mono">{completedAt ? completedAt.toLocaleString() : 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Workload-Specific Metrics Display */}
              {taskType === 'cpu_test' && (requestedIterations || checksum !== null) && (
                <div className="card" style={{ margin: 0, padding: '1rem', backgroundColor: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Cpu size={16} />
                    CPU Workload Execution Metrics
                  </div>

                  <div className="grid grid-4" style={{ gap: '0.75rem' }}>
                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Requested Iterations</div>
                      <div className="stat-value mono" style={{ fontSize: '1.1rem' }}>
                        {requestedIterations !== null ? Number(requestedIterations).toLocaleString() : 'N/A'}
                      </div>
                    </div>

                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Actual Executed</div>
                      <div className="stat-value mono" style={{ color: 'var(--accent-green)', fontSize: '1.1rem' }}>
                        {actualIterations !== null ? Number(actualIterations).toLocaleString() : 'N/A'}
                      </div>
                    </div>

                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Computation Time</div>
                      <div className="stat-value mono" style={{ color: 'var(--accent-cyan)', fontSize: '1.1rem' }}>
                        {computationDuration !== null ? `${Number(computationDuration).toFixed(4)}s` : 'N/A'}
                      </div>
                    </div>

                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Math Checksum</div>
                      <div className="stat-value mono" style={{ color: 'var(--accent-amber)', fontSize: '1.1rem' }}>
                        {checksum !== null ? String(checksum) : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {taskType === 'matrix_multiply' && matrixDim && (
                <div className="card" style={{ margin: 0, padding: '1rem', backgroundColor: 'rgba(168, 85, 247, 0.05)', border: '1px solid rgba(168, 85, 247, 0.25)' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-purple)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Zap size={16} />
                    Matrix Multiplication Execution Metrics
                  </div>

                  <div className="grid grid-3" style={{ gap: '0.75rem' }}>
                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Square Matrix Dimension</div>
                      <div className="stat-value mono" style={{ fontSize: '1.1rem' }}>{matrixDim} &times; {matrixDim}</div>
                    </div>
                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Matrix Operations</div>
                      <div className="stat-value mono" style={{ color: 'var(--accent-cyan)', fontSize: '1.1rem' }}>
                        {matrixOps !== null ? Number(matrixOps).toLocaleString() : 'N/A'}
                      </div>
                    </div>
                    <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="stat-label">Checksum</div>
                      <div className="stat-value mono" style={{ color: 'var(--accent-green)', fontSize: '1.1rem' }}>
                        {checksum !== null ? String(checksum) : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {taskType === 'image_inference' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* CV & Colour Analysis KPI Cards */}
                  <div className="card" style={{ margin: 0, padding: '1rem', backgroundColor: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-green)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Activity size={16} />
                      YOLOv8 & OpenCV Colour Analysis Metrics
                    </div>

                    <div className="grid grid-4" style={{ gap: '0.75rem' }}>
                      <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                        <div className="stat-label">Model Architecture</div>
                        <div className="stat-value mono" style={{ fontSize: '1rem', color: 'var(--accent-green)' }}>
                          {String(aiModel || 'yolov8n')}
                        </div>
                        <div className="stat-hint">Ultralytics PyTorch</div>
                      </div>

                      <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                        <div className="stat-label">Objects Detected</div>
                        <div className="stat-value mono" style={{ color: 'var(--accent-cyan)', fontSize: '1.25rem' }}>
                          {detections.length}
                        </div>
                        <div className="stat-hint">COCO 80-Class Detect</div>
                      </div>

                      <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                        <div className="stat-label">Total Execution Time</div>
                        <div className="stat-value mono" style={{ color: 'var(--accent-green)', fontSize: '1.25rem' }}>
                          {timings.total_execution_ms ? `${timings.total_execution_ms.toFixed(1)} ms` : (aiLatency ? `${Number(aiLatency).toFixed(1)} ms` : '-')}
                        </div>
                        <div className="stat-hint">Preprocess + Infer + Palette</div>
                      </div>

                      <div className="stat-card" style={{ padding: '0.65rem 0.85rem' }}>
                        <div className="stat-label">Image Resolution</div>
                        <div className="stat-value mono" style={{ fontSize: '1rem' }}>
                          {imgMeta.width ? `${imgMeta.width} × ${imgMeta.height}` : '810 × 1080'}
                        </div>
                        <div className="stat-hint">{imgMeta.channels || 3} channels RGB</div>
                      </div>
                    </div>
                  </div>

                  {/* Dual-Image Visual Comparison Viewer */}
                  <div className="card" style={{ margin: 0, padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <ImageIcon size={16} color="var(--accent-cyan)" />
                        Computer Vision Artifact Comparison
                      </div>

                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        <div style={{ display: 'flex', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', padding: '2px', border: '1px solid var(--border-color)' }}>
                          <button
                            type="button"
                            className={`btn btn-sm ${imageTab === 'annotated' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setImageTab('annotated')}
                            style={{ fontSize: '0.72rem', padding: '0.2rem 0.6rem' }}
                          >
                            Annotated Output
                          </button>
                          <button
                            type="button"
                            className={`btn btn-sm ${imageTab === 'original' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setImageTab('original')}
                            style={{ fontSize: '0.72rem', padding: '0.2rem 0.6rem' }}
                          >
                            Original Input
                          </button>
                          <button
                            type="button"
                            className={`btn btn-sm ${imageTab === 'split' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setImageTab('split')}
                            style={{ fontSize: '0.72rem', padding: '0.2rem 0.6rem' }}
                          >
                            Side-by-Side
                          </button>
                        </div>

                        {annotatedImgUrl && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={handleDownloadAnnotated}
                            style={{ fontSize: '0.72rem', padding: '0.25rem 0.6rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                            title="Download Annotated Image"
                          >
                            <Download size={13} color="var(--accent-green)" />
                            <span>Download JPEG</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Image Viewport */}
                    <div
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-color)',
                        padding: '0.75rem',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        minHeight: '260px',
                        overflow: 'hidden',
                      }}
                    >
                      {loadingImages ? (
                        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                          <div style={{ fontSize: '0.85rem' }}>Loading image artifacts from cluster...</div>
                        </div>
                      ) : imageTab === 'split' ? (
                        <div className="grid grid-2" style={{ gap: '0.75rem', width: '100%' }}>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '0.4rem' }}>
                              Original Uploaded Image
                            </div>
                            {inputImgUrl ? (
                              <img
                                src={inputImgUrl}
                                alt="Original input"
                                style={{
                                  maxWidth: '100%',
                                  maxHeight: '320px',
                                  objectFit: 'contain',
                                  borderRadius: 'var(--radius-xs)',
                                  border: '1px solid var(--border-color)',
                                }}
                              />
                            ) : (
                              <div style={{ padding: '2rem', color: 'var(--text-dim)', fontSize: '0.78rem' }}>Original image not cached</div>
                            )}
                          </div>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--accent-green)', marginBottom: '0.4rem' }}>
                              Annotated YOLOv8 + Palette Output
                            </div>
                            {annotatedImgUrl ? (
                              <img
                                src={annotatedImgUrl}
                                alt="Annotated output"
                                style={{
                                  maxWidth: '100%',
                                  maxHeight: '320px',
                                  objectFit: 'contain',
                                  borderRadius: 'var(--radius-xs)',
                                  border: '1px solid var(--border-color)',
                                }}
                              />
                            ) : (
                              <div style={{ padding: '2rem', color: 'var(--text-dim)', fontSize: '0.78rem' }}>Annotated output pending</div>
                            )}
                          </div>
                        </div>
                      ) : imageTab === 'original' ? (
                        inputImgUrl ? (
                          <img
                            src={inputImgUrl}
                            alt="Original input"
                            style={{
                              maxWidth: '100%',
                              maxHeight: '380px',
                              objectFit: 'contain',
                              borderRadius: 'var(--radius-xs)',
                            }}
                          />
                        ) : (
                          <div style={{ padding: '2rem', color: 'var(--text-dim)', fontSize: '0.78rem' }}>Original input image not cached on this host</div>
                        )
                      ) : (
                        annotatedImgUrl ? (
                          <img
                            src={annotatedImgUrl}
                            alt="Annotated YOLO output"
                            style={{
                              maxWidth: '100%',
                              maxHeight: '380px',
                              objectFit: 'contain',
                              borderRadius: 'var(--radius-xs)',
                            }}
                          />
                        ) : (
                          <div style={{ padding: '2rem', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                            {status === 'completed' ? 'Annotated image artifact generated' : 'Waiting for worker inference...'}
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Dominant Colours Palette Section */}
                  {dominantColors.length > 0 && (
                    <div className="card" style={{ margin: 0, padding: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Palette size={16} color="var(--accent-purple)" />
                          Dominant Colours Palette (CIELAB K-Means Clustering)
                        </div>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                          {dominantColors.length} Clusters &bull; Sum: 100.0%
                        </span>
                      </div>

                      {/* Proportional Stacked Palette Bar */}
                      <div
                        style={{
                          height: 28,
                          width: '100%',
                          borderRadius: 'var(--radius-sm)',
                          overflow: 'hidden',
                          display: 'flex',
                          boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)',
                          border: '1px solid rgba(255,255,255,0.1)',
                          marginBottom: '1rem',
                        }}
                      >
                        {dominantColors.map((c: any, idx: number) => (
                          <div
                            key={idx}
                            title={`${c.nearest_name} (${c.hex}) - ${c.percentage}%`}
                            style={{
                              backgroundColor: c.hex,
                              flex: c.percentage,
                              minWidth: '6px',
                              cursor: 'pointer',
                              transition: 'opacity 0.15s ease',
                            }}
                            onClick={() => handleCopyHex(c.hex)}
                          />
                        ))}
                      </div>

                      {/* Interactive Colour Cards Grid */}
                      <div className="grid grid-4" style={{ gap: '0.6rem' }}>
                        {dominantColors.map((c: any, idx: number) => (
                          <div
                            key={idx}
                            style={{
                              backgroundColor: 'var(--bg-main)',
                              border: '1px solid var(--border-color)',
                              borderRadius: 'var(--radius-sm)',
                              padding: '0.6rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.6rem',
                            }}
                          >
                            <div
                              style={{
                                width: 28,
                                height: 28,
                                borderRadius: '50%',
                                backgroundColor: c.hex,
                                border: '2px solid rgba(255, 255, 255, 0.25)',
                                flexShrink: 0,
                                boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                              }}
                            />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontSize: '0.78rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {c.nearest_name}
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
                                <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                                  {c.percentage}%
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleCopyHex(c.hex)}
                                  className="mono"
                                  style={{
                                    fontSize: '0.68rem',
                                    padding: '1px 4px',
                                    borderRadius: '3px',
                                    border: '1px solid var(--border-color)',
                                    background: 'transparent',
                                    color: 'var(--text-dim)',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '2px',
                                  }}
                                  title="Copy HEX"
                                >
                                  {copiedHex === c.hex ? <Check size={10} color="var(--accent-green)" /> : c.hex}
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Detected Objects Table */}
                  {detections.length > 0 && (
                    <div className="card" style={{ margin: 0, padding: '1rem' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Eye size={16} color="var(--accent-green)" />
                        Detected Objects &amp; Dominant Object Colours ({detections.length})
                      </div>

                      <div style={{ overflowX: 'auto' }}>
                        <table className="data-table" style={{ width: '100%', fontSize: '0.78rem' }}>
                          <thead>
                            <tr>
                              <th style={{ width: '32px' }}>#</th>
                              <th>Class</th>
                              <th>Confidence</th>
                              <th>Bounding Box [ymin, xmin, ymax, xmax]</th>
                              <th>Dominant Object Colour</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detections.map((d: any, idx: number) => {
                              const confPct = (d.confidence * 100).toFixed(1)
                              const bboxStr = Array.isArray(d.bbox) ? `[${d.bbox.join(', ')}]` : '-'
                              const objColor = d.dominant_color || {}
                              return (
                                <tr key={idx}>
                                  <td className="mono" style={{ color: 'var(--text-dim)' }}>{idx + 1}</td>
                                  <td>
                                    <span className="badge badge-green" style={{ textTransform: 'capitalize' }}>
                                      {d.class}
                                    </span>
                                  </td>
                                  <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                      <div
                                        style={{
                                          width: 48,
                                          height: 5,
                                          backgroundColor: 'rgba(255,255,255,0.1)',
                                          borderRadius: 3,
                                          overflow: 'hidden',
                                        }}
                                      >
                                        <div
                                          style={{
                                            width: `${confPct}%`,
                                            height: '100%',
                                            backgroundColor: Number(confPct) > 75 ? 'var(--accent-green)' : 'var(--accent-cyan)',
                                          }}
                                        />
                                      </div>
                                      <span className="mono" style={{ fontWeight: 600 }}>{confPct}%</span>
                                    </div>
                                  </td>
                                  <td className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                                    {bboxStr}
                                  </td>
                                  <td>
                                    {objColor.hex ? (
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                        <div
                                          style={{
                                            width: 14,
                                            height: 14,
                                            borderRadius: '50%',
                                            backgroundColor: objColor.hex,
                                            border: '1px solid rgba(255,255,255,0.3)',
                                            flexShrink: 0,
                                          }}
                                        />
                                        <span className="mono" style={{ fontSize: '0.72rem' }}>{objColor.hex}</span>
                                        <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                                          ({objColor.nearest_name || 'Object Color'})
                                        </span>
                                      </div>
                                    ) : (
                                      <span style={{ color: 'var(--text-dim)' }}>-</span>
                                    )}
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Multi-Stage Execution Latency Breakdown */}
                  {timings.total_execution_ms && (
                    <div className="card" style={{ margin: 0, padding: '1rem', backgroundColor: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Sliders size={16} />
                        Distributed AI Pipeline Latency Breakdown
                      </div>

                      <div className="grid grid-5" style={{ gap: '0.5rem' }}>
                        <div className="stat-card" style={{ padding: '0.5rem 0.65rem' }}>
                          <div className="stat-label" style={{ fontSize: '0.65rem' }}>1. Preprocessing</div>
                          <div className="stat-value mono" style={{ fontSize: '0.95rem' }}>
                            {timings.preprocessing_ms ? `${timings.preprocessing_ms.toFixed(1)} ms` : '-'}
                          </div>
                          <div className="stat-hint" style={{ fontSize: '0.62rem' }}>Decode &amp; Letterbox</div>
                        </div>

                        <div className="stat-card" style={{ padding: '0.5rem 0.65rem' }}>
                          <div className="stat-label" style={{ fontSize: '0.65rem' }}>2. YOLOv8 Inference</div>
                          <div className="stat-value mono" style={{ fontSize: '0.95rem', color: 'var(--accent-green)' }}>
                            {timings.inference_ms ? `${timings.inference_ms.toFixed(1)} ms` : '-'}
                          </div>
                          <div className="stat-hint" style={{ fontSize: '0.62rem' }}>PyTorch Forward Pass</div>
                        </div>

                        <div className="stat-card" style={{ padding: '0.5rem 0.65rem' }}>
                          <div className="stat-label" style={{ fontSize: '0.65rem' }}>3. Colour Extraction</div>
                          <div className="stat-value mono" style={{ fontSize: '0.95rem', color: 'var(--accent-purple)' }}>
                            {timings.color_extraction_ms ? `${timings.color_extraction_ms.toFixed(1)} ms` : '-'}
                          </div>
                          <div className="stat-hint" style={{ fontSize: '0.62rem' }}>CIELAB K-Means</div>
                        </div>

                        <div className="stat-card" style={{ padding: '0.5rem 0.65rem' }}>
                          <div className="stat-label" style={{ fontSize: '0.65rem' }}>4. Visual Annotation</div>
                          <div className="stat-value mono" style={{ fontSize: '0.95rem' }}>
                            {timings.annotation_ms ? `${timings.annotation_ms.toFixed(1)} ms` : '-'}
                          </div>
                          <div className="stat-hint" style={{ fontSize: '0.62rem' }}>BBoxes &amp; Palette Bar</div>
                        </div>

                        <div className="stat-card" style={{ padding: '0.5rem 0.65rem' }}>
                          <div className="stat-label" style={{ fontSize: '0.65rem' }}>Total Execution</div>
                          <div className="stat-value mono" style={{ fontSize: '0.95rem', color: 'var(--accent-cyan)' }}>
                            {timings.total_execution_ms ? `${timings.total_execution_ms.toFixed(1)} ms` : '-'}
                          </div>
                          <div className="stat-hint" style={{ fontSize: '0.62rem' }}>Pure Worker Compute</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'result' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-color)' }}>
                  Structured Output Payload:
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  Verified worker execution outcome
                </span>
              </div>

              <pre
                className="code-font"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.45)',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  maxHeight: '340px',
                  overflowY: 'auto',
                  fontSize: '0.8rem',
                  lineHeight: '1.45',
                  color: '#e2e8f0',
                }}
              >
                {JSON.stringify(output && Object.keys(output).length > 0 ? output : resultObj, null, 2)}
              </pre>

              {metrics && Object.keys(metrics).length > 0 && (
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-color)', marginBottom: '0.35rem' }}>
                    Hardware Telemetry & Inference Metrics:
                  </div>
                  <pre
                    className="code-font"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.35)',
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-color)',
                      maxHeight: '160px',
                      overflowY: 'auto',
                      fontSize: '0.78rem',
                      color: '#94a3b8',
                    }}
                  >
                    {JSON.stringify(metrics, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {activeTab === 'timeline' && (
            <div style={{ padding: '0.5rem 0' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', position: 'relative' }}>
                {/* 1. Submitted */}
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      backgroundColor: 'rgba(56, 189, 248, 0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <CheckCircle2 size={16} color="var(--accent-cyan)" />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Task Submitted & Accepted</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      Registered to Orchestrator persistence with Priority P{priority}
                    </div>
                    <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', marginTop: '2px' }}>
                      {createdAt ? createdAt.toLocaleString() : 'N/A'}
                    </div>
                  </div>
                </div>

                {/* 2. Dispatched */}
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      backgroundColor: assignedNode ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Server size={16} color={assignedNode ? 'var(--accent-blue)' : 'var(--text-dim)'} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                      {assignedNode ? `Assigned to Node: ${assignedNode}` : 'Awaiting Worker Assignment'}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      {assignedNode ? `Adaptive scheduler lease allocated. Host: ${workerHostname || 'online worker'}` : 'In priority dispatch queue'}
                    </div>
                    <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      Queue wait: {queueWaitSeconds}
                    </div>
                  </div>
                </div>

                {/* 3. Executed */}
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      backgroundColor:
                        status === 'completed'
                          ? 'rgba(16, 185, 129, 0.2)'
                          : status === 'failed'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : 'rgba(245, 158, 11, 0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {status === 'completed' ? (
                      <CheckCircle2 size={16} color="var(--accent-green)" />
                    ) : status === 'failed' ? (
                      <XCircle size={16} color="var(--status-failed)" />
                    ) : (
                      <Clock size={16} color="var(--status-degraded)" />
                    )}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                      {status === 'completed'
                        ? 'Execution Finalized Successfully'
                        : status === 'failed'
                        ? 'Execution Failed'
                        : 'Execution In Progress'}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                      {status === 'completed'
                        ? `Computation duration: ${executionTime !== null ? `${Number(executionTime).toFixed(4)}s` : 'N/A'}`
                        : status === 'failed'
                        ? `Terminated with error: ${errorMessage || 'Unknown error'}`
                        : 'Running on worker execution pool'}
                    </div>
                    <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--accent-green)', marginTop: '2px' }}>
                      {completedAt ? completedAt.toLocaleString() : 'In flight'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'payload' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-color)' }}>
                  Task Input Arguments (Payload):
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  JSON dispatched to worker agent
                </span>
              </div>

              <pre
                className="code-font"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.45)',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  maxHeight: '340px',
                  overflowY: 'auto',
                  fontSize: '0.8rem',
                  lineHeight: '1.45',
                  color: '#e2e8f0',
                }}
              >
                {JSON.stringify(task.payload || task.payload_summary || {}, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="modal-footer"
          style={{
            padding: '0.85rem 1.25rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {(status === 'failed' || status === 'cancelled') && onRetry && (
              <button className="btn btn-secondary btn-sm" onClick={() => onRetry(taskId)}>
                Retry Workload
              </button>
            )}
            {(status === 'pending' || status === 'running') && onCancel && (
              <button className="btn btn-danger btn-sm" onClick={() => onCancel(taskId)}>
                Abort Workload
              </button>
            )}
          </div>

          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

