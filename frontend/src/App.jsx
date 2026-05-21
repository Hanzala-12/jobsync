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

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(localStorage.getItem('auth') === 'true')
  const [studentProfileId, setStudentProfileId] = useState(Number(localStorage.getItem('student_profile_id') || 0))

  useEffect(() => {
    const syncProfile = () => setStudentProfileId(Number(localStorage.getItem('student_profile_id') || 0))
    window.addEventListener('storage', syncProfile)
    return () => window.removeEventListener('storage', syncProfile)
  }, [])

  const handleAuth = () => {
    localStorage.setItem('auth', 'true')
    setIsAuthenticated(true)
  }

  const requireStudentProfile = (element) => (studentProfileId ? element : <Navigate to="/student/profile" replace />)

  return (
    <Router>
      {!isAuthenticated ? (
        <Routes>
          <Route path="/login" element={<Login onLogin={handleAuth} />} />
          <Route path="/signup" element={<Signup onSignup={handleAuth} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      ) : (
        <Layout>
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
            <Route path="/student/profile" element={<StudentProfileForm />} />
            <Route path="/student/dashboard" element={requireStudentProfile(<UniversityDashboard />)} />
            <Route path="/student/matches" element={requireStudentProfile(<UniversityMatchList profileId={studentProfileId} />)} />
            <Route path="/student/applications" element={requireStudentProfile(<MyApplications />)} />
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
