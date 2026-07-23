import { getToken } from './auth'

export interface StreamMessage {
  type: 'log' | 'done' | 'error' | 'status'
  content?: string
  agent?: string
  data?: any
}

export type StreamCallback = (message: StreamMessage) => void
export type StreamErrorCallback = (error: Error) => void
export type StreamCompleteCallback = () => void

/**
 * Subscribe to a run's event stream via SSE
 */
export function subscribeToRunStream(
  runId: string,
  onMessage: StreamCallback,
  onError?: StreamErrorCallback,
  onComplete?: StreamCompleteCallback
): () => void {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8080'
  const token = getToken()
  
  const url = new URL(`${API_BASE_URL}/api/runs/${runId}/stream`)
  if (token) {
    url.searchParams.append('token', token)
  }

  let eventSource: EventSource | null = null

  try {
    eventSource = new EventSource(url.toString())

    eventSource.addEventListener('log', (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage({
          type: 'log',
          content: data.content || data.message,
          agent: data.agent,
        })
      } catch (e) {
        console.error('[v0] Error parsing log event:', e)
      }
    })

    eventSource.addEventListener('done', (event) => {
      try {
        const data = event.data ? JSON.parse(event.data) : {}
        onMessage({
          type: 'done',
          data,
        })
      } catch (e) {
        console.error('[v0] Error parsing done event:', e)
      }
      if (onComplete) onComplete()
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
    })

    eventSource.addEventListener('error', (event) => {
      const error = new Error('Stream error')
      if (onError) onError(error)
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
    })

    eventSource.onerror = () => {
      const error = new Error('EventSource connection lost')
      if (onError) onError(error)
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
    }
  } catch (error) {
    const err = error instanceof Error ? error : new Error('Stream subscription failed')
    if (onError) onError(err)
  }

  // Return unsubscribe function
  return () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }
}
