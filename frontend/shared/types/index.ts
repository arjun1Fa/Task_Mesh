export type TaskStatus =
  | 'pending'
  | 'scheduled'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'cancelled'
  | 'dlq'

export type NodeStatus = 'online' | 'degraded' | 'draining' | 'maintenance' | 'offline'

export type SchedulerMode = 'round_robin' | 'least_loaded' | 'highest_bid' | 'adaptive'

export type OffloadPolicy = 'local_only' | 'wireless_allowed' | 'remote_allowed'

export type UserRole = 'super_admin' | 'orchestrator_operator' | 'worker_operator' | 'viewer'

export interface BinaryPayloadMeta {
  payload_id: string
  task_id: string
  workload_type: string
  model_identifier: string
  payload_size_bytes: number
  mime_type: string
  checksum_sha256: string
  chunk_size_bytes: number
  total_chunks: number
}

export interface TaskResult {
  task_id: string
  attempt_id: string
  node_id: string
  status: TaskStatus
  output?: Record<string, any>
  error?: string
  execution_time_seconds: number
  metrics?: Record<string, any>
  completed_at: string
}

export interface Task {
  id: string
  idempotency_key?: string
  task_type: string
  payload: Record<string, any>
  priority: number
  status: TaskStatus
  created_at: string
  updated_at: string
  scheduled_at?: string
  timeout_seconds: number
  assigned_node_id?: string
  current_attempt: number
  current_attempt_id?: string
  requires_gpu: boolean
  required_memory_mb: number
  required_capabilities: string[]
  offload_policy: OffloadPolicy
  binary_meta?: BinaryPayloadMeta
  retry_count: number
  error_message?: string
  progress: number
  result?: TaskResult
  metadata: Record<string, any>
}

export interface NodeCapabilities {
  cpu_cores: number
  cpu_frequency_mhz: number
  ram_total_mb: number
  ram_available_mb: number
  has_gpu: boolean
  gpu_name?: string
  gpu_vram_mb: number
  os: string
  arch: string
  supported_handlers: string[]
  tags: string[]
  worker_capacity: number
  ip_address?: string
  hostname?: string
  is_local: boolean
}

export interface NodeTelemetry {
  node_id: string
  timestamp: string
  cpu_percent: number
  ram_percent: number
  gpu_percent?: number
  gpu_memory_used_mb?: number
  active_tasks: number
  queued_tasks: number
  completed_tasks_total: number
  failed_tasks_total: number
  network_latency_ms: number
  rtt_ms_ewma: number
  upload_mbps_ewma: number
  download_mbps_ewma: number
  transfer_failures: number
}

export interface NodeProfile {
  id: string
  status: NodeStatus
  capabilities: NodeCapabilities
  telemetry?: NodeTelemetry
  first_seen: string
  last_heartbeat: string
  last_telemetry?: string
  base_score: number
  performance_multiplier: number
  effective_score: number
  drr_deficit: number
  total_assigned: number
  total_completed: number
  total_failed: number
  metadata: Record<string, any>
}

export interface SchedulerDecision {
  task_id: string
  selected_node_id: string
  policy_used: SchedulerMode
  candidate_node_ids: string[]
  candidate_scores: Record<string, number>
  bids: Record<string, number>
  fairness_deficits: Record<string, number>
  rl_state?: [number, number, number]
  rl_action?: number
  fallback_reason?: string
  local_estimate_ms?: number
  remote_estimate_ms?: number
  upload_ms?: number
  remote_inference_ms?: number
  download_ms?: number
  offload_decision?: 'local' | 'remote'
  offload_reason?: string
  timestamp: string
}

export interface User {
  id: string
  username: string
  role: UserRole
  node_scope?: string
  is_active: boolean
  created_at: string
  last_login?: string
}

export interface LoginResponse {
  user: User
  token: string
  permissions: string[]
}

export interface AuditEvent {
  id: string
  timestamp: string
  actor: string
  role: string
  action: string
  target: string
  result: 'success' | 'denied' | 'error'
  details: Record<string, any>
}

export interface ClusterHealth {
  status: string
  total_nodes: number
  online_nodes: number
  total_tasks: number
  running_tasks: number
  pending_tasks: number
  dlq_tasks: number
  fairness_cv: number
  scheduler_mode: string
}

export interface DashboardEvent {
  event_id: string
  event_type: string
  timestamp: string
  source: string
  entity_id: string
  data: Record<string, any>
}

export interface SystemLogEntry {
  id: string
  timestamp: string
  level: string
  source: string
  message: string
  task_id?: string
  node_id?: string
}

export interface WorkerIdentity {
  node_id: string
  hostname: string
  orchestrator_url: string
  status: string
  is_worker: boolean
  agent_version: string
}

export interface WorkerOverview {
  node_id: string
  hostname: string
  status: string
  connection_status: string
  orchestrator_url: string
  uptime_seconds: number
  agent_version: string
  cpu_percent: number
  ram_percent: number
  gpu_percent?: number
  gpu_memory_used_mb?: number
  has_gpu: boolean
  gpu_name?: string
  gpu_vram_mb: number
  active_tasks: number
  queued_tasks: number
  completed_tasks: number
  failed_tasks: number
  worker_concurrency: number
  capacity_utilization: number
  rtt_ms: number
  upload_mbps: number
  download_mbps: number
  is_local: boolean
  base_score?: number
  performance_multiplier?: number
  effective_score?: number
  paused_assignments?: boolean
}

