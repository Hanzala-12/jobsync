import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './Button'
import UniversityMatchList from './UniversityMatchList'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

function UniversityDashboard({ profileId: providedProfileId }) {
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [savedPrograms, setSavedPrograms] = useState([])
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)

  const profileId = Number(providedProfileId || 0)

  const loadSummary = async () => {
    if (!profileId) {
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const [profileRes, savedRes] = await Promise.all([
        studentAPI.getProfile(profileId),
        studentAPI.getSavedUniversities(profileId),
      ])
      setProfile(profileRes.data)
      setSavedPrograms(savedRes.data || [])
    } catch {
      setProfile(null)
      setSavedPrograms([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSummary()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId])

  const scholarshipCount = matches.filter((item) => item.program?.scholarship_available).length

  return (
    <div className="study-page">
      <section className="study-hero">
        <div>
          <p className="section-label">Study Mode</p>
          <h1>{profile ? `Welcome back, ${profile.intended_major || 'Student'}` : 'Welcome to your university dashboard'}</h1>
          <p className="muted">Find programs, save opportunities, and track applications in one place.</p>
        </div>
        <div className="study-hero-actions">
          <span className="study-badge">Top 10 matches ready</span>
          <span className="study-badge">Scholarships available: {scholarshipCount || savedPrograms.filter((item) => item.program?.scholarship_available).length || 0}</span>
          <Button onClick={() => navigate('/student/matches')}>Find My Matches</Button>
        </div>
      </section>

      {loading ? (
        <div className="study-panel"><div className="loading-block">Loading your study dashboard...</div></div>
      ) : !profile ? (
        <div className="study-panel">
          <div className="empty-block">
            <div>
              <p className="section-label">No profile found</p>
              <h2>Create your profile first</h2>
              <p>We need a student profile before matches can be calculated. After that, saved programs and application tracking will sync here on every refresh.</p>
              <div style={{ marginTop: 12 }}>
                <Button onClick={() => navigate('/student/profile')}>Create Profile</Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <section className="dashboard-stats">
            <article className="study-panel"><p className="section-label">Saved programs</p><h2>{savedPrograms.length}</h2><p className="muted-small">Previously viewed or bookmarked.</p></article>
            <article className="study-panel"><p className="section-label">Major</p><h2>{profile.intended_major}</h2><p className="muted-small">{profile.degree_level}</p></article>
            <article className="study-panel"><p className="section-label">Budget</p><h2>${Number(profile.budget_per_year || 0).toLocaleString()}</h2><p className="muted-small">Per academic year</p></article>
          </section>

          <section className="study-panel">
            <div className="panel-head">
              <div>
                <p className="section-label">Saved universities</p>
                <h2>Shortlist</h2>
              </div>
              <Button variant="secondary" onClick={loadSummary}>Refresh</Button>
            </div>
            {savedPrograms.length > 0 ? (
              <div className="saved-grid">
                {savedPrograms.map((item) => (
                  <article key={item.id} className="saved-card">
                    <div className="match-card-top">
                      <div>
                        <span className="ranking-pill">{item.university?.country || 'Unknown'}</span>
                        <h3>{item.university?.name || 'University'}</h3>
                        <p className="muted-small">{item.program?.name || 'Program'}</p>
                      </div>
                      <div className="score-pill warn">{item.university?.ranking_global || item.university?.ranking || 'N/A'}</div>
                    </div>
                    <p className="muted-small">${Number(item.program?.estimated_tuition_fees || 0).toLocaleString()} annual tuition</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-block"><p>No saved universities yet. Save a match to build your shortlist.</p></div>
            )}
          </section>

          <div id="match-list">
            <UniversityMatchList profileId={profile.id} onResultsLoaded={setMatches} />
          </div>
        </>
      )}
    </div>
  )
}

export default UniversityDashboard