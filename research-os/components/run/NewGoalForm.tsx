'use client'

import { useState } from 'react'
import { createRun } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface NewGoalFormProps {
  onRunCreated?: (runId: string) => void
}

export function NewGoalForm({ onRunCreated }: NewGoalFormProps) {
  const [goal, setGoal] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!goal.trim()) {
      setError('Please enter a goal')
      return
    }

    try {
      setIsLoading(true)
      setError(null)
      const run = await createRun(goal.trim())
      setGoal('')
      if (onRunCreated) {
        onRunCreated(run.id)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create run'
      setError(message)
      console.error('[v0] Error creating run:', err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder="Enter your research goal or development task..."
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={isLoading}
          className="flex-1"
        />
        <Button type="submit" disabled={isLoading || !goal.trim()}>
          {isLoading ? 'Creating...' : 'Start'}
        </Button>
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}
