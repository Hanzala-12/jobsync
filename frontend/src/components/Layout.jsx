import { Link, useLocation, useNavigate } from 'react-router-dom'
import './Layout.css'

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
    label: 'STUDY WORKSPACE',
    items: [
      { path: '/student/dashboard', label: 'Dashboard' },
      { path: '/student/profile', label: 'Student Profile' },
    ],
  },
  {
    label: 'DISCOVER',
    items: [
      { path: '/student/search', label: 'University Search' },
      { path: '/student/matches', label: 'Match Recommendations' },
      { path: '/student/scholarships', label: 'Scholarships' },
    ],
  },
  {
    label: 'TRACK',
    items: [
      { path: '/student/saved', label: 'Saved Universities' },
      { path: '/student/applications', label: 'Study Applications' },
    ],
  },
]

const Layout = ({ children, studentProfileId = 0, onLogout }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const mainClass = location.pathname === '/kanban' ? 'app-main app-main-full' : 'app-main'
  const isStudyRoute = location.pathname.startsWith('/student')
  const activeMode = isStudyRoute ? 'study' : 'jobs'

  const navGroups = activeMode === 'study' ? studyNavGroups : jobNavGroups

  const goToMode = (mode) => {
    if (mode === 'jobs') {
      navigate('/')
      return
    }

    navigate(studentProfileId ? '/student/dashboard' : '/student/profile')
  }

  return (
    <div className="layout-shell">
      <header className="workspace-header">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <div>
            <span className="workspace-brand">JobSync</span>
            <p className="workspace-subtitle">Switch between job hunting and study abroad workspaces</p>
          </div>
        </div>

        <div className="workspace-tabs" role="tablist" aria-label="Workspace mode">
          <button
            type="button"
            className={`workspace-tab ${activeMode === 'jobs' ? 'active' : ''}`}
            aria-selected={activeMode === 'jobs'}
            onClick={() => goToMode('jobs')}
          >
            <span>Jobs</span>
            <strong>Job search</strong>
          </button>
          <button
            type="button"
            className={`workspace-tab ${activeMode === 'study' ? 'active' : ''}`}
            aria-selected={activeMode === 'study'}
            onClick={() => goToMode('study')}
          >
            <span>Study</span>
            <strong>University planning</strong>
          </button>
        </div>

        <button className="logout-btn header-logout" onClick={() => onLogout?.()}>
          <span aria-hidden="true">→</span>
          Log out
        </button>
      </header>

      <aside className="sidebar">
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
            <button className="logout-btn" onClick={() => onLogout?.()}>
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
