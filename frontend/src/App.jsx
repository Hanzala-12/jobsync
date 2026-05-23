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
import { AuthProvider, useAuth } from './contexts/AuthContext'

const AUTH_BYPASS = (import.meta.env.VITE_AUTH_BYPASS || '').toString().toLowerCase() === 'true'

function AppRoutes() {
  const { authLoading, isAuthenticated, studentProfileId, setStudentProfileId, handleAuth, handleLogout } = useAuth()
  const handleStudentProfileCreated = (profileId) => {
    const nextProfileId = Number(profileId) || 0
    setStudentProfileId(nextProfileId)
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
    !isAuthenticated ? (
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
    )
  )
}

function App() {
  return (
    <AuthProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppRoutes />
      </Router>
    </AuthProvider>
  )
}

export default App
