'use client'

import { useState, useEffect } from 'react'
import { getRuns, Run } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface SidebarProps {
  currentRunId?: string
  onSelectRun?: (runId: string) => void
  onCreateNew?: () => void
}

export function Sidebar({ currentRunId, onSelectRun, onCreateNew }: SidebarProps) {
  const [runs, setRuns] = useState<Run[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        setIsLoading(true)
        const data = await getRuns()
        setRuns(data)
        setError(null)
      } catch (err) {
        console.error('[v0] Error fetching runs:', err)
        setError('Failed to load runs')
      } finally {
        setIsLoading(false)
      }
    }

    fetchRuns()
  }, [])

  // Group runs by thread
  const runsByThread = runs.reduce(
    (acc, run) => {
      const threadId = run.thread_id || 'default'
      if (!acc[threadId]) {
        acc[threadId] = []
      }
      acc[threadId].push(run)
      return acc
    },
    {} as Record<string, Run[]>
  )

  return (
    <div className="w-64 h-full bg-secondary/50 border-r border-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <Button
          onClick={onCreateNew}
          variant="default"
          className="w-full"
        >
          New Goal
        </Button>
      </div>

      {/* Runs List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-foreground" />
          </div>
        )}

        {error && (
          <div className="p-4 text-sm text-red-600 dark:text-red-400">{error}</div>
        )}

        {!isLoading && runs.length === 0 && (
          <div className="p-4 text-center text-muted-foreground text-sm">
            No runs yet. Create one to get started.
          </div>
        )}

        {!isLoading && Object.entries(runsByThread).map(([threadId, threadRuns]) => (
          <div key={threadId} className="border-b border-border">
            {/* Thread header (if not default) */}
            {threadId !== 'default' && (
              <div className="px-4 py-2 text-xs font-semibold text-muted-foreground bg-foreground/5">
                Thread {threadId.slice(0, 8)}
              </div>
            )}

            {/* Runs in thread */}
            <div className="space-y-1 p-2">
              {threadRuns.map((run) => (
                <button
                  key={run.id}
                  onClick={() => onSelectRun?.(run.id)}
                  className={`w-full text-left px-3 py-2 rounded text-sm truncate transition-colors ${
                    currentRunId === run.id
                      ? 'bg-blue-600 text-white'
                      : 'hover:bg-foreground/10 text-foreground'
                  }`}
                  title={run.goal}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
                        run.status === 'done'
                          ? 'bg-green-500'
                          : run.status === 'error'
                            ? 'bg-red-500'
                            : run.status === 'running'
                              ? 'bg-blue-500 animate-pulse'
                              : 'bg-yellow-500'
                      }`}
                    />
                    <span className="truncate">{run.goal.slice(0, 30)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(run.created_at || '').toLocaleDateString()}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
