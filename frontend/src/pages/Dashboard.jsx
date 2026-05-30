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
    const savedJobs = applications.filter((app) => app.status === 'Saved').length
    const ats = health?.score ?? 0
    return { total, interviews, offers, savedJobs, ats }
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

  const scoreTone = (score) => {
    if (score >= 85) return { background: 'rgba(16, 185, 129, 0.10)', color: '#047857', borderColor: 'rgba(16, 185, 129, 0.18)' }
    if (score >= 70) return { background: 'rgba(245, 158, 11, 0.12)', color: '#b45309', borderColor: 'rgba(245, 158, 11, 0.20)' }
    return { background: 'rgba(239, 68, 68, 0.10)', color: '#b91c1c', borderColor: 'rgba(239, 68, 68, 0.18)' }
  }

  const scoreLabel = (score) => {
    if (score >= 85) return 'Excellent'
    if (score >= 70) return 'Strong'
    if (score >= 55) return 'Needs work'
    return 'Low'
  }

  const statCards = [
    {
      label: 'Total Applications',
      value: stats.total,
      hint: 'Active pipeline size',
      icon: Briefcase,
      accent: 'from-blue-500 to-indigo-500',
    },
    {
      label: 'Interviews',
      value: stats.interviews,
      hint: 'Scheduled or in progress',
      icon: Calendar,
      accent: 'from-violet-500 to-fuchsia-500',
    },
    {
      label: 'Average Match Score',
      value: `${health?.score ?? 0}%`,
      hint: health?.grade ? `Health grade ${health.grade}` : 'Health score unavailable',
      icon: Award,
      accent: 'from-emerald-500 to-teal-500',
    },
    {
      label: 'Saved Jobs',
      value: stats.savedJobs,
      hint: 'Jobs bookmarked in your pipeline',
      icon: Briefcase,
      accent: 'from-slate-500 to-slate-700',
    },
  ]

  const improvementLink = (text) => {
    const lower = String(text || '').toLowerCase()
    if (lower.includes('resume') || lower.includes('ats')) return '/resume'
    if (lower.includes('interview')) return '/interview'
    if (lower.includes('application')) return '/applications'
    return '/'
  }

  const today = new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'short', day: 'numeric' }).format(new Date())

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <section
        className="app-card"
        style={{
          padding: '24px',
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.25fr) minmax(280px, 0.75fr)',
          gap: '20px',
          alignItems: 'stretch',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <div>
              <p style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>
                Today
              </p>
              <h2 style={{ marginTop: '6px', fontSize: '28px', lineHeight: 1.05, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--j-text-1)' }}>
                {today}
              </h2>
            </div>

            <div
              style={{
                minWidth: '104px',
                borderRadius: '18px',
                padding: '14px 16px',
                background: 'linear-gradient(135deg, rgba(58,87,232,0.10), rgba(99,115,248,0.06))',
                border: '1px solid rgba(58,87,232,0.14)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '40px', lineHeight: 1, fontWeight: 800, letterSpacing: '-0.05em', color: 'var(--j-text-1)' }}>
                {health?.score ?? 0}
              </div>
              <div className="status-pill" style={{ marginTop: '10px', ...scoreTone(health?.score ?? 0) }}>
                Grade {health?.grade || 'F'} · {scoreLabel(health?.score ?? 0)}
              </div>
            </div>
          </div>

          <p style={{ color: 'var(--j-text-2)', maxWidth: '72ch' }}>
            {health?.status_message || 'Health score active. Keep building your pipeline and tracking follow-ups.'}
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <Link className="btn-primary" to="/jobs" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              Explore Jobs
              <ArrowRight size={16} />
            </Link>
            <Link className="btn-secondary" to="/resume" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              Review Resume
            </Link>
          </div>
        </div>

        <div
          style={{
            borderRadius: '20px',
            padding: '18px',
            background: 'linear-gradient(180deg, rgba(31,35,64,0.98), rgba(21,25,54,0.98))',
            color: 'var(--j-text-inverse)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            boxShadow: '0 18px 40px rgba(15,23,42,0.18)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
            <div>
              <p style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(248,250,252,0.62)' }}>
                Suggested Actions
              </p>
              <h3 style={{ marginTop: '6px', fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em' }}>
                Focus your next move
              </h3>
            </div>
            <div style={{ width: '40px', height: '40px', borderRadius: '14px', background: 'rgba(255,255,255,0.08)', display: 'grid', placeItems: 'center' }}>
              <Activity size={18} />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {topImprovements.slice(0, 3).map((item, index) => (
              <label
                key={`${item}-${index}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '12px 12px',
                  borderRadius: '14px',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={!!checked[index]}
                  onChange={(event) => setChecked((prev) => ({ ...prev, [index]: event.target.checked }))}
                  style={{ marginTop: '3px', accentColor: '#6373f8' }}
                />
                <Link to={improvementLink(item)} style={{ flex: 1, color: 'rgba(248,250,252,0.92)', fontSize: '13px', lineHeight: 1.45 }}>
                  {item}
                </Link>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#86efac', whiteSpace: 'nowrap' }}>
                  {pointsFromText(item)}
                </span>
              </label>
            ))}
          </div>
        </div>
      </section>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
        }}
      >
        {statCards.map((card, index) => {
          const Icon = card.icon
          return (
            <article
              key={card.label}
              className="app-card"
              style={{
                padding: '20px',
                minHeight: '156px',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 'auto -24px -24px auto',
                  width: '110px',
                  height: '110px',
                  borderRadius: '999px',
                  background: `linear-gradient(145deg, rgba(58,87,232,0.10), rgba(99,115,248,0.02))`,
                  filter: 'blur(0px)',
                }}
              />

              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', position: 'relative' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '14px',
                      display: 'grid',
                      placeItems: 'center',
                      color: '#fff',
                      background: `linear-gradient(135deg, ${card.accent.includes('blue') ? '#3a57e8' : card.accent.includes('violet') ? '#8b5cf6' : card.accent.includes('emerald') ? '#10b981' : '#475569'}, ${card.accent.includes('blue') ? '#6373f8' : card.accent.includes('violet') ? '#d946ef' : card.accent.includes('emerald') ? '#14b8a6' : '#334155'})`,
                      boxShadow: '0 14px 28px rgba(15,23,42,0.10)',
                    }}
                  >
                    <Icon size={18} />
                  </div>

                  <div>
                    <p style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>
                      {card.label}
                    </p>
                    <div style={{ marginTop: '10px', fontSize: '34px', lineHeight: 1, fontWeight: 800, letterSpacing: '-0.05em', color: 'var(--j-text-1)' }}>
                      {card.value}
                    </div>
                    <p style={{ marginTop: '8px', fontSize: '13px', color: 'var(--j-text-2)' }}>
                      {card.hint}
                    </p>
                  </div>
                </div>

                {index === 2 ? (
                  <div className="status-pill" style={{ position: 'relative', ...scoreTone(health?.score ?? 0) }}>
                    {scoreLabel(health?.score ?? 0)}
                  </div>
                ) : null}
              </div>
            </article>
          )
        })}
      </section>

      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '14px' }}>
          <div>
            <p style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>
              Recent Job Matches
            </p>
            <h3 style={{ marginTop: '6px', fontSize: '20px', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--j-text-1)' }}>
              Latest applications and matches
            </h3>
          </div>
          <Link to="/jobs" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--j-accent)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            View all <ArrowRight size={14} />
          </Link>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px',
          }}
        >
          {recentApplications.length > 0 ? recentApplications.map((app, index) => {
            const score = Math.max(42, Math.min(98, (health?.score ?? 0) - (index * 4)))
            return (
              <article
                key={app.id}
                className="app-card"
                style={{
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  minHeight: '100%',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
                    <div style={{ width: '46px', height: '46px', borderRadius: '16px', background: 'linear-gradient(135deg, rgba(58,87,232,0.10), rgba(6,182,212,0.08))', color: 'var(--j-accent)', display: 'grid', placeItems: 'center', fontWeight: 800, flexShrink: 0 }}>
                      {(app.company || 'J').charAt(0).toUpperCase()}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <h4 style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--j-text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {app.role || 'Untitled role'}
                      </h4>
                      <p style={{ marginTop: '4px', fontSize: '13px', color: 'var(--j-text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {app.company || 'Unknown company'}
                      </p>
                    </div>
                  </div>

                  <div className="status-pill" style={scoreTone(score)}>
                    {score}% Match
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', color: 'var(--j-text-2)', fontSize: '13px' }}>
                  <span>{app.applied_date ? new Date(app.applied_date).toLocaleDateString() : 'Not applied yet'}</span>
                  <span className={`status-pill status-${app.status}`}>{app.status}</span>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: 'auto' }}>
                  <Link className="btn-primary" to="/jobs" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    Match Me
                  </Link>
                  <Link className="btn-secondary" to="/resume" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    Tailor Resume
                  </Link>
                </div>
              </article>
            )
          }) : (
            <div className="app-card" style={{ padding: '28px', textAlign: 'center' }}>
              <CheckCircle2 style={{ margin: '0 auto 12px', opacity: 0.6 }} />
              <h4 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--j-text-1)' }}>No recent matches yet</h4>
              <p style={{ marginTop: '8px', color: 'var(--j-text-2)' }}>Search jobs and start building your pipeline.</p>
            </div>
          )}
        </div>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        <article className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.03em' }}>Pipeline</h3>
            <span className="status-pill">Tracked statuses</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {STATUS_ORDER.map((status) => {
              const value = statusCounts[status]
              const width = `${Math.round((value / maxCount) * 100)}%`
              return (
                <div key={status} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 700 }}>
                    <span>{status}</span>
                    <strong>{value}</strong>
                  </div>
                  <div style={{ height: '8px', background: 'var(--j-surface-3)', borderRadius: '999px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width,
                        height: '100%',
                        borderRadius: '999px',
                        background: status === 'Saved' ? '#94a3b8' : status === 'Applied' ? 'linear-gradient(90deg, #3a57e8, #6373f8)' : status === 'Interviewing' ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : status === 'Offered' ? 'linear-gradient(90deg, #10b981, #34d399)' : 'linear-gradient(90deg, #ef4444, #fb7185)',
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </article>

        <article className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.03em' }}>Skill Gaps</h3>
            <Link to="/skill-gap" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--j-accent)' }}>Analyze</Link>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {skillsToLearn.length > 0 ? (
              skillsToLearn.map((skill) => (
                <span
                  key={skill}
                  className="status-pill"
                  style={{ background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)' }}
                >
                  {skill}
                </span>
              ))
            ) : (
              <p style={{ color: 'var(--j-text-2)' }}>No missing skills captured yet.</p>
            )}
          </div>
        </article>

        <article className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.03em' }}>Upcoming Interviews</h3>
            <Link to="/applications" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--j-accent)' }}>Open list</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {upcomingInterviews.length > 0 ? (
              upcomingInterviews.map((item) => (
                <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: '14px', padding: '14px', borderRadius: '16px', background: 'var(--j-surface-2)', border: '1px solid var(--j-border)' }}>
                  <div style={{ width: '46px', height: '46px', borderRadius: '14px', background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '16px', fontWeight: 800, lineHeight: 1 }}>
                        {new Date(item.interview_date).getDate()}
                      </div>
                      <div style={{ fontSize: '10px', textTransform: 'uppercase', fontWeight: 700 }}>
                        {new Date(item.interview_date).toLocaleString('default', { month: 'short' })}
                      </div>
                    </div>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontSize: '14px', fontWeight: 800, color: 'var(--j-text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.company}</p>
                    <p style={{ fontSize: '13px', color: 'var(--j-text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.role}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state" style={{ padding: '30px 12px' }}>
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
