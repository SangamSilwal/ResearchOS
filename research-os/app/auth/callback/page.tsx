'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { setToken, setUser } from '@/lib/auth'
import { useAuth } from '@/contexts/AuthContext'

export default function AuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setAuthToken } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [tokenText, setTokenText] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setError(errorParam)
      return
    }

    if (token) {
      // Check if it looks like raw JSON (dev mode)
      if (token.startsWith('{')) {
        try {
          const parsed = JSON.parse(token)
          setTokenText(JSON.stringify(parsed, null, 2))
          return
        } catch {
          // Not JSON, treat as regular token
        }
      }

      // Store token and redirect to dashboard
      setToken(token)
      setAuthToken(token)

      // Optionally store user info
      const user = searchParams.get('user')
      if (user) {
        try {
          const userObj = JSON.parse(decodeURIComponent(user))
          setUser(userObj)
        } catch {
          // Ignore parse error
        }
      }

      // Redirect to dashboard
      router.push('/dashboard')
    } else {
      setError('No token received from authentication')
    }
  }, [searchParams, router, setAuthToken])

  if (error) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="max-w-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Authentication Error</h1>
          <p className="text-muted-foreground mb-4">{error}</p>
          <a
            href="/auth"
            className="text-blue-600 hover:underline"
          >
            Back to login
          </a>
        </div>
      </main>
    )
  }

  if (tokenText) {
    return (
      <main className="flex items-center justify-center min-h-screen p-4">
        <div className="max-w-2xl w-full">
          <h1 className="text-2xl font-bold mb-4">Token Response (Dev Mode)</h1>
          <pre className="bg-secondary p-4 rounded-lg overflow-auto max-h-96 text-sm">
            {tokenText}
          </pre>
          <p className="text-muted-foreground text-sm mt-4">
            Copy the token from above and add it to localStorage manually, or
            wait for redirect...
          </p>
        </div>
      </main>
    )
  }

  return (
    <main className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-foreground mx-auto mb-4" />
        <p className="text-muted-foreground">Completing authentication...</p>
      </div>
    </main>
  )
}
