'use client'

import { useState, useEffect } from 'react'
import { getAgentModels, setAgentModels, AgentModelConfig } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const AGENT_ROLES = [
  'researcher',
  'writer',
  'analyzer',
  'coder',
  'reviewer',
  'planner',
  'executor',
  'validator',
  'optimizer',
]

interface EditingModel {
  role: string
  provider: string
  model: string
}

export function AgentModelsPanel() {
  // Keep the raw backend dict (keyed by index) as the source of truth
  const [rawModels, setRawModels] = useState<Record<string, AgentModelConfig>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [editingRole, setEditingRole] = useState<EditingModel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchModels()
  }, [])

  const fetchModels = async () => {
    try {
      setIsLoading(true)
      const data = await getAgentModels()
      setRawModels(data || {})
      setError(null)
    } catch (err) {
      console.error('[v0] Error fetching models:', err)
      setError('Failed to load agent models')
    } finally {
      setIsLoading(false)
    }
  }

  // Helper: find the entry (and its key) for a given role, if any
  const findEntryForRole = (role: string) => {
    const entry = Object.entries(rawModels).find(
      ([, v]) => v.agent_role === role
    )
    return entry ? { key: entry[0], value: entry[1] } : null
  }

  const nextFreeKey = () => {
    const numericKeys = Object.keys(rawModels)
      .map((k) => parseInt(k, 10))
      .filter((n) => !isNaN(n))
    const max = numericKeys.length ? Math.max(...numericKeys) : -1
    return String(max + 1)
  }

  const handleSaveModel = async () => {
    if (!editingRole || !editingRole.provider.trim() || !editingRole.model.trim()) {
      setError('Please enter provider and model')
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      const existing = findEntryForRole(editingRole.role)
      const key = existing ? existing.key : nextFreeKey()

      const updatedModels: Record<string, AgentModelConfig> = {
        ...rawModels,
        [key]: {
          agent_role: editingRole.role,
          provider: editingRole.provider.trim(),
          model_name: editingRole.model.trim(),
          is_default: existing?.value.is_default ?? false,
        },
      }

      await setAgentModels(updatedModels)
      setRawModels(updatedModels)
      setSuccess(`${editingRole.role} model updated`)
      setEditingRole(null)
    } catch (err) {
      console.error('[v0] Error saving model:', err)
      setError('Failed to save agent model')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearModel = async (role: string) => {
    if (!confirm(`Clear ${role} model assignment?`)) return

    try {
      setIsLoading(true)
      setError(null)
      const existing = findEntryForRole(role)
      if (!existing) return

      const updatedModels = { ...rawModels }
      delete updatedModels[existing.key]

      await setAgentModels(updatedModels)
      setRawModels(updatedModels)
      setSuccess(`${role} model cleared`)
    } catch (err) {
      console.error('[v0] Error clearing model:', err)
      setError('Failed to clear agent model')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 p-4 rounded text-sm">
          {success}
        </div>
      )}

      <div className="space-y-3">
        {AGENT_ROLES.map((role) => {
          const entry = findEntryForRole(role)
          const model = entry?.value
          const isEditing = editingRole?.role === role

          return (
            <div
              key={role}
              className="flex items-center justify-between p-4 border border-border rounded bg-secondary/30"
            >
              <div className="flex-1">
                <p className="font-semibold capitalize">{role}</p>
                {model && (
                  <p className="text-sm text-muted-foreground">
                    {model.provider}/{model.model_name}
                  </p>
                )}
              </div>

              {isEditing ? (
                <div className="flex gap-2 ml-4 flex-1 max-w-sm">
                  <Input
                    placeholder="provider"
                    value={editingRole.provider}
                    onChange={(e) =>
                      setEditingRole({ ...editingRole, provider: e.target.value })
                    }
                    className="flex-1"
                  />
                  <Input
                    placeholder="model"
                    value={editingRole.model}
                    onChange={(e) =>
                      setEditingRole({ ...editingRole, model: e.target.value })
                    }
                    className="flex-1"
                  />
                  <Button size="sm" variant="default" onClick={handleSaveModel} disabled={isLoading}>
                    Save
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingRole(null)} disabled={isLoading}>
                    Cancel
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2 ml-4">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      setEditingRole({
                        role,
                        provider: model?.provider || '',
                        model: model?.model_name || '',
                      })
                    }
                    disabled={isLoading}
                  >
                    {model ? 'Edit' : 'Assign'}
                  </Button>
                  {model && (
                    <Button size="sm" variant="outline" onClick={() => handleClearModel(role)} disabled={isLoading}>
                      Clear
                    </Button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}