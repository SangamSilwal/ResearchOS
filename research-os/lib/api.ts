import { getAuthHeader, getToken, clearToken } from './auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8080'

export interface Run {
  id: string
  goal: string
  thread_id?: string
  status: 'queued' | 'running' | 'done' | 'error'
  run_type?: 'research' | 'build'
  created_at?: string
  updated_at?: string
  summary?: string
  tasks?: Array<{
    name: string
    status: string
  }>
  flagged_tasks?: string[]
  has_download?: boolean
}

export interface Thread {
  id: string
  name?: string
  created_at?: string
  updated_at?: string
}

export interface ApiError extends Error {
  status?: number
  data?: any
}

/**
 * Make authenticated API request
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers as Record<string, string>),
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  // Handle 401 - unauthorized
  if (response.status === 401) {
    clearToken()
    if (typeof window !== 'undefined') {
      window.location.href = '/auth'
    }
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const error = new Error(`API Error: ${response.status}`) as ApiError
    error.status = response.status
    try {
      error.data = await response.json()
    } catch {
      error.data = null
    }
    throw error
  }

  return response.json() as Promise<T>
}

/**
 * Fetch current user info
 */
export async function getMe() {
  return apiRequest<{ id: string; email: string; name?: string }>('/auth/me')
}

/**
 * Get all runs, optionally filtered by thread
 */
export async function getRuns(
  threadId?: string,
  limit: number = 50
): Promise<Run[]> {
  const params = new URLSearchParams()
  if (threadId) params.append('thread_id', threadId)
  params.append('limit', limit.toString())

  const response = await apiRequest<{ runs: Run[] }>(
    `/api/runs?${params.toString()}`
  )
  return response.runs || []
}

/**
 * Get a specific run
 */
export async function getRun(id: string): Promise<Run> {
  return apiRequest<Run>(`/api/runs/${id}`)
}

/**
 * Create a new run
 */
export async function createRun(
  goal: string,
  threadId?: string
): Promise<Run> {
  return apiRequest<Run>('/api/runs', {
    method: 'POST',
    body: JSON.stringify({
      goal,
      thread_id: threadId,
    }),
  })
}

/**
 * Download run results (returns blob)
 */
export async function downloadRun(id: string): Promise<Blob> {
  const token = getToken()
  const url = `${API_BASE_URL}/api/runs/${id}/download`
  const headers: Record<string, string> = {}

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(url, { headers })

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`)
  }

  return response.blob()
}

/**
 * Get API keys status
 */
export async function getSettingsStatus(): Promise<{
  configured_keys: string[]
  missing_providers: string[]
}> {
  return apiRequest('/api/settings/status')
}

/**
 * Update API key for a provider
 */
export async function setApiKey(
  provider: string,
  apiKey: string,
  label?: string
): Promise<void> {
  await apiRequest(`/api/settings/keys/${provider}`, {
    method: 'PUT',
    body: JSON.stringify({
      api_key: apiKey,
      label,
    }),
  })
}

/**
 * Delete API key for a provider
 */
export async function deleteApiKey(provider: string): Promise<void> {
  await apiRequest(`/api/settings/keys/${provider}`, {
    method: 'DELETE',
  })
}

export interface AgentModelConfig {
  agent_role: string
  provider: string
  model_name: string
  is_default: boolean
}

/**
 * Get configured agent models
 */
export async function getAgentModels(): Promise<
  Record<string, AgentModelConfig>
> {
  return apiRequest('/api/settings/agent-models')
}

/**
 * Update agent models
 */
export async function setAgentModels(
  models: Record<string, AgentModelConfig>
): Promise<void> {
  await apiRequest('/api/settings/agent-models', {
    method: 'PUT',
    body: JSON.stringify(models),
  })
}
