import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './Button'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

function StudentSavedUniversities({ profileId }) {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadSaved = async () => {
    if (!profileId) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await studentAPI.getSavedUniversities(profileId)
      const d = response.data
      setItems(Array.isArray(d) ? d : (d?.saved || d?.data || []))
    } catch (err) {
      setError(err.userMessage || 'Could not load saved universities')
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSaved()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId])

  return (
    <div className="study-page">
      <section className="study-hero">
        <div>
          <p className="section-label">Study Mode</p>
          <h1>Saved universities</h1>
          <p className="muted">Your shortlist stays in one place so you can compare, revisit, and apply later.</p>
        </div>
        <div className="study-hero-actions">
          <Button onClick={() => navigate('/student/search')}>Search Universities</Button>
          <Button variant="secondary" onClick={() => navigate('/student/applications')}>Open Applications</Button>
        </div>
      </section>

      {error && <p className="muted-small" style={{ color: 'var(--danger)' }}>{error}</p>}
      {loading ? (
        <div className="study-panel"><div className="loading-block">Loading saved universities...</div></div>
      ) : !profileId ? (
        <div className="study-panel">
          <div className="empty-block">
            <div>
              <p className="section-label">Start here</p>
              <h2>Create your profile first</h2>
              <p>Saved universities are tied to your student profile.</p>
              <div style={{ marginTop: 12 }}>
                <Button onClick={() => navigate('/student/profile')}>Create Profile</Button>
              </div>
            </div>
          </div>
        </div>
      ) : items.length > 0 ? (
        <div className="saved-grid">
          {items.map((item) => (
            <article key={item.id} className="saved-card">
              <div className="saved-card-top">
                <div>
                  <span className="ranking-pill">{item.university?.country || 'Unknown'}</span>
                  <h3>{item.university?.name || 'University'}</h3>
                  <p className="muted-small">{item.program?.name || 'Program'} · {item.program?.degree_level || 'Degree'}</p>
                </div>
                <div className="score-pill warn">{item.university?.ranking_global || item.university?.ranking || 'N/A'}</div>
              </div>
              <div className="meta">
                <span className="tag-pill">Tuition ${Number(item.program?.estimated_tuition_fees || 0).toLocaleString()}</span>
                <span className="tag-pill">Scholarship {item.program?.scholarship_available ? 'Available' : 'Not listed'}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="study-panel">
          <div className="empty-block">
            <div>
              <p className="section-label">No saved universities</p>
              <h2>Build your shortlist</h2>
              <p>Save programs from the search or match pages to track them here.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StudentSavedUniversities