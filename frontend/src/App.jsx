import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Resume from './pages/Resume'
import Jobs from './pages/Jobs'
import Profile from './pages/Profile'
import Applications from './pages/Applications'
import CoverLetter from './pages/CoverLetter'
import Interview from './pages/Interview'
import SkillGap from './pages/SkillGap'
import Kanban from './pages/Kanban'
import MockInterview from './pages/MockInterview'
import DailyScout from './pages/DailyScout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import StudentProfileForm from './components/StudentProfileForm'
import UniversityDashboard from './components/UniversityDashboard'
import UniversityMatchList from './components/UniversityMatchList'
import MyApplications from './components/MyApplications'
import StudentUniversitySearch from './components/StudentUniversitySearch'
import StudentSavedUniversities from './components/StudentSavedUniversities'
import StudentScholarships from './components/StudentScholarships'
import { authAPI, clearAuthToken, getStoredAuthToken, setAuthToken, studentAPI } from './api/client'

const AUTH_BYPASS = true

function App() {
  const [authLoading, setAuthLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [studentProfileId, setStudentProfileId] = useState(0)

  useEffect(() => {
    const bootstrap = async () => {
      if (AUTH_BYPASS) {
        setIsAuthenticated(true)
        setStudentProfileId(0)
        setAuthLoading(false)
        return
      }

      const token = getStoredAuthToken()
      if (!token) {
        setAuthLoading(false)
        return
      }

      setAuthToken(token)
      try {
        const [, profileResponse] = await Promise.all([
          authAPI.me(),
          studentAPI.getCurrentProfile().catch(() => null),
        ])
        setIsAuthenticated(true)
        const profileId = Number(profileResponse?.data?.id || 0)
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

    try {
      const response = await studentAPI.getCurrentProfile()
      const profileId = Number(response.data?.id || 0)
      setStudentProfileId(profileId)
    } catch {
      setStudentProfileId(0)
    }
  }

  const handleStudentProfileCreated = (profileId) => {
    setStudentProfileId(Number(profileId || 0))
    setStudyMode(true)
  }

  const handleLogout = () => {
    clearAuthToken()
    setIsAuthenticated(false)
    setStudentProfileId(0)
  }

  if (authLoading) {
    return (
      <div className="auth-shell">
        <section className="auth-panel">
          <div className="auth-card">
            <h1>Loading your workspace</h1>
            <p className="subtitle">Checking your session and study profile...</p>
          </div>
        </section>
      </div>
    )
  }

  return (
    <Router>
      {!isAuthenticated ? (
        <Routes>
          <Route path="/login" element={<Login onLogin={handleAuth} />} />
          <Route path="/signup" element={<Signup onSignup={handleAuth} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      ) : (
        <Layout
          studentProfileId={studentProfileId}
          onLogout={handleLogout}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/resume" element={<Resume />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/applications" element={<Applications />} />
            <Route path="/kanban" element={<Kanban />} />
            <Route path="/cover-letter" element={<CoverLetter />} />
            <Route path="/interview" element={<Interview />} />
            <Route path="/mock-interview" element={<MockInterview />} />
            <Route path="/skill-gap" element={<SkillGap />} />
            <Route path="/daily-scout" element={<DailyScout />} />
            <Route path="/student" element={<Navigate to={studentProfileId ? '/student/dashboard' : '/student/profile'} replace />} />
            <Route path="/student/profile" element={<StudentProfileForm onCreated={handleStudentProfileCreated} />} />
            <Route path="/student/dashboard" element={<UniversityDashboard profileId={studentProfileId} />} />
            <Route path="/student/search" element={<StudentUniversitySearch profileId={studentProfileId} />} />
            <Route path="/student/matches" element={<UniversityMatchList profileId={studentProfileId} />} />
            <Route path="/student/saved" element={<StudentSavedUniversities profileId={studentProfileId} />} />
            <Route path="/student/applications" element={<MyApplications profileId={studentProfileId} />} />
            <Route path="/student/scholarships" element={<StudentScholarships profileId={studentProfileId} />} />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="/signup" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      )}
    </Router>
  )
}

export default App
