import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  Briefcase, LayoutDashboard, User, FileText, CheckSquare, 
  MessageSquare, Video, Target, TrendingUp, LogOut,
  GraduationCap, Search, Heart, Award
} from 'lucide-react'
import './Layout.css'

const careerLinks = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/profile', label: 'Profile', icon: User },
  { path: '/jobs', label: 'Jobs', icon: Briefcase },
  { path: '/applications', label: 'Applications', icon: CheckSquare },
  { path: '/kanban', label: 'Kanban Board', icon: LayoutDashboard },
  { path: '/resume', label: 'Resume', icon: FileText },
  { path: '/cover-letter', label: 'Cover Letter', icon: FileText },
  { path: '/interview', label: 'Interview Prep', icon: MessageSquare },
  { path: '/mock-interview', label: 'Mock Interview', icon: Video },
  { path: '/skill-gap', label: 'Skill Gap', icon: Target },
  { path: '/daily-scout', label: 'Daily Scout', icon: TrendingUp },
]

const universityLinks = [
  { path: '/student/profile', label: 'Student Profile', icon: User },
  { path: '/student/dashboard', label: 'University Portal', icon: GraduationCap },
  { path: '/student/search', label: 'University Search', icon: Search },
  { path: '/student/matches', label: 'Match Recommendations', icon: Target },
  { path: '/student/saved', label: 'Saved Universities', icon: Heart },
  { path: '/student/applications', label: 'Study Applications', icon: CheckSquare },
  { path: '/student/scholarships', label: 'Scholarships', icon: Award },
]

const Layout = ({ children, studentProfileId = 0, onLogout }) => {
  const location = useLocation()
  const navigate = useNavigate()
  
  const [module, setModule] = useState(() => {
    return location.pathname.startsWith('/student') ? 'university' : 'career'
  })

  useEffect(() => {
    if (location.pathname.startsWith('/student')) {
      setModule('university')
    } else if (location.pathname !== '/login' && location.pathname !== '/signup') {
      setModule('career')
    }
  }, [location.pathname])

  const handleModuleSwitch = (newModule) => {
    setModule(newModule)
    if (newModule === 'career') {
      navigate('/')
    } else {
      navigate('/student')
    }
  }

  // Decide main class based on path if needed
  const isKanban = location.pathname === '/kanban'
  const isStudyRoute = location.pathname.startsWith('/student')

  return (
    <div className={`layout ${isStudyRoute ? 'is-university' : 'is-career'}`}>
      <style>{`
        .custom-nav-item {
          display: flex;
          align-items: center;
          gap: 9px;
          padding: 7px 10px 7px 13px;
          border-radius: 7px;
          font-size: 13px;
          font-weight: 450;
          color: #555;
          text-decoration: none;
          transition: all 0.12s;
          border-left: 3px solid transparent;
          cursor: pointer;
          margin-bottom: 1px;
        }
        .custom-nav-item.career-link:hover {
          background: #f5f5f5;
          color: #111;
        }
        .custom-nav-item.career-active {
          background: #f0f0f0 !important;
          color: #111 !important;
          font-weight: 600 !important;
          border-left: 3px solid #111 !important;
        }
        
        .custom-nav-item.university-link:hover {
          background: #f5f2ff;
          color: #7c3aed;
        }
        .custom-nav-item.university-active {
          background: #ede9fe !important;
          color: #7c3aed !important;
          font-weight: 600 !important;
          border-left: 3px solid #7c3aed !important;
        }
      `}</style>
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-square">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <span className="logo-text">JobSync</span>
        </div>

        <div style={{
          display: 'flex',
          margin: '12px 10px',
          background: '#f0f0f0',
          borderRadius: '8px',
          padding: '3px',
          gap: '2px',
        }}>
          <button
            onClick={() => handleModuleSwitch('career')}
            style={{
              flex: 1,
              padding: '6px 0',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
              fontFamily: 'inherit',
              background: module === 'career' ? '#ffffff' : 'transparent',
              color: module === 'career' ? '#111111' : '#888888',
              boxShadow: module === 'career' ? '0 1px 3px rgba(0,0,0,0.12)' : 'none',
              transition: 'all 0.15s',
            }}
          >
            💼 Career
          </button>
          <button
            onClick={() => handleModuleSwitch('university')}
            style={{
              flex: 1,
              padding: '6px 0',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
              fontFamily: 'inherit',
              background: module === 'university' ? '#7c3aed' : 'transparent',
              color: module === 'university' ? '#ffffff' : '#888888',
              boxShadow: module === 'university' ? '0 1px 3px rgba(124,58,237,0.3)' : 'none',
              transition: 'all 0.15s',
            }}
          >
            🎓 University
          </button>
        </div>

        <div className="sidebar-scroll" style={{ padding: '0 10px' }}>
          {module === 'career' && (
            <div className="nav-section">
              {careerLinks.map((item) => {
                const active = location.pathname === item.path
                const Icon = item.icon
                return (
                  <Link key={item.path} to={item.path} onClick={() => setModule('career')} className={`custom-nav-item career-link ${active ? 'career-active' : ''}`}>
                    <Icon size={16} strokeWidth={active ? 2.5 : 2} style={{ opacity: active ? 1 : 0.75 }} />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </div>
          )}

          {module === 'university' && (
            <div className="nav-section university-section">
              {universityLinks.map((item) => {
                const active = location.pathname === item.path
                const Icon = item.icon
                return (
                  <Link key={item.path} to={item.path} onClick={() => setModule('university')} className={`custom-nav-item university-link ${active ? 'university-active' : ''}`}>
                    <Icon size={16} strokeWidth={active ? 2.5 : 2} style={{ opacity: active ? 1 : 0.75 }} />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <button className="logout-button" onClick={() => onLogout?.()}>
            <LogOut size={15} />
            <span>Log out</span>
          </button>
        </div>
      </aside>

      <main className={`main-content ${isKanban ? 'main-full' : ''}`}>
        {children}
      </main>
    </div>
  )
}

export default Layout
