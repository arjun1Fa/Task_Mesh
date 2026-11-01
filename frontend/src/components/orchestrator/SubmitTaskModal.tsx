import React, { useState } from 'react'
import { PlusCircle, Cpu, Layers, Zap, X } from 'lucide-react'
import { api } from '../../api/client'

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="card max-w-lg w-full bg-[#14161b] border-[#2d3139]">
        <div className="flex justify-between items-center pb-3 border-b border-[#2d3139] mb-4">
          <div className="flex items-center gap-2">
            <PlusCircle className="text-blue-400" size={18} />
            <h3 className="font-semibold text-base text-white">Submit Task to Cluster</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white font-mono text-lg">
            ✕
          </button>
        </div>

        {error && (
          <div className="bg-red-950/60 border border-red-800 text-red-300 text-xs p-2.5 rounded mb-3">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-secondary block mb-1">Task Type:</label>
              <select
                value={taskType}
                onChange={(e) => handleTaskTypeChange(e.target.value)}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
              >
                <option value="benchmark">benchmark</option>
                <option value="echo">echo</option>
                <option value="object_detection">object_detection</option>
                <option value="yolo_inference">yolo_inference</option>
              </select>
            </div>

            <div>
              <label className="text-secondary block mb-1">Priority (1-10):</label>
              <input
                type="number"
                min="1"
                max="10"
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-secondary block mb-1">Offload Policy:</label>
              <select
                value={offloadPolicy}
                onChange={(e) => setOffloadPolicy(e.target.value)}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
              >
                <option value="remote_allowed">remote_allowed</option>
                <option value="wireless_allowed">wireless_allowed</option>
                <option value="local_only">local_only</option>
              </select>
            </div>

            <div>
              <label className="text-secondary block mb-1">Memory Required (MB):</label>
              <input
                type="number"
                step="64"
                value={requiredMemoryMb}
                onChange={(e) => setRequiredMemoryMb(Number(e.target.value))}
                className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="reqGpu"
              checked={requiresGpu}
              onChange={(e) => setRequiresGpu(e.target.checked)}
              className="cursor-pointer"
            />
            <label htmlFor="reqGpu" className="text-white cursor-pointer flex items-center gap-1">
              <Cpu size={14} className="text-purple-400" /> Requires Dedicated GPU Acceleration
            </label>
          </div>

          <div>
            <label className="text-secondary block mb-1">JSON Payload:</label>
            <textarea
              rows={5}
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 font-mono text-xs"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[#2d3139]">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="btn btn-primary text-xs"
            >
              {submitting ? 'Submitting...' : 'Submit to Queue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

