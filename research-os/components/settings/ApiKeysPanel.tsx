'use client'

import { useState, useEffect } from 'react'
import { getSettingsStatus, setApiKey, deleteApiKey } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const PROVIDERS = ['gemini', 'mistral', 'openrouter']

interface EditingProvider {
  provider: string
  key: string
}

export function ApiKeysPanel() {
  const [configuredKeys, setConfiguredKeys] = useState<string[]>([])
  const [missingProviders, setMissingProviders] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [editingProvider, setEditingProvider] = useState<EditingProvider | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      setIsLoading(true)
      const data = await getSettingsStatus()
      setConfiguredKeys(data.configured_keys || [])
      setMissingProviders(data.missing_providers || [])
      setError(null)
    } catch (err) {
      console.error('[v0] Error fetching settings:', err)
      setError('Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveKey = async () => {
    if (!editingProvider || !editingProvider.key.trim()) {
      setError('Please enter an API key')
      return
    }

    try {
      setIsLoading(true)
      setError(null)
      await setApiKey(editingProvider.provider, editingProvider.key.trim())
      setSuccess(`${editingProvider.provider} key updated`)
      setEditingProvider(null)
      await fetchSettings()
    } catch (err) {
      console.error('[v0] Error saving key:', err)
      setError('Failed to save API key')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteKey = async (provider: string) => {
    if (!confirm(`Delete ${provider} API key?`)) return

    try {
      setIsLoading(true)
      setError(null)
      await deleteApiKey(provider)
      setSuccess(`${provider} key deleted`)
      await fetchSettings()
    } catch (err) {
      console.error('[v0] Error deleting key:', err)
      setError('Failed to delete API key')
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
      {/* Warnings */}
      {missingProviders.length > 0 && (
        <div className="bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 p-4 rounded">
          <p className="font-semibold text-sm">Missing Configuration</p>
          <p className="text-sm mt-1">
            {missingProviders.join(', ')} configured but no model assigned
          </p>
        </div>
      )}

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

      {/* Providers List */}
      <div className="space-y-3">
        {PROVIDERS.map((provider) => (
          <div
            key={provider}
            className="flex items-center justify-between p-4 border border-border rounded bg-secondary/30"
          >
            <div className="flex-1">
              <p className="font-semibold capitalize">{provider}</p>
              <p className="text-sm text-muted-foreground">
                {configuredKeys.includes(provider) ? 'Configured' : 'Not configured'}
              </p>
            </div>

            {editingProvider?.provider === provider ? (
              <div className="flex gap-2 ml-4 min-w-0 flex-1 max-w-xs">
                <Input
                  type="password"
                  placeholder="Enter API key"
                  value={editingProvider.key}
                  onChange={(e) =>
                    setEditingProvider({
                      ...editingProvider,
                      key: e.target.value,
                    })
                  }
                  className="flex-1"
                />
                <Button
                  size="sm"
                  variant="default"
                  onClick={handleSaveKey}
                  disabled={isLoading}
                >
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditingProvider(null)}
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
                    setEditingProvider({
                      provider,
                      key: '',
                    })
                  }
                  disabled={isLoading}
                >
                  {configuredKeys.includes(provider) ? 'Update' : 'Add'}
                </Button>
                {configuredKeys.includes(provider) && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDeleteKey(provider)}
                    disabled={isLoading}
                  >
                    Delete
                  </Button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
