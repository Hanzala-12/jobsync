import { Link, useLocation } from 'react-router-dom'
import './Layout.css'
import searchStream from '../services/searchStream'

const navGroups = [
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

const Layout = ({ children }) => {
  const location = useLocation()
  const mainClass = location.pathname === '/kanban' ? 'app-main app-main-full' : 'app-main'

  return (
    <div className="layout-shell">
      <aside className="sidebar">
        <div className="logo">
          <span>JobSync</span>
          <button
            className="stop-search-btn"
            onClick={() => {
              try {
                if (window.confirm('Stop background search?')) {
                  searchStream.stop()
                  alert('Search stopped')
                }
              } catch (e) {}
            }}
          >
            Stop Search
          </button>
        </div>
        <nav>
          {navGroups.map((group) => (
            <div key={group.label} className="nav-group">
              <p className="nav-group-label">{group.label}</p>
              {group.items.map((item) => {
                const active = location.pathname === item.path
                return (
                  <Link key={item.path} to={item.path} className={`nav-link ${active ? 'active' : ''}`}>
                    {item.label}
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>
      </aside>
      <main className={mainClass}>{children}</main>
    </div>
  )
}

export default Layout
