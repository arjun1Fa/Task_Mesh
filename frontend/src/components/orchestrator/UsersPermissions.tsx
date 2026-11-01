import React, { useState, useEffect } from 'react'
import {
  Shield,
  UserPlus,
  RefreshCw,
  Key,
  CheckCircle2,
  XCircle,
  Edit,
  Trash2,
  Lock,
  UserCheck,
  ShieldAlert
} from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import type { User, UserRole } from '../../types'
import { ConfirmationModal } from '../common/ConfirmationModal'

export const UsersPermissions: React.FC = () => {
  const { user: currentUser, can } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [permissionsMap, setPermissionsMap] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(true)

  // Create / Edit User Modal
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('viewer')
  const [nodeScope, setNodeScope] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete User Confirmation
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [uList, pMap] = await Promise.all([
        api.listUsers().catch(() => []),
        api.getPermissions().catch(() => ({})),
      ])
      setUsers(uList)
      setPermissionsMap(pMap)
    } catch (err) {
      console.error('Failed to load user management data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleOpenCreate = () => {
    setModalMode('create')
    setUsername('')
    setPassword('')
    setRole('viewer')
    setNodeScope('')
    setIsActive(true)
    setFormError(null)
    setIsModalOpen(true)
  }

  const handleOpenEdit = (user: User) => {
    setModalMode('edit')
    setUsername(user.username)
    setPassword('')
    setRole(user.role)
    setNodeScope(user.node_scope || '')
    setIsActive(user.is_active)
    setFormError(null)
    setIsModalOpen(true)
  }

  const handleSubmitUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    try {
      setSubmitting(true)
      if (modalMode === 'create') {
        if (!username.trim() || !password.trim()) {
          throw new Error('Username and password are required')
        }
        await api.createUser({
          username: username.trim(),
          password: password.trim(),
          role,
          node_scope: role === 'worker_operator' && nodeScope.trim() ? nodeScope.trim() : undefined,
        })
      } else {
        await api.updateUser(username, {
          role,
          node_scope: role === 'worker_operator' && nodeScope.trim() ? nodeScope.trim() : undefined,
          is_active: isActive,
          password: password.trim() ? password.trim() : undefined,
        })
      }
      setIsModalOpen(false)
      await fetchData()
    } catch (err: any) {
      setFormError(err.message || 'Operation failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteUser = async () => {
    if (!deleteTarget) return
    try {
      setDeleting(true)
      await api.deleteUser(deleteTarget.username)
      setDeleteTarget(null)
      await fetchData()
    } catch (err: any) {
      alert(`Failed to delete user: ${err.message}`)
    } finally {
      setDeleting(false)
    }
  }

  // Get all unique permissions across all roles
  const allPerms = Array.from(new Set(Object.values(permissionsMap).flat()))

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Shield className="text-blue-400" size={24} />
            Users & Role-Based Access Control (RBAC)
          </h1>
          <p className="page-description">
            PBKDF2-hashed credential authentication, role assignment, per-node operator scoping, and permission matrices.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {can('users:manage') && (
            <button
              onClick={handleOpenCreate}
              className="btn btn-primary flex items-center gap-1.5 text-xs"
            >
              <UserPlus size={14} /> Add User
            </button>
          )}
          <button
            onClick={fetchData}
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Users Table Card */}
      <div className="card mb-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3">
          Registered Accounts
        </h2>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Node Scope</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-[#1a1d24]">
                  <td className="font-mono text-xs font-bold text-white flex items-center gap-1.5">
                    {u.username}
                    {u.username === currentUser?.username && (
                      <span className="text-[10px] bg-blue-950 text-blue-300 px-1.5 py-0.2 rounded border border-blue-800">
                        YOU
                      </span>
                    )}
                  </td>
                  <td>
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                        u.role === 'super_admin'
                          ? 'bg-red-950/80 text-red-300 border border-red-800'
                          : u.role === 'orchestrator_operator'
                          ? 'bg-purple-950/80 text-purple-300 border border-purple-800'
                          : u.role === 'worker_operator'
                          ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800'
                          : 'bg-gray-800 text-gray-300'
                      }`}
                    >
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="font-mono text-xs text-secondary">
                    {u.node_scope ? <span className="text-green-400">{u.node_scope}</span> : 'Cluster Wide'}
                  </td>
                  <td>
                    {u.is_active ? (
                      <span className="text-xs text-green-400 flex items-center gap-1 font-mono">
                        <CheckCircle2 size={13} /> Active
                      </span>
                    ) : (
                      <span className="text-xs text-red-400 flex items-center gap-1 font-mono">
                        <XCircle size={13} /> Disabled
                      </span>
                    )}
                  </td>
                  <td className="font-mono text-xs text-secondary">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="font-mono text-xs text-secondary">
                    {u.last_login ? new Date(u.last_login).toLocaleTimeString() : 'Never'}
                  </td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      {can('users:manage') && (
                        <>
                          <button
                            onClick={() => handleOpenEdit(u)}
                            className="btn btn-secondary px-2 py-1 text-xs"
                            title="Edit User"
                          >
                            <Edit size={13} />
                          </button>
                          {u.username !== 'admin' && u.username !== currentUser?.username && (
                            <button
                              onClick={() => setDeleteTarget(u)}
                              className="btn btn-danger px-2 py-1 text-xs"
                              title="Delete User"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Role Permission Matrix Card */}
      <div className="card">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-secondary mb-3">
          RBAC Permission Matrix
        </h2>
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Permission Scope</th>
                <th className="text-center font-mono text-xs text-red-300">SUPER_ADMIN</th>
                <th className="text-center font-mono text-xs text-purple-300">ORCHESTRATOR_OPERATOR</th>
                <th className="text-center font-mono text-xs text-cyan-300">WORKER_OPERATOR</th>
                <th className="text-center font-mono text-xs text-gray-300">VIEWER</th>
              </tr>
            </thead>
            <tbody>
              {allPerms.map((perm) => (
                <tr key={perm}>
                  <td className="font-mono text-xs text-white">{perm}</td>
                  {(['super_admin', 'orchestrator_operator', 'worker_operator', 'viewer'] as UserRole[]).map(
                    (r) => {
                      const granted = (permissionsMap[r] || []).includes(perm)
                      return (
                        <td key={r} className="text-center">
                          {granted ? (
                            <span className="text-emerald-400 font-bold">✓</span>
                          ) : (
                            <span className="text-gray-600">-</span>
                          )}
                        </td>
                      )
                    }
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit User Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="card max-w-md w-full bg-[#14161b] border-[#2d3139]">
            <div className="flex justify-between items-center pb-3 border-b border-[#2d3139] mb-4">
              <h3 className="font-semibold text-base text-white">
                {modalMode === 'create' ? 'Create User Account' : `Edit User: ${username}`}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-white font-mono text-lg"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="bg-red-950/60 border border-red-800 text-red-300 text-xs p-2.5 rounded mb-3">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmitUser} className="space-y-4 text-xs font-mono">
              <div>
                <label className="text-secondary block mb-1">Username:</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={modalMode === 'edit'}
                  required
                  className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500 disabled:opacity-50"
                />
              </div>

              <div>
                <label className="text-secondary block mb-1">
                  {modalMode === 'create' ? 'Password:' : 'Password (leave blank to keep unchanged):'}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required={modalMode === 'create'}
                  className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-secondary block mb-1">Role:</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
                >
                  <option value="viewer">VIEWER (Read-only access)</option>
                  <option value="worker_operator">WORKER_OPERATOR (Node scoped control)</option>
                  <option value="orchestrator_operator">ORCHESTRATOR_OPERATOR (Cluster management)</option>
                  <option value="super_admin">SUPER_ADMIN (Full cluster authority)</option>
                </select>
              </div>

              {role === 'worker_operator' && (
                <div>
                  <label className="text-secondary block mb-1">Assigned Node Scope (Node ID):</label>
                  <input
                    type="text"
                    value={nodeScope}
                    onChange={(e) => setNodeScope(e.target.value)}
                    placeholder="e.g. node-alpha"
                    className="bg-[#0f1013] border border-[#2d3139] text-white p-2 rounded w-full outline-none focus:border-blue-500"
                  />
                </div>
              )}

              {modalMode === 'edit' && (
                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="isActiveCheck"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="cursor-pointer"
                  />
                  <label htmlFor="isActiveCheck" className="text-white cursor-pointer">
                    Account Active / Enabled
                  </label>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-3 border-t border-[#2d3139]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn btn-primary text-xs"
                >
                  {submitting ? 'Saving...' : modalMode === 'create' ? 'Create User' : 'Update User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete User Modal */}
      {deleteTarget && (
        <ConfirmationModal
          isOpen={true}
          title={`Delete User: ${deleteTarget.username}?`}
          message="This action will permanently delete this user account. The user will no longer be able to log in to the TaskMesh control platform."
          confirmLabel="Delete User"
          isDanger={true}
          loading={deleting}
          onConfirm={handleDeleteUser}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}

