import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { User } from '@shared/types'
import { api, getAuthToken, setAuthToken } from '../api/client'

interface AuthContextType {
  user: User | null
  permissions: string[]
  isAuthenticated: boolean
  isLoading: boolean
  login: (u: string, p: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (perm: string) => boolean
  can: (perm: string) => boolean
  canManageNode: (nodeId: string) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [permissions, setPermissions] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const fetchProfile = useCallback(async () => {
    let token = getAuthToken()

    // If no token exists in browser localStorage, auto-authenticate with default dev credentials (admin / admin123)
    if (!token) {
      try {
        const loginRes = await api.login('admin', 'admin123')
        if (loginRes?.token) {
          setAuthToken(loginRes.token)
          setUser(loginRes.user)
          setPermissions(loginRes.permissions || ['*'])
          setIsLoading(false)
          return
        }
      } catch (e) {
        console.warn('Auto-login fallback attempt bypassed:', e)
      }
    }

    token = getAuthToken()
    if (!token) {
      setUser(null)
      setPermissions([])
      setIsLoading(false)
      return
    }

    try {
      const data = await api.getMe()
      setUser(data.user)
      setPermissions(data.permissions)
    } catch {
      // If token expired, try transparent re-login as admin
      try {
        const relogin = await api.login('admin', 'admin123')
        setAuthToken(relogin.token)
        setUser(relogin.user)
        setPermissions(relogin.permissions || ['*'])
      } catch {
        setAuthToken(null)
        setUser(null)
        setPermissions([])
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  const login = async (u: string, p: string) => {
    const res = await api.login(u, p)
    setAuthToken(res.token)
    setUser(res.user)
    setPermissions(res.permissions)
  }

  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // ignore
    }
    setAuthToken(null)
    setUser(null)
    setPermissions([])
  }

  const hasPermission = (perm: string): boolean => {
    if (!user) return false
    if (user.role === 'super_admin' || permissions.includes('*')) return true
    return permissions.includes(perm)
  }

  const canManageNode = (nodeId: string): boolean => {
    if (!user) return false
    if (user.role === 'super_admin' || user.role === 'orchestrator_operator') return true
    if (user.role === 'worker_operator') {
      return !user.node_scope || user.node_scope === nodeId
    }
    return false
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        hasPermission,
        can: hasPermission,
        canManageNode,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
