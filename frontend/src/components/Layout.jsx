import { Link, useLocation } from 'react-router-dom'
import { 
  Home, FileText, Briefcase, ClipboardList, 
  FileEdit, MessageSquare, TrendingUp, Kanban, Mic, Zap
} from 'lucide-react'
import './Layout.css'

const Layout = ({ children }) => {
  const location = useLocation()

  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/resume', icon: FileText, label: 'Resume' },
    { path: '/jobs', icon: Briefcase, label: 'Jobs' },
    { path: '/applications', icon: ClipboardList, label: 'Applications' },
    { path: '/kanban', icon: Kanban, label: 'Kanban Board' },
    { path: '/cover-letter', icon: FileEdit, label: 'Cover Letter' },
    { path: '/interview', icon: MessageSquare, label: 'Interview Prep' },
    { path: '/mock-interview', icon: Mic, label: 'Mock Interview' },
    { path: '/skill-gap', icon: TrendingUp, label: 'Skill Gap' },
    { path: '/daily-scout', icon: Zap, label: 'Daily Scout' },
  ]

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="logo">JobSync Pro</h1>
          <p className="tagline">AI-Powered Job Hunting</p>
        </div>
        <nav className="nav">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

export default Layout
