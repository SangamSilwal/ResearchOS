'use client'

import { useEffect, useState } from 'react'
import { Run, getRun, downloadRun } from '@/lib/api'
import { StatusBadge } from '@/components/common/StatusBadge'
import { RunLog } from './RunLog'
import { Button } from '@/components/ui/button'

interface RunDetailProps {
  runId: string
}

export function RunDetail({ runId }: RunDetailProps) {
  const [run, setRun] = useState<Run | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRun = async () => {
      try {
        setIsLoading(true)
        const data = await getRun(runId)
        setRun(data)
        setError(null)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load run'
        setError(message)
        console.error('[v0] Error fetching run:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchRun()
  }, [runId])

  const handleDownload = async () => {
    if (!run?.has_download) return

    try {
      setIsDownloading(true)
      const blob = await downloadRun(runId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `run-${runId}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('[v0] Download error:', err)
      setError('Failed to download run')
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-foreground" />
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="p-6 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded-lg">
        <p className="font-semibold">Error loading run</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    )
  }

  const isLive = run.status === 'running' || run.status === 'queued'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold break-words">{run.goal}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {new Date(run.created_at || '').toLocaleString()}
            </p>
          </div>
          <StatusBadge status={run.status} />
        </div>

        {run.run_type && (
          <p className="text-sm text-muted-foreground">
            Type: <span className="font-semibold capitalize">{run.run_type}</span>
          </p>
        )}
      </div>

      {/* Live Log */}
      <div className="h-96">
        <RunLog runId={runId} isLive={isLive} />
      </div>

      {/* Results Section (when done) */}
      {run.status === 'done' && (
        <div className="space-y-4 border-t border-border pt-6">
          {run.summary && (
            <div>
              <h3 className="font-semibold mb-2">Summary</h3>
              <p className="text-sm text-foreground whitespace-pre-wrap">{run.summary}</p>
            </div>
          )}

          {run.tasks && run.tasks.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Tasks</h3>
              <div className="space-y-2">
                {run.tasks.map((task, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 p-2 bg-secondary rounded border border-border"
                  >
                    <span className="text-sm font-medium">{task.name}</span>
                    <span className="text-xs px-2 py-1 rounded bg-foreground/10">
                      {task.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {run.flagged_tasks && run.flagged_tasks.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Flagged Issues</h3>
              <div className="space-y-2">
                {run.flagged_tasks.map((task, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-2 bg-yellow-100 dark:bg-yellow-900 rounded border border-yellow-300 dark:border-yellow-700"
                  >
                    <span className="text-yellow-700 dark:text-yellow-300 text-sm">⚠</span>
                    <span className="text-sm text-yellow-800 dark:text-yellow-100">{task}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {run.has_download && (
            <Button
              onClick={handleDownload}
              disabled={isDownloading}
              className="w-full"
            >
              {isDownloading ? 'Downloading...' : 'Download Results'}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
