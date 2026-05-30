import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { authAPI, setAuthToken } from '../api/client'
import './Auth.css'

function Login({ onLogin }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await authAPI.login({ email, password })
      setAuthToken(response.data?.access_token || '')
      onLogin?.(response.data)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.userMessage || 'Could not log in')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <aside className="auth-hero">
        <div className="hero-content fade-up">
          <div className="hero-logo-lockup">
            <div className="hero-mark">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <span className="hero-brand">JobSync</span>
          </div>
          <h1 className="hero-title">Sync yourself with your dream job</h1>
          <ul className="hero-features">
            <li><span>🎯</span> Smart job matching</li>
            <li><span>📊</span> Application tracking</li>
          </ul>
        </div>
      </aside>

      <section className="auth-panel fade-up">
        <div className="auth-card">
          <h1>Welcome back</h1>
          <p className="subtitle">Log in to track your career journey.</p>

          {error && <p className="auth-error">{error}</p>}

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
              <Button type="submit" loading={loading} className="auth-submit">Log in</Button>
              <p className="auth-link">Don't have an account? <Link to="/signup">Sign up</Link></p>
            </div>
          </form>
        </div>
      </section>
    </div>
  )
}

export default Login
