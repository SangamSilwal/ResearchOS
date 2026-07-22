'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ApiKeysPanel } from './ApiKeysPanel'
import { AgentModelsPanel } from './AgentModelsPanel'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'keys' | 'models'>('keys')

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background border border-border rounded-lg shadow-lg max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-2xl font-bold">Settings</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-lg"
          >
            ✕
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 px-6 pt-4 border-b border-border">
          <button
            onClick={() => setActiveTab('keys')}
            className={`pb-2 px-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'keys'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            API Keys
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`pb-2 px-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'models'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Agent Models
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'keys' && <ApiKeysPanel />}
          {activeTab === 'models' && <AgentModelsPanel />}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border flex justify-end">
          <Button onClick={onClose}>Done</Button>
        </div>
      </div>
    </div>
  )
}
