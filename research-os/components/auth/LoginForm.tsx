'use client'

import { Button } from '@/components/ui/button'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8080'

export function LoginForm() {
  const handleOAuth = (provider: 'google' | 'github') => {
    const redirectUrl = `${API_BASE_URL}/auth/${provider}/login`
    window.location.href = redirectUrl
  }

  return (
    <div className="flex flex-col gap-4 w-full max-w-sm">
      <div className="text-center mb-6">
        <h1 className="text-3xl font-bold">ResearchOS</h1>
        <p className="text-muted-foreground mt-2">
          Multi-agent AI research and development platform
        </p>
      </div>

      <Button
        onClick={() => handleOAuth('google')}
        size="lg"
        className="w-full"
        variant="outline"
      >
        Continue with Google
      </Button>

      <Button
        onClick={() => handleOAuth('github')}
        size="lg"
        className="w-full"
        variant="outline"
      >
        Continue with GitHub
      </Button>

      <p className="text-xs text-muted-foreground text-center mt-4">
        By signing in, you agree to our Terms of Service and Privacy Policy
      </p>
    </div>
  )
}
