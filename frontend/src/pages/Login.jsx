import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import './Auth.css'

function Login({ onLogin }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
    localStorage.setItem('auth', 'true')
    onLogin?.()
    navigate('/', { replace: true })
  }

  return (
    <div className="auth-shell">
      <aside className="auth-hero">
        <div className="auth-brand" style={{ marginBottom: 0 }}>
          <div className="auth-mark" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <span style={{ color: '#fff' }}>JobSync</span>
        </div>
        <div>
          <p className="auth-hero-title">Your job search, systematized.</p>
          <p className="auth-hero-copy">Track every application. Optimize every resume. Interview with confidence.</p>
        </div>
        <p className="auth-hero-footer">© 2026 JobSync</p>
      </aside>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-brand">
            <div className="auth-mark" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <span>JobSync</span>
          </div>

          <h1>Welcome back</h1>
          <p className="subtitle">Log in to continue tracking your applications and job matches.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
            </div>
            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" />
            </div>
            <div className="auth-actions">
              <Button type="submit" className="w-full">Log in</Button>
              <p className="auth-link">Don’t have an account? <Link to="/signup">Sign up</Link></p>
            </div>
          </form>
        </div>
      </section>
    </div>
  )
}

export default Login
