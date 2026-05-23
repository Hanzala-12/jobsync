import React, { createContext, useContext, useEffect, useState } from 'react'
import { authAPI, clearAuthToken, getStoredAuthToken, setAuthToken, setRefreshToken, studentAPI } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authLoading, setAuthLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [studentProfileId, setStudentProfileId] = useState(0)

  useEffect(() => {
    const bootstrap = async () => {
      const token = getStoredAuthToken()
      if (!token) {
        setAuthLoading(false)
        return
      }

      setAuthToken(token)
      try {
        const [, profileResponse] = await Promise.all([
          authAPI.me(),
          studentAPI.listProfiles().catch(() => null),
        ])
        setIsAuthenticated(true)
        const profileId = Number(profileResponse?.data?.selected_profile_id || 0)
        setStudentProfileId(profileId)
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
    if (authData?.refresh_token) {
      setRefreshToken(authData.refresh_token)
    }
    setIsAuthenticated(true)

    try {
      const response = await studentAPI.listProfiles()
      const profileId = Number(response.data?.selected_profile_id || 0)
      setStudentProfileId(profileId)
    } catch {
      setStudentProfileId(0)
    }
  }

  const handleLogout = () => {
    authAPI.logout().catch(() => null)
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
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export default AuthContext
