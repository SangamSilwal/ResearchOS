'use client'

import { useState, useCallback, useEffect } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Header } from '@/components/layout/Header'
import { Sidebar } from '@/components/layout/Sidebar'
import { NewGoalForm } from '@/components/run/NewGoalForm'
import { RunDetail } from '@/components/run/RunDetail'
import { SettingsModal } from '@/components/settings/SettingsModal'

export default function DashboardPage() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleRunCreated = useCallback((runId: string) => {
    setSelectedRunId(runId)
    // Trigger sidebar refresh
    setRefreshKey((prev) => prev + 1)
  }, [])

  const handleRefreshSidebar = useCallback(() => {
    setRefreshKey((prev) => prev + 1)
  }, [])

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen bg-background">
        {/* Header */}
        <Header onSettingsClick={() => setSettingsOpen(true)} />

        {/* Main Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <Sidebar
            key={refreshKey}
            currentRunId={selectedRunId || ''}
            onSelectRun={setSelectedRunId}
            onCreateNew={() => setSelectedRunId(null)}
          />

          {/* Main Panel */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-auto">
              <div className="max-w-6xl mx-auto p-6 space-y-6">
                {/* New Goal Form */}
                <NewGoalForm onRunCreated={handleRunCreated} />

                {/* Run Detail or Empty State */}
                {selectedRunId ? (
                  <RunDetail runId={selectedRunId} />
                ) : (
                  <div className="flex items-center justify-center h-96 text-center">
                    <div className="text-muted-foreground">
                      <p className="text-lg font-semibold">No run selected</p>
                      <p className="text-sm mt-2">
                        Create a new goal or select a run from the sidebar to get started
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Settings Modal */}
        <SettingsModal
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
        />
      </div>
    </ProtectedRoute>
  )
}
