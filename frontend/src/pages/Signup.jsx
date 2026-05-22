import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { authAPI, setAuthToken } from '../api/client'
import './Auth.css'

function Signup({ onSignup }) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await authAPI.signup({ email, password })
      setAuthToken(response.data?.access_token || '')
      onSignup?.(response.data)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.userMessage || 'Could not create your account')
    } finally {
      setLoading(false)
    }
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
          <p className="auth-hero-title">Build a cleaner job hunt from day one.</p>
          <p className="auth-hero-copy">Create a workspace for applications, resumes, cover letters, and interview prep.</p>
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

          <h1>Create your account</h1>
          <p className="subtitle">Sign up to start managing your job search in one place.</p>

          {error && <p className="auth-error">{error}</p>}

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="name">Full name</label>
              <input id="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" />
            </div>
            <div className="auth-field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
            </div>
            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Create a password" />
            </div>
            <div className="auth-actions">
              <Button type="submit" className="w-full" loading={loading}>Sign up</Button>
              <p className="auth-link">Already have an account? <Link to="/login">Log in</Link></p>
            </div>
          </form>
        </div>
      </section>
    </div>
  )
}

export default Signup
