import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { applicationsAPI } from '../api/client'
import { Briefcase, Calendar, Award, Activity, ArrowRight, CheckCircle2 } from 'lucide-react'
import './Dashboard.css'

const STATUS_ORDER = ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected']

function parseSkillsFromStorage() {
  const keys = ['jobsync_resume_analysis_history', 'jobsync_resume_analyses', 'jobsync_job_analyses', 'jobsync_analysis_history']
  const counts = {}

  keys.forEach((key) => {
    try {
      const items = JSON.parse(localStorage.getItem(key) || '[]')
      if (!Array.isArray(items)) return
      items.forEach((item) => {
        const missing = item?.missing_keywords || item?.missing_skills || []
        if (!Array.isArray(missing)) return
        missing.forEach((skill) => {
          const normalized = String(skill || '').trim()
          if (!normalized) return
          counts[normalized] = (counts[normalized] || 0) + 1
        })
      })
    } catch {
      // ignore localStorage parsing issues
    }
  })

  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([skill]) => skill)
}

function getGradeClass(grade) {
  if (grade === 'A') return 'grade-a'
  if (grade === 'B') return 'grade-b'
  if (grade === 'C') return 'grade-c'
  if (grade === 'D') return 'grade-d'
  return 'grade-f'
}

function pointsFromText(text) {
  const match = String(text || '').match(/\+\d+|\-\d+/)
  return match ? match[0] : '+5'
}

