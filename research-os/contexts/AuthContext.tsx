'use client'

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
} from 'react'
import { User, getToken, setToken, setUser, getUser, clearToken } from '@/lib/auth'

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  logout: () => void
  setAuthToken: (token: string) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [token, setTokenState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    clearToken()
    setUserState(null)
    setTokenState(null)
  }, [])

  const setAuthToken = useCallback((newToken: string) => {
    setToken(newToken)
    setTokenState(newToken)
  }, [])

  useEffect(() => {
    const initAuth = async () => {
      try {
        // Check if token exists in localStorage
        const storedToken = getToken()
        const storedUser = getUser()

        if (storedToken) {
          setTokenState(storedToken)
          if (storedUser) {
            setUserState(storedUser)
          } else {
            // Optionally fetch user info from /auth/me
            // For now, just use the stored token
          }
        }
      } catch (error) {
        console.error('[v0] Auth initialization error:', error)
        logout()
      } finally {
        setIsLoading(false)
      }
    }

    initAuth()
  }, [logout])

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!token,
    logout,
    setAuthToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
