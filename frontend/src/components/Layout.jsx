import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Briefcase,
  CheckSquare,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  PencilLine,
  Settings,
  Target,
  User,
  Video,
  X,
  Bell,
  Upload,
} from 'lucide-react'

const navigationItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/jobs', label: 'Jobs', icon: Briefcase },
  { path: '/applications', label: 'Applications', icon: CheckSquare },
  { path: '/kanban', label: 'Kanban Board', icon: LayoutDashboard },
  { path: '/resume', label: 'Resume', icon: FileText },
  { path: '/cover-letter', label: 'Cover Letter', icon: FileText },
  { path: '/interview', label: 'Interview Prep', icon: MessageSquare },
  { path: '/mock-interview', label: 'Mock Interview', icon: Video },
  { path: '/skill-gap', label: 'Skill Gap', icon: Target },
]

const routeTitles = {
  '/': 'Dashboard',
  '/jobs': 'Jobs',
  '/applications': 'Applications',
  '/kanban': 'Kanban Board',
  '/resume': 'Resume',
  '/cover-letter': 'Cover Letter',
  '/interview': 'Interview Prep',
  '/mock-interview': 'Mock Interview',
  '/skill-gap': 'Skill Gap',
  '/settings': 'Settings',
}

const avatarStorageKey = 'jobsync_account_avatar'
const avatarModeStorageKey = 'jobsync_account_avatar_mode'
const avatarPresetStorageKey = 'jobsync_account_avatar_preset'

const avatarPresets = [
  {
    id: 'azure',
    label: 'Azure',
    colorStart: '#3b82f6',
    colorEnd: '#60a5fa',
  },
  {
    id: 'indigo',
    label: 'Indigo',
    colorStart: '#4f46e5',
    colorEnd: '#818cf8',
  },
  {
    id: 'emerald',
    label: 'Emerald',
    colorStart: '#059669',
    colorEnd: '#34d399',
  },
  {
    id: 'slate',
    label: 'Slate',
    colorStart: '#334155',
    colorEnd: '#64748b',
  },
]

const defaultAvatarPreset = avatarPresets[0]

const createAvatarSvg = (preset) => {
  const { colorStart, colorEnd, label } = preset
  const safeLabel = String(label || 'U').slice(0, 1).toUpperCase()
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${colorStart}" />
          <stop offset="100%" stop-color="${colorEnd}" />
        </linearGradient>
      </defs>
      <circle cx="80" cy="80" r="80" fill="url(#bg)" />
      <circle cx="80" cy="66" r="28" fill="rgba(255,255,255,0.92)" />
      <path d="M40 132c7-22 24-34 40-34s33 12 40 34" fill="rgba(255,255,255,0.92)" />
      <text x="80" y="88" text-anchor="middle" font-size="30" font-family="Inter, Arial, sans-serif" font-weight="700" fill="#0f172a">${safeLabel}</text>
    </svg>
  `
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg.trim())}`
}

const Layout = ({ children, studentProfileId = 0, onLogout }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const accountMenuRef = useRef(null)
  const avatarInputRef = useRef(null)
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const [avatarMode, setAvatarMode] = useState(() => (typeof window !== 'undefined' ? window.localStorage.getItem(avatarModeStorageKey) || 'preset' : 'preset'))
  const [avatarPreset, setAvatarPreset] = useState(() => (typeof window !== 'undefined' ? window.localStorage.getItem(avatarPresetStorageKey) || defaultAvatarPreset.id : defaultAvatarPreset.id))
  const [avatarSrc, setAvatarSrc] = useState(() => (typeof window !== 'undefined' ? window.localStorage.getItem(avatarStorageKey) || '' : ''))
  const isKanban = location.pathname === '/kanban'
  const currentTitle = routeTitles[location.pathname] || 'Dashboard'

  const selectedPreset = useMemo(() => avatarPresets.find((item) => item.id === avatarPreset) || defaultAvatarPreset, [avatarPreset])
  const avatarPreview = avatarMode === 'upload' && avatarSrc ? avatarSrc : createAvatarSvg(selectedPreset)

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(avatarModeStorageKey, avatarMode)
    window.localStorage.setItem(avatarPresetStorageKey, avatarPreset)
    if (avatarSrc) {
      window.localStorage.setItem(avatarStorageKey, avatarSrc)
    }
  }, [avatarMode, avatarPreset, avatarSrc])

  useEffect(() => {
    const handlePointerDown = (event) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setAccountMenuOpen(false)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    window.addEventListener('touchstart', handlePointerDown)
    return () => {
      window.removeEventListener('mousedown', handlePointerDown)
      window.removeEventListener('touchstart', handlePointerDown)
    }
  }, [])

  return (
    <div className="js-layout-shell">
      <input id="js-sidebar-toggle" className="js-sidebar-toggle" type="checkbox" aria-hidden="true" />

      <div className="js-layout">
        <label htmlFor="js-sidebar-toggle" className="js-sidebar-backdrop" aria-hidden="true" />

        <aside className="js-sidebar">
          <div className="js-sidebar-top">
            <button className="js-brand" type="button" onClick={() => navigate('/')}>
              <span className="js-brand-mark">JP</span>
              <span className="js-brand-copy">
                <strong>JobSync Pro</strong>
                <span>Career workspace</span>
              </span>
            </button>

            <label htmlFor="js-sidebar-toggle" className="js-sidebar-close" aria-label="Close navigation">
              <X size={18} />
            </label>
          </div>

          <nav className="js-sidebar-nav" aria-label="Primary">
            {navigationItems.map((item) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`js-nav-item ${active ? 'is-active' : ''}`}
                >
                  <span className="js-nav-icon">
                    <Icon size={18} strokeWidth={active ? 2.4 : 2} />
                  </span>
                  <span className="js-nav-label">{item.label}</span>
                </Link>
              )
            })}
          </nav>

        </aside>

        <div className={`js-main-shell ${isKanban ? 'is-full' : ''}`}>
          <header className="js-header">
            <div className="js-header-left">
              <label htmlFor="js-sidebar-toggle" className="js-menu-button" aria-label="Open navigation">
                <Menu size={20} />
              </label>

              <div className="js-header-copy">
                <p className="js-header-kicker">JobSync Pro</p>
                <h1 className="js-header-title">{currentTitle}</h1>
              </div>
            </div>

            <div className="js-header-right">
              <button className="js-icon-button" type="button" aria-label="Notifications">
                <Bell size={18} />
              </button>

              <div className="js-account-menu" ref={accountMenuRef}>
                <button
                  className="js-profile-chip js-profile-chip-circle"
                  type="button"
                  aria-label="Open account menu"
                  aria-expanded={accountMenuOpen}
                  onClick={() => setAccountMenuOpen((current) => !current)}
                >
                  <img className="js-profile-avatar js-profile-avatar-image" src={avatarPreview} alt="Selected account avatar" />
                  <span className="js-profile-edit-badge" aria-hidden="true">
                    <PencilLine size={10} />
                  </span>
                </button>

                {accountMenuOpen ? (
                  <div className="js-account-dropdown" role="menu" aria-label="Account menu">
                    <div className="js-account-hero">
                      <div className="js-account-hero-preview">
                        <img src={avatarPreview} alt="Selected avatar preview" />
                        <button
                          type="button"
                          className="js-account-hero-edit"
                          onClick={() => avatarInputRef.current?.click()}
                          aria-label="Edit avatar"
                        >
                          <PencilLine size={12} />
                        </button>
                      </div>
                      <div className="js-account-hero-copy">
                        <strong>Workspace</strong>
                        <span>Profile avatar</span>
                      </div>
                    </div>

                    <div className="js-account-section-label">Choose an avatar</div>
                    <div className="js-avatar-picker" aria-label="Avatar picker">
                      {avatarPresets.map((preset) => {
                        const active = avatarMode === 'preset' && avatarPreset === preset.id
                        const presetPreview = createAvatarSvg(preset)
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            className={`js-avatar-option ${active ? 'is-active' : ''}`}
                            onClick={() => {
                              setAvatarMode('preset')
                              setAvatarPreset(preset.id)
                            }}
                            aria-label={`Choose ${preset.label} avatar`}
                          >
                            <img src={presetPreview} alt={preset.label} />
                          </button>
                        )
                      })}
                    </div>

                    <div className="js-avatar-actions">
                      <button
                        type="button"
                        className={`js-avatar-action ${avatarMode === 'upload' ? 'is-active' : ''}`}
                        onClick={() => avatarInputRef.current?.click()}
                      >
                        <Upload size={14} />
                        <span>{avatarSrc ? 'Replace photo' : 'Upload photo'}</span>
                      </button>
                      <button
                        type="button"
                        className={`js-avatar-action ${avatarMode === 'preset' ? 'is-active' : ''}`}
                        onClick={() => setAvatarMode('preset')}
                      >
                        <User size={14} />
                        <span>Use preset</span>
                      </button>
                    </div>

                    <input
                      ref={avatarInputRef}
                      type="file"
                      accept="image/*"
                      hidden
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (!file) return
                        const reader = new FileReader()
                        reader.onload = () => {
                          const nextSrc = String(reader.result || '')
                          setAvatarMode('upload')
                          setAvatarSrc(nextSrc)
                        }
                        reader.readAsDataURL(file)
                        event.target.value = ''
                      }}
                    />

                    <div className="js-account-section-label">Quick actions</div>
                    <button type="button" className="js-account-menu-item" onClick={() => { navigate('/profile'); setAccountMenuOpen(false) }}>
                      <User size={16} />
                      <span>Profile</span>
                    </button>
                    <button type="button" className="js-account-menu-item" onClick={() => { navigate('/settings'); setAccountMenuOpen(false) }}>
                      <Settings size={16} />
                      <span>Settings</span>
                    </button>
                    <button type="button" className="js-account-menu-item danger" onClick={() => { setAccountMenuOpen(false); onLogout?.() }}>
                      <LogOut size={16} />
                      <span>Log out</span>
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          </header>

          <main className="js-main-content" data-profile-id={studentProfileId || undefined}>
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}

export default Layout
