import React, { createContext, useContext, useEffect, useState } from 'react'
import { authAPI, clearAuthToken, getStoredAuthToken, setAuthToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authLoading, setAuthLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [studentProfileId, setStudentProfileId] = useState(0)

  useEffect(() => {
    const bootstrap = async () => {
      // Attempt to bootstrap from stored access token or by refreshing via HttpOnly cookie
      const token = getStoredAuthToken()
      if (token) {
        setAuthToken(token)
      } else {
        try {
          const refreshResp = await authAPI.refresh().catch(() => null)
          const newAccess = refreshResp?.data?.access_token
          if (newAccess) setAuthToken(newAccess)
        } catch {
          // ignore
        }
      }

      try {
        await authAPI.me()
        setIsAuthenticated(true)
      } catch {
        clearAuthToken()
        setIsAuthenticated(false)
        setStudentProfileId(0)
      } finally {
        setAuthLoading(false)
      }
    }

    bootstrap()

    const handleInvalidation = () => {
      clearAuthToken()
      setIsAuthenticated(false)
      setStudentProfileId(0)
    }

    window.addEventListener('jobsync-auth-invalidated', handleInvalidation)
    return () => window.removeEventListener('jobsync-auth-invalidated', handleInvalidation)
  }, [])

  const handleAuth = async (authData) => {
    if (authData?.access_token) {
      setAuthToken(authData.access_token)
    }
    setIsAuthenticated(true)
  }

  const handleLogout = async () => {
    try {
      await authAPI.logout()
    } catch {
      // Clear local auth state even if the network call fails.
    }
    clearAuthToken()
    setIsAuthenticated(false)
    setStudentProfileId(0)
  }

  return (
    <AuthContext.Provider value={{ authLoading, isAuthenticated, studentProfileId, setStudentProfileId, handleAuth, handleLogout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    // Return safe defaults to avoid runtime crashes when called outside provider
    return {
      authLoading: true,
      isAuthenticated: false,
      studentProfileId: 0,
      setStudentProfileId: () => {},
      handleAuth: async () => {},
      handleLogout: () => {},
    }
  }
  return ctx
}

export default AuthContext
