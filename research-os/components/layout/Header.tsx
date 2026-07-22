'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'

interface HeaderProps {
  onSettingsClick?: () => void
}

export function Header({ onSettingsClick }: HeaderProps) {
  const { user, logout } = useAuth()
  const router = useRouter()

  const handleLogout = () => {
    logout()
    router.push('/auth')
  }

  return (
    <header className="h-16 border-b border-border bg-background flex items-center justify-between px-6">
      <div>
        <h1 className="text-2xl font-bold">ResearchOS</h1>
      </div>

      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={onSettingsClick}
        >
          Settings
        </Button>

        <div className="flex items-center gap-3 pl-4 border-l border-border">
          {user && (
            <div className="text-right">
              <p className="text-sm font-medium">{user.name || user.email}</p>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
          >
            Logout
          </Button>
        </div>
      </div>
    </header>
  )
}