function Dashboard() {
  const [health, setHealth] = useState(null)
  const [applications, setApplications] = useState([])
  const [checked, setChecked] = useState({})

  useEffect(() => {
    applicationsAPI.healthScore().then((res) => setHealth(res.data)).catch(() => setHealth(null))
    applicationsAPI.list().then((res) => {
      const data = res.data
      setApplications(Array.isArray(data) ? data : (data?.jobs || data?.items || data?.applications || []))
    }).catch(() => setApplications([]))
  }, [])

  const stats = useMemo(() => {
    const total = applications.length
    const interviews = applications.filter((app) => app.status === 'Interviewing').length
    const offers = applications.filter((app) => app.status === 'Offered').length
    const ats = health?.score ?? 0
    return { total, interviews, offers, ats }
  }, [applications, health])

  const recentApplications = useMemo(() => applications.slice(0, 5), [applications])

  const statusCounts = useMemo(() => {
    const result = {}
    STATUS_ORDER.forEach((status) => {
      result[status] = applications.filter((app) => app.status === status).length
    })
    return result
  }, [applications])

  const maxCount = Math.max(1, ...Object.values(statusCounts))
  const topImprovements = (health?.improvements || []).slice(0, 3)
  const skillsToLearn = parseSkillsFromStorage()
  const upcomingInterviews = applications
    .filter((app) => app.interview_date)
    .sort((a, b) => new Date(a.interview_date) - new Date(b.interview_date))
    .slice(0, 5)

  const improvementLink = (text) => {
    const lower = String(text || '').toLowerCase()
    if (lower.includes('resume') || lower.includes('ats')) return '/resume'
    if (lower.includes('interview')) return '/interview'
    if (lower.includes('application')) return '/applications'
    return '/'
  }

  const today = new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'short', day: 'numeric' }).format(new Date())

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p className="subtitle">{today}</p>
      </div>

      <section className="health-banner fade-up">
        <div className="health-left">
          <div className="health-score">{health?.score ?? 0}</div>
          <div className={`health-grade ${getGradeClass(health?.grade || 'F')}`}>Grade {health?.grade || 'F'}</div>
        </div>

        <div className="health-middle">
          <div className="health-status">{health?.status_message || 'Health score active'}</div>
          <div className="health-streak">{health?.streak ?? 0} day tracking streak</div>
        </div>

        <div className="health-right">
          <div className="section-title">SUGGESTED ACTIONS</div>
          <div className="improvements-list">
            {topImprovements.map((item, index) => (
              <label key={`${item}-${index}`} className="improvement-item">
                <input
                  type="checkbox"
                  checked={!!checked[index]}
                  onChange={(event) => setChecked((prev) => ({ ...prev, [index]: event.target.checked }))}
                />
                <Link to={improvementLink(item)} className="improvement-text">{item}</Link>
                <span className="improvement-pts">{pointsFromText(item)}</span>
              </label>
            ))}
          </div>
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card fade-up" style={{ animationDelay: '0.05s' }}>
          <Briefcase className="stat-icon" size={16} />
          <div className="stat-label">TOTAL APPLICATIONS</div>
          <div className="stat-value">{stats.total}</div>
          <div className="stat-desc">Active pipeline size</div>
        </article>
        <article className="stat-card fade-up" style={{ animationDelay: '0.1s' }}>
          <Calendar className="stat-icon" size={16} />
          <div className="stat-label">INTERVIEWS SCHEDULED</div>
          <div className="stat-value">{stats.interviews}</div>
          <div className="stat-desc">In progress this cycle</div>
        </article>
        <article className="stat-card fade-up" style={{ animationDelay: '0.15s' }}>
          <Award className="stat-icon" size={16} />
          <div className="stat-label">OFFERS RECEIVED</div>
          <div className="stat-value">{stats.offers}</div>
          <div className="stat-desc">Positive outcomes</div>
        </article>
        <article className="stat-card fade-up" style={{ animationDelay: '0.2s' }}>
          <Activity className="stat-icon" size={16} />
          <div className="stat-label">AVG ATS SCORE</div>
          <div className="stat-value">{stats.ats}</div>
          <div className="stat-desc">Current health score</div>
        </article>
      </section>

      <section className="dashboard-grid fade-up" style={{ animationDelay: '0.25s' }}>
        <article className="dash-card recent-apps-card">
          <div className="dash-card-header">
            <h3>Recent Applications</h3>
            <Link to="/applications" className="view-all">View all <ArrowRight size={14} /></Link>
          </div>
          <div className="apps-table-container">
            <table className="apps-table">
              <tbody>
                {recentApplications.map((app) => (
                  <tr key={app.id}>
                    <td>
                      <div className="company-info">
                        <div className="company-avatar">{app.company.charAt(0).toUpperCase()}</div>
                        <div className="company-text">
                          <div className="company-name">{app.company}</div>
                          <div className="company-role">{app.role}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`status-pill status-${app.status}`}>{app.status}</span>
                    </td>
                    <td className="date-cell">
                      {app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="dash-card pipeline-card">
          <div className="dash-card-header">
            <h3>Pipeline</h3>
          </div>
          <div className="pipeline-bars">
            {STATUS_ORDER.map((status) => {
              const value = statusCounts[status]
              const width = `${Math.round((value / maxCount) * 100)}%`
              return (
                <div className="pipeline-row" key={status}>
                  <div className="pipeline-label">
                    <span>{status}</span>
                    <strong>{value}</strong>
                  </div>
                  <div className="pipeline-track">
                    <div className={`pipeline-fill fill-${status}`} style={{ width }} />
                  </div>
                </div>
              )
            })}
          </div>
        </article>
      </section>

      <section className="dashboard-grid bottom-grid fade-up" style={{ animationDelay: '0.3s' }}>
        <article className="dash-card">
          <div className="dash-card-header">
            <h3>Skill Gaps</h3>
          </div>
          <div className="skills-gap-container">
            {skillsToLearn.length > 0 ? (
              skillsToLearn.map((skill) => <span key={skill} className="skill-pill">{skill}</span>)
            ) : (
              <p className="empty-text">No missing skills captured yet</p>
            )}
          </div>
        </article>

        <article className="dash-card">
          <div className="dash-card-header">
            <h3>Upcoming Interviews</h3>
          </div>
          <div className="upcoming-interviews-container">
            {upcomingInterviews.length > 0 ? (
              upcomingInterviews.map((item) => (
                <div key={item.id} className="upcoming-item">
                  <div className="upcoming-date-box">
                    <span className="upcoming-day">{new Date(item.interview_date).getDate()}</span>
                    <span className="upcoming-month">{new Date(item.interview_date).toLocaleString('default', { month: 'short' })}</span>
                  </div>
                  <div className="upcoming-info">
                    <p className="upcoming-company">{item.company}</p>
                    <p className="upcoming-role">{item.role}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <CheckCircle2 />
                <p>No interviews scheduled right now.</p>
              </div>
            )}
          </div>
        </article>
      </section>
    </div>
  )
}

export default Dashboard
