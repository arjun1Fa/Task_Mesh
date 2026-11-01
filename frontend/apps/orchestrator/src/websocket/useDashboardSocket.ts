import { useEffect, useRef, useState, useCallback } from 'react'
import type { DashboardEvent } from '@shared/types'
import { getAuthToken } from '../api/client'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

interface UseDashboardSocketReturn {
  status: ConnectionStatus
  lastEvent: DashboardEvent | null
  events: DashboardEvent[]
  subscribe: (eventType: string, handler: (event: DashboardEvent) => void) => () => void
}

export interface UseDashboardSocketOptions {
  token?: string | null
  isAuthenticated?: boolean
  onEvent?: (event: DashboardEvent) => void
  onMessage?: (event: DashboardEvent) => void
  onHealth?: (health: any) => void
}

export function useDashboardSocket(options?: UseDashboardSocketOptions): UseDashboardSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [lastEvent, setLastEvent] = useState<DashboardEvent | null>(null)
  const [events, setEvents] = useState<DashboardEvent[]>([])

  const socketRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, Set<(event: DashboardEvent) => void>>>(new Map())
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptRef = useRef<number>(0)
  const isMountedRef = useRef<boolean>(true)
  const optionsRef = useRef<UseDashboardSocketOptions | undefined>(options)

  useEffect(() => {
    optionsRef.current = options
  }, [options])

  const connect = useCallback(() => {
    if (!isMountedRef.current) return

    // Require token or authentication before attempting WebSocket connection
    const currentToken = optionsRef.current?.token ?? getAuthToken()
    const isAuthed = optionsRef.current?.isAuthenticated ?? !!currentToken

    if (!isAuthed || !currentToken) {
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
      setStatus('disconnected')
      return
    }

    // Clean up any existing connection
    if (socketRef.current) {
      try {
        socketRef.current.close()
      } catch {
        // ignore
      }
      socketRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const query = `?token=${encodeURIComponent(currentToken)}`
    const wsUrl = `${protocol}//${host}/v1/ws/dashboard${query}`

    setStatus(reconnectAttemptRef.current > 0 ? 'reconnecting' : 'connecting')

    try {
      const ws = new WebSocket(wsUrl)
      socketRef.current = ws

      ws.onopen = () => {
        if (!isMountedRef.current) return
        setStatus('connected')
        reconnectAttemptRef.current = 0
      }

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return
        try {
          if (event.data === 'pong') return
          const payload = JSON.parse(event.data) as DashboardEvent
          setLastEvent(payload)
          setEvents((prev) => [payload, ...prev.slice(0, 99)])

          // Support both onEvent and onMessage callback contracts
          const callback = optionsRef.current?.onEvent || optionsRef.current?.onMessage
          if (callback) {
            callback(payload)
          }

          if (
            (payload.event_type === 'health_update' || payload.event_type === 'initial_sync') &&
            optionsRef.current?.onHealth
          ) {
            optionsRef.current.onHealth(payload.data)
          }

          // Dispatch to type-specific handlers
          const listeners = handlersRef.current.get(payload.event_type)
          if (listeners) {
            listeners.forEach((handler) => handler(payload))
          }
          // Dispatch to wildcard listeners
          const wildcardListeners = handlersRef.current.get('*')
          if (wildcardListeners) {
            wildcardListeners.forEach((handler) => handler(payload))
          }
        } catch {
          // ignore non-json
        }
      }

      ws.onerror = () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close()
        }
      }

      ws.onclose = (evt) => {
        if (!isMountedRef.current) return
        setStatus('disconnected')
        socketRef.current = null

        // If closed due to unauthorized policy violation (1008), do not retry indefinitely without auth
        if (evt.code === 1008) {
          return
        }

        // Exponential backoff reconnect if authenticated
        const hasToken = optionsRef.current?.token ?? getAuthToken()
        if (hasToken) {
          const timeout = Math.min(1000 * Math.pow(1.5, reconnectAttemptRef.current), 10000)
          reconnectAttemptRef.current += 1
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, timeout)
        }
      }
    } catch {
      setStatus('disconnected')
    }
  }, [])

  // Re-connect whenever authentication state or token changes
  useEffect(() => {
    isMountedRef.current = true
    reconnectAttemptRef.current = 0
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
    connect()

    // Keep alive ping
    const pingInterval = setInterval(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send('ping')
      }
    }, 15000)

    return () => {
      isMountedRef.current = false
      clearInterval(pingInterval)
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [connect, options?.token, options?.isAuthenticated])

  const subscribe = useCallback((eventType: string, handler: (event: DashboardEvent) => void) => {
    if (!handlersRef.current.has(eventType)) {
      handlersRef.current.set(eventType, new Set())
    }
    handlersRef.current.get(eventType)!.add(handler)

    return () => {
      handlersRef.current.get(eventType)?.delete(handler)
    }
  }, [])

  return { status, lastEvent, events, subscribe }
}

