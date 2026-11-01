import type {
  AuditEvent,
  ClusterHealth,
  NodeProfile,
  SchedulerDecision,
  SchedulerMode,
  SystemLogEntry,
  Task,
  TaskStatus,
  User,
} from '@shared/types'

const API_BASE = ''

export function getAuthToken(): string | null {
  return localStorage.getItem('taskmesh_token')
}

export function setAuthToken(token: string | null): void {
  if (token) {
    localStorage.setItem('taskmesh_token', token)
  } else {
    localStorage.removeItem('taskmesh_token')
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken()
  const headers = new Headers(options.headers || {})

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errMsg = `Request failed: ${response.status} ${response.statusText}`
    try {
      const errData = await response.json()
      if (errData.detail) errMsg = errData.detail
    } catch {
      // fallback
    }
    throw new Error(errMsg)
  }

  return response.json()
}

export const api = {
  // Auth & RBAC
  login: (username: string, password: string) =>
    request<{ user: User; token: string; permissions: string[] }>('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () =>
    request<{ status: string }>('/v1/auth/logout', {
      method: 'POST',
    }),

  getMe: () =>
    request<{ user: User; permissions: string[] }>('/v1/auth/me'),

  getPermissions: () =>
    request<Record<string, string[]>>('/v1/auth/permissions'),

  listUsers: () =>
    request<User[]>('/v1/users'),

  createUser: (data: { username: string; password: string; role: string; node_scope?: string }) =>
    request<User>('/v1/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateUser: (username: string, data: { role?: string; node_scope?: string; is_active?: boolean; password?: string }) =>
    request<User>(`/v1/users/${username}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteUser: (username: string) =>
    request<{ status: string; username: string }>(`/v1/users/${username}`, {
      method: 'DELETE',
    }),

  // Cluster & Health
  getClusterHealth: () =>
    request<ClusterHealth>('/v1/cluster/health'),

  getDetailedHealth: () =>
    request<Record<string, any>>('/v1/system/health/detailed'),

  getDispatchStatus: () =>
    request<{ dispatch_paused: boolean }>('/v1/cluster/dispatch/status'),

  pauseDispatch: () =>
    request<{ status: string; dispatch_paused: boolean }>('/v1/cluster/dispatch/pause', {
      method: 'POST',
    }),

  resumeDispatch: () =>
    request<{ status: string; dispatch_paused: boolean }>('/v1/cluster/dispatch/resume', {
      method: 'POST',
    }),

  // Nodes Management
  listNodes: (status?: string) =>
    request<NodeProfile[]>(`/v1/nodes${status ? `?status=${status}` : ''}`),

  getNode: (nodeId: string) =>
    request<NodeProfile>(`/v1/nodes/${nodeId}`),

  drainNode: (nodeId: string) =>
    request<{ status: string; node_id: string }>(`/v1/nodes/${nodeId}/drain`, {
      method: 'POST',
    }),

  resumeNode: (nodeId: string) =>
    request<{ status: string; node_id: string }>(`/v1/nodes/${nodeId}/resume`, {
      method: 'POST',
    }),

  setMaintenance: (nodeId: string, maintenance: boolean) =>
    request<{ status: string; node_id: string }>(`/v1/nodes/${nodeId}/maintenance`, {
      method: 'POST',
      body: JSON.stringify({ maintenance }),
    }),

  deleteNode: (nodeId: string, force: boolean = false) =>
    request<{ status: string; node_id: string }>(`/v1/nodes/${nodeId}?force=${force}`, {
      method: 'DELETE',
    }),

  getNodeTasks: (nodeId: string, limit: number = 50) =>
    request<Task[]>(`/v1/nodes/${nodeId}/tasks?limit=${limit}`),

  // Tasks Management
  listTasks: (status?: TaskStatus, limit: number = 100) =>
    request<Task[]>(`/v1/tasks?limit=${limit}${status ? `&status=${status}` : ''}`),

  getTask: (taskId: string) =>
    request<Task>(`/v1/tasks/${taskId}`),

  submitTask: (data: {
    task_type: string
    payload: Record<string, any>
    priority?: number
    offload_policy?: string
    requires_gpu?: boolean
    required_memory_mb?: number
  }) =>
    request<Task>('/v1/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  cancelTask: (taskId: string, reason: string = 'Operator cancellation') =>
    request<Task>(`/v1/tasks/${taskId}/cancel?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    }),

  retryTask: (taskId: string) =>
    request<Task>(`/v1/tasks/${taskId}/retry`, {
      method: 'POST',
    }),

  // Scheduler & Explainability
  getSchedulerStatus: () =>
    request<Record<string, any>>('/v1/scheduler/status'),

  getSchedulerDecisions: (limit: number = 50) =>
    request<SchedulerDecision[]>(`/v1/scheduler/decisions?limit=${limit}`),

  getSchedulerDiagnostics: () =>
    request<Record<string, any>>('/v1/scheduler/diagnostics'),

  changeSchedulerMode: (mode: SchedulerMode) =>
    request<{ status: string; new_mode: string }>('/v1/scheduler/mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),

  updateAdaptiveToggles: (toggles: Record<string, boolean>) =>
    request<{ status: string; toggles: Record<string, boolean> }>('/v1/scheduler/toggles', {
      method: 'POST',
      body: JSON.stringify({ toggles }),
    }),

  // DLQ Management
  listDlq: () =>
    request<Array<{ task: Task; failed_at: string; final_error: string; failure_count: number }>>('/v1/dlq'),

  recoverDlq: (taskId: string) =>
    request<Task>(`/v1/dlq/${taskId}/recover`, {
      method: 'POST',
    }),

  // Recovery & High Availability
  getStandbySnapshot: () =>
    request<Record<string, any>>('/v1/standby/snapshot'),

  getStandbyStatus: () =>
    request<{ standby_mode: boolean; primary_url: string | null; snapshot_interval_seconds: number }>('/v1/standby/status'),

  promoteStandby: () =>
    request<{ status: string; role: string }>('/v1/standby/promote', {
      method: 'POST',
    }),

  // System Config
  getSystemConfig: () =>
    request<Record<string, any>>('/v1/system/config'),

  updateSystemConfig: (updates: Record<string, any>) =>
    request<Record<string, any>>('/v1/system/config', {
      method: 'PATCH',
      body: JSON.stringify({ updates }),
    }),

  // Audit Logs
  getAuditLogs: (params: { actor?: string; action?: string; result?: string; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.actor) q.set('actor', params.actor)
    if (params.action) q.set('action', params.action)
    if (params.result) q.set('result', params.result)
    if (params.limit) q.set('limit', params.limit.toString())
    return request<AuditEvent[]>(`/v1/audit/logs?${q.toString()}`)
  },

  // System Logs
  getSystemLogs: (params: { level?: string; source?: string; search?: string; limit?: number; node_id?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.level) q.set('level', params.level)
    if (params.source) q.set('source', params.source)
    if (params.search) q.set('search', params.search)
    if (params.node_id) q.set('node_id', params.node_id)
    if (params.limit) q.set('limit', params.limit.toString())
    return request<SystemLogEntry[]>(`/v1/system/logs?${q.toString()}`)
  },
}
