import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { applicationsAPI } from '../api/client'
import './Dashboard.css'

const STATUS_ORDER = ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected']
const STATUS_BAR_CLASS = {
  Saved: 'bar-saved',
  Applied: 'bar-applied',
  Interviewing: 'bar-interviewing',
  Offered: 'bar-offered',
  Rejected: 'bar-rejected',
}

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
    applicationsAPI.list().then((res) => setApplications(res.data || [])).catch(() => setApplications([]))
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

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p className="subtitle">Track your weekly application health and execution.</p>
      </div>

      <section className="health-card">
        <div className="health-left">
          <p className="score-value">{health?.score ?? 0}</p>
          <p className={`grade ${getGradeClass(health?.grade || 'F')}`}>{health?.grade || 'F'}</p>
        </div>

        <div className="health-middle">
          <p>{health?.status_message || 'Health score is loading...'}</p>
          <p className="streak">{health?.streak ?? 0} day streak</p>
        </div>

        <div className="health-right">
          {topImprovements.map((item, index) => (
            <label key={`${item}-${index}`} className="improvement-row">
              <input
                type="checkbox"
                checked={!!checked[index]}
                onChange={(event) => setChecked((prev) => ({ ...prev, [index]: event.target.checked }))}
              />
              <Link to={improvementLink(item)}>{item}</Link>
              <span>{pointsFromText(item)}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="stats-row">
        <article className="stat-card left-accent">
          <p className="section-label">TOTAL APPLICATIONS</p>
          <p className="stat-value">{stats.total}</p>
          <p className="muted">Active pipeline size</p>
        </article>
        <article className="stat-card">
          <p className="section-label">INTERVIEWS SCHEDULED</p>
          <p className="stat-value">{stats.interviews}</p>
          <p className="muted">In progress this cycle</p>
        </article>
        <article className="stat-card">
          <p className="section-label">OFFERS RECEIVED</p>
          <p className="stat-value">{stats.offers}</p>
          <p className="muted">Positive outcomes</p>
        </article>
        <article className="stat-card">
          <p className="section-label">AVG ATS SCORE</p>
          <p className="stat-value">{stats.ats}</p>
          <p className="muted">Current health score</p>
        </article>
      </section>

      <section className="row-two">
        <article className="panel panel-wide">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentApplications.map((app) => (
                <tr key={app.id}>
                  <td>{app.company}</td>
                  <td>{app.role}</td>
                  <td><span className={`status-badge status-${app.status}`}>{app.status}</span></td>
                  <td>{app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="view-all-wrap"><Link to="/applications">View all</Link></div>
        </article>

        <article className="panel panel-narrow">
          {STATUS_ORDER.map((status) => {
            const value = statusCounts[status]
            const width = `${Math.round((value / maxCount) * 100)}%`
            return (
              <div className="status-row" key={status}>
                <div className="status-head">
                  <span>{status}</span>
                  <strong>{value}</strong>
                </div>
                <div className="progress-track">
                  <span className={STATUS_BAR_CLASS[status]} style={{ width }} />
                </div>
              </div>
            )
          })}
        </article>
      </section>

      <section className="row-three">
        <article className="panel">
          <p className="section-label">SKILLS TO LEARN</p>
          <div className="chips">
            {skillsToLearn.length > 0 ? (
              skillsToLearn.map((skill) => <span key={skill} className="skill-chip">{skill}</span>)
            ) : (
              <p className="muted">No missing skills captured yet</p>
            )}
          </div>
        </article>

        <article className="panel">
          <p className="section-label">UPCOMING INTERVIEWS</p>
          {upcomingInterviews.length > 0 ? (
            <div className="interview-list">
              {upcomingInterviews.map((item) => (
                <div key={item.id} className="interview-item">
                  <p className="company">{item.company}</p>
                  <p className="role">{item.role}</p>
                  <p className="date">{new Date(item.interview_date).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">No interviews scheduled</p>
          )}
        </article>
      </section>
    </div>
  )
}

export default Dashboard
