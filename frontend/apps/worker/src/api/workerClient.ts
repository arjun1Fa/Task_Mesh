/**
 * Worker Agent Console API Client.
 * Communicates exclusively with the local Node Agent daemon running on this machine.
 */

import type {
  WorkerOverview,
  WorkerHardware,
  WorkerTasksResponse,
  WorkerPoolStatus,
  WorkerNetworkStatus,
  SystemLogEntry,
  WorkerIdentity,
} from '@shared/types'

class WorkerApiClient {
  private baseUrl: string
  private consoleToken: string | null = null

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    }

    if (this.consoleToken) {
      headers['X-Worker-Token'] = this.consoleToken
    }

    const response = await fetch(url, { ...options, headers })

    if (!response.ok) {
      let errorMsg = `Worker API error: ${response.status} ${response.statusText}`
      try {
        const data = await response.json()
        if (data.detail) errorMsg = data.detail
      } catch {
        // Fallback to text
      }
      throw new Error(errorMsg)
    }

    return response.json()
  }

  // Identity Autodiscovery
  async getIdentity(): Promise<WorkerIdentity> {
    const identity = await this.request<WorkerIdentity>('/api/worker/identity')
    if (identity.console_token) {
      this.consoleToken = identity.console_token
    }
    return identity
  }

  // Telemetry & Overview
  async getOverview(): Promise<WorkerOverview> {
    return this.request<WorkerOverview>('/api/worker/overview')
  }

  // Hardware & Capabilities
  async getHardware(): Promise<WorkerHardware> {
    return this.request<WorkerHardware>('/api/worker/hardware')
  }

  // Local Task Execution
  async getTasks(): Promise<WorkerTasksResponse> {
    return this.request<WorkerTasksResponse>('/api/worker/tasks')
  }

  // Concurrency Pool
  async getPool(): Promise<WorkerPoolStatus> {
    return this.request<WorkerPoolStatus>('/api/worker/pool')
  }

  // Network & Transport
  async getNetwork(): Promise<WorkerNetworkStatus> {
    return this.request<WorkerNetworkStatus>('/api/worker/network')
  }

  // Local Logs
  async getLogs(limit: number = 100, severity?: string): Promise<SystemLogEntry[]> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    if (severity) params.set('severity', severity)
    return this.request<SystemLogEntry[]>(`/api/worker/logs?${params.toString()}`)
  }

  // Local Worker Operations
  async drain(): Promise<{ status: string; node_id: string }> {
    return this.request('/api/worker/drain', { method: 'POST' })
  }

  async resume(): Promise<{ status: string; node_id: string }> {
    return this.request('/api/worker/resume', { method: 'POST' })
  }

  async setMaintenance(maintenance: boolean): Promise<{ maintenance: boolean; status: string; node_id: string }> {
    return this.request('/api/worker/maintenance', {
      method: 'POST',
      body: JSON.stringify({ maintenance }),
    })
  }

  async updateConcurrency(concurrency: number): Promise<{ concurrency: number; node_id: string }> {
    return this.request('/api/worker/concurrency', {
      method: 'POST',
      body: JSON.stringify({ concurrency }),
    })
  }

  async togglePause(): Promise<{ paused_assignments: boolean; node_id: string }> {
    return this.request('/api/worker/pause_assignments', { method: 'POST' })
  }
}

export const workerApi = new WorkerApiClient()

