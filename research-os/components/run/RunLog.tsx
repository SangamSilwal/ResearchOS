'use client'

import { useEffect, useRef, useState } from 'react'
import { subscribeToRunStream, StreamMessage } from '@/lib/stream'

interface RunLogProps {
  runId: string
  isLive: boolean
}

export function RunLog({ runId, isLive }: RunLogProps) {
  const [messages, setMessages] = useState<StreamMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(isLive)
  const [error, setError] = useState<string | null>(null)
  const scrollEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isLive) return

    const unsubscribe = subscribeToRunStream(
      runId,
      (message) => {
        setMessages((prev) => [...prev, message])
      },
      (err) => {
        console.error('[v0] Stream error:', err)
        setError(err.message)
        setIsStreaming(false)
      },
      () => {
        setIsStreaming(false)
      }
    )

    return () => {
      unsubscribe()
    }
  }, [runId, isLive])

  useEffect(() => {
    // Auto-scroll to bottom
    scrollEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full bg-secondary/50 rounded-lg border border-border">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="font-semibold">Agent Output</h3>
        {isStreaming && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            Live
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && !error && (
          <p className="text-muted-foreground text-sm italic">Waiting for agent output...</p>
        )}

        {error && (
          <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-3 rounded text-sm">
            Stream Error: {error}
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-2">
            {msg.type === 'log' && (
              <div className="space-y-1">
                {msg.agent && (
                  <p className="text-xs font-semibold text-blue-600 dark:text-blue-400">
                    {msg.agent}
                  </p>
                )}
                <p className="text-sm text-foreground whitespace-pre-wrap break-words">
                  {msg.content}
                </p>
              </div>
            )}

            {msg.type === 'done' && (
              <div className="bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 p-3 rounded text-sm font-medium">
                Execution Complete
              </div>
            )}

            {msg.type === 'error' && (
              <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-3 rounded text-sm">
                Error: {msg.content}
              </div>
            )}
          </div>
        ))}

        <div ref={scrollEndRef} />
      </div>

      {/* Footer */}
      {!isStreaming && messages.length > 0 && (
        <div className="px-4 py-3 border-t border-border text-xs text-muted-foreground text-center">
          End of output
        </div>
      )}
    </div>
  )
}
