import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'
import searchStream from '../services/searchStream'

const jobNavGroups = [
  {
    label: 'MAIN',
    items: [
      { path: '/', label: 'Dashboard' },
      { path: '/profile', label: 'Profile' },
    ],
  },
  {
    label: 'JOBS',
    items: [
      { path: '/jobs', label: 'Jobs' },
      { path: '/daily-scout', label: 'Daily Scout' },
    ],
  },
  {
    label: 'TRACK',
    items: [
      { path: '/applications', label: 'Applications' },
      { path: '/kanban', label: 'Kanban Board' },
    ],
  },
  {
    label: 'TOOLS',
    items: [
      { path: '/resume', label: 'Resume' },
      { path: '/cover-letter', label: 'Cover Letter' },
      { path: '/interview', label: 'Interview Prep' },
      { path: '/mock-interview', label: 'Mock Interview' },
      { path: '/skill-gap', label: 'Skill Gap' },
    ],
  },
]

const studyNavGroups = [
  {
    label: 'STUDY',
    items: [
      { path: '/student/dashboard', label: 'University Dashboard' },
      { path: '/student/profile', label: 'Find Universities' },
      { path: '/student/matches', label: 'My Matches' },
      { path: '/student/applications', label: 'My Applications' },
    ],
  },
]

const Layout = ({ children }) => {
  const location = useLocation()
  const mainClass = location.pathname === '/kanban' ? 'app-main app-main-full' : 'app-main'
  const [studyMode, setStudyMode] = useState(localStorage.getItem('study_mode') === 'true')
  const [hasStudentProfile, setHasStudentProfile] = useState(Boolean(localStorage.getItem('student_profile_id')))

  useEffect(() => {
    const syncState = () => {
      setStudyMode(localStorage.getItem('study_mode') === 'true')
      setHasStudentProfile(Boolean(localStorage.getItem('student_profile_id')))
    }
    window.addEventListener('storage', syncState)
    syncState()
    return () => window.removeEventListener('storage', syncState)
  }, [])

  const navGroups = studyMode && hasStudentProfile ? studyNavGroups : jobNavGroups

  return (
    <div className="layout-shell">
      <aside className="sidebar">
        <div className="logo">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <span>JobSync</span>
          </div>
          <button
            type="button"
            className="mode-toggle"
            onClick={() => {
              const next = !studyMode
              localStorage.setItem('study_mode', next ? 'true' : 'false')
              setStudyMode(next)
            }}
          >
            <span>{studyMode ? 'Study Mode' : 'Job Mode'}</span>
            <strong>{studyMode ? 'Switch to Jobs' : 'Switch to Study'}</strong>
          </button>
        </div>
        <nav>
          {navGroups.map((group) => (
            <div key={group.label} className="nav-group">
              <p className="nav-group-label">{group.label}</p>
              {group.items.map((item) => {
                const active = location.pathname === item.path
                return (
                      <div key={item.path} className={`nav-link-wrap ${active ? 'active' : ''}`}>
                        {active && <span className="nav-active-bar" aria-hidden="true" />}
                        <Link to={item.path} className={`nav-link ${active ? 'active' : ''}`}>
                          {item.label}
                        </Link>
                      </div>
                )
              })}
            </div>
          ))}

          <div className="sidebar-footer">
            <button
              className="logout-btn"
              onClick={() => {
                localStorage.removeItem('auth')
                localStorage.removeItem('student_profile_id')
                localStorage.removeItem('study_mode')
                window.location.reload()
              }}
            >
              <span aria-hidden="true">→</span>
              Log out
            </button>
          </div>
        </nav>
      </aside>
      <main className={`${mainClass} page-enter`}>{children}</main>
    </div>
  )
}

export default Layout
