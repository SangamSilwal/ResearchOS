'use client'

import { useState, useEffect } from 'react'
import { getAgentModels, setAgentModels, AgentModelConfig } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// Must match the backend's AgentRole enum (web/models.py)
const AGENT_ROLES = [
  'orchestrator',
  'researcher',
  'architect_a',
  'architect_b',
  'judge',
  'planner',
  'coder',
  'critic',
  'summarizer',
]

interface EditingModel {
  role: string
  provider: string
  model: string
}

export function AgentModelsPanel() {
  const [models, setModels] = useState<Record<string, AgentModelConfig>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [editingRole, setEditingRole] = useState<EditingModel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchModels()
  }, [])

  const toRoleMap = (entries: AgentModelConfig[]): Record<string, AgentModelConfig> => {
    const byRole: Record<string, AgentModelConfig> = {}
    for (const entry of entries || []) {
      byRole[entry.agent_role] = entry
    }
    return byRole
  }

  const fetchModels = async () => {
    try {
      setIsLoading(true)
      const data = await getAgentModels()
      setModels(toRoleMap(data))
      setError(null)
    } catch (err) {
      console.error('[v0] Error fetching models:', err)
      setError('Failed to load agent models')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveModel = async () => {
    if (!editingRole || !editingRole.provider.trim() || !editingRole.model.trim()) {
      setError('Please enter provider and model')
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      // Backend expects { [role]: "provider/model-name" }
      const modelKey = `${editingRole.provider.trim()}/${editingRole.model.trim()}`
      const data = await setAgentModels({ [editingRole.role]: modelKey })

      setModels(toRoleMap(data))
      setSuccess(`${editingRole.role} model updated`)
      setEditingRole(null)
    } catch (err) {
      console.error('[v0] Error saving model:', err)
      setError('Failed to save agent model')
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

      {/* Model Assignment Table */}
      <div className="space-y-3">
        {AGENT_ROLES.map((role) => {
          const model = models[role]
          const isEditing = editingRole?.role === role

          return (
            <div
              key={role}
              className="flex items-center justify-between p-4 border border-border rounded bg-secondary/30"
            >
              <div className="flex-1">
                <p className="font-semibold capitalize">{role.replace(/_/g, ' ')}</p>
                {model && (
                  <p className="text-sm text-muted-foreground">
                    {model.provider}/{model.model_name}
                    {model.is_default && ' (default)'}
                  </p>
                )}
              </div>

              {isEditing ? (
                <div className="flex gap-2 ml-4 flex-1 max-w-sm">
                  <Input
                    placeholder="provider"
                    value={editingRole.provider}
                    onChange={(e) =>
                      setEditingRole({
                        ...editingRole,
                        provider: e.target.value,
                      })
                    }
                    className="flex-1"
                  />
                  <Input
                    placeholder="model"
                    value={editingRole.model}
                    onChange={(e) =>
                      setEditingRole({
                        ...editingRole,
                        model: e.target.value,
                      })
                    }
                    className="flex-1"
                  />
                  <Button
                    size="sm"
                    variant="default"
                    onClick={handleSaveModel}
                    disabled={isLoading}
                  >
                    Save
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditingRole(null)}
                    disabled={isLoading}
                  >
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
                    {model && !model.is_default ? 'Edit' : 'Assign'}
                  </Button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
