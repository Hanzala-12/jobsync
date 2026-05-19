import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  BadgeCheck,
  Briefcase,
  CalendarDays,
  ClipboardList,
  FileText,
  Flame,
  Sparkles,
  TrendingUp,
  Users,
  Clock3,
  AlertTriangle,
  Activity,
  Circle,
} from 'lucide-react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import Card from '../components/Card'
import Button from '../components/Button'
import { applicationsAPI } from '../api/client'
import './Dashboard.css'

const STATUS_ORDER = ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected']
const STATUS_COLORS = {
  Saved: '#64748b',
  Applied: '#2563eb',
  Interviewing: '#10b981',
  Offered: '#f59e0b',
  Rejected: '#ef4444',
}

const ANALYSIS_STORAGE_KEYS = [
  'jobsync_resume_analyses',
  'jobsync_job_analyses',
  'jobsync_analysis_history',
]

const ACTIVITY_STORAGE_KEYS = [
  'jobsync_activity_feed',
  'jobsync_recent_activity',
]

const QUICK_ACTIONS = [
  { label: 'Analyze Resume', path: '/resume', icon: FileText },
  { label: 'Search Jobs', path: '/jobs', icon: Briefcase },
  { label: 'Applications', path: '/applications', icon: ClipboardList },
  { label: 'Cover Letter', path: '/cover-letter', icon: Sparkles },
]

function safeParseArray(rawValue) {
  if (!rawValue) return []
  try {
    const parsed = JSON.parse(rawValue)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function formatRelativeDate(value) {
  if (!value) return 'Unknown date'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown date'

  const now = new Date()
  const diffDays = Math.round((date - now) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays > 1) return `In ${diffDays} days`
  if (diffDays === -1) return '1 day ago'
  return `${Math.abs(diffDays)} days ago`
}

function formatShortDate(value) {
  if (!value) return 'Unknown date'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown date'
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function buildActivityFromApplications(applications) {
  return applications
    .map((application) => {
      const baseDate = application.interview_date || application.applied_date || application.fetched_at
      let title = `${application.role} at ${application.company}`
      let description = ''

      if (application.status === 'Applied') {
        description = 'Applied to'
      } else if (application.status === 'Interviewing') {
        description = 'Interview scheduled at'
      } else if (application.status === 'Offered') {
        description = 'Offer received from'
      } else if (application.status === 'Rejected') {
        description = 'Rejected by'
      } else {
        description = 'Saved'
      }

      return {
        id: `app-${application.id}`,
        label: `${description} ${application.company}`,
        meta: title,
        date: baseDate,
        tone: application.status,
      }
    })
    .filter((item) => item.date)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
}

function collectAnalysisMetrics() {
  const analyses = ANALYSIS_STORAGE_KEYS.flatMap((key) => safeParseArray(localStorage.getItem(key)))
  const scores = analyses
    .map((item) => Number(item.ats_score ?? item.score ?? item.match_score))
    .filter((score) => Number.isFinite(score))

  const skillCounts = new Map()
  analyses.forEach((item) => {
    const missing = item.missing_keywords || item.missing_skills || item.missing || []
    if (Array.isArray(missing)) {
      missing.forEach((skill) => {
        const key = String(skill).trim()
        if (!key) return
        skillCounts.set(key, (skillCounts.get(key) || 0) + 1)
      })
    }
  })

  return {
    averageScore: scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : null,
    topMissingSkills: Array.from(skillCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([skill, count]) => ({ skill, count })),
    analysisCount: analyses.length,
  }
}

function collectActivityFeed(applications) {
  const localActivity = ACTIVITY_STORAGE_KEYS.flatMap((key) => safeParseArray(localStorage.getItem(key)))
    .map((item, index) => ({
      id: item.id || `local-${index}`,
      label: item.label || item.title || item.message || 'Activity',
      meta: item.meta || item.detail || '',
      date: item.date || item.timestamp || item.created_at,
      tone: item.tone || item.status || 'Applied',
    }))
    .filter((item) => item.date)

  const applicationActivity = buildActivityFromApplications(applications)

  return [...localActivity, ...applicationActivity]
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 5)
}

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [applications, setApplications] = useState([])
  const [metrics, setMetrics] = useState({
    totalApplications: 0,
    applicationsThisWeek: 0,
    applicationsLastWeek: 0,
    averageScore: null,
    topMissingSkills: [],
    upcomingInterviews: [],
    recentActivity: [],
    statusData: [],
    analysisCount: 0,
  })

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await applicationsAPI.list()
      const apps = response.data || []
      setApplications(apps)

      const now = new Date()
      const sevenDaysAgo = new Date(now)
      sevenDaysAgo.setDate(now.getDate() - 7)
      const fourteenDaysAgo = new Date(now)
      fourteenDaysAgo.setDate(now.getDate() - 14)

      const applicationsThisWeek = apps.filter((app) => {
        const appliedDate = new Date(app.applied_date)
        return !Number.isNaN(appliedDate.getTime()) && appliedDate >= sevenDaysAgo
      }).length

      const applicationsLastWeek = apps.filter((app) => {
        const appliedDate = new Date(app.applied_date)
        return !Number.isNaN(appliedDate.getTime()) && appliedDate < sevenDaysAgo && appliedDate >= fourteenDaysAgo
      }).length

      const statusData = STATUS_ORDER.map((status) => ({
        name: status,
        value: apps.filter((app) => app.status === status).length,
        color: STATUS_COLORS[status],
      }))

      const upcomingInterviews = apps
        .filter((app) => app.interview_date)
        .map((app) => ({ ...app, interviewDateValue: new Date(app.interview_date) }))
        .filter((app) => !Number.isNaN(app.interviewDateValue.getTime()) && app.interviewDateValue >= new Date(now.getTime() - 24 * 60 * 60 * 1000))
        .sort((a, b) => a.interviewDateValue - b.interviewDateValue)
        .slice(0, 3)

      const analysisMetrics = collectAnalysisMetrics()
      const recentActivity = collectActivityFeed(apps)

      setMetrics({
        totalApplications: apps.length,
        applicationsThisWeek,
        applicationsLastWeek,
        averageScore: analysisMetrics.averageScore,
        topMissingSkills: analysisMetrics.topMissingSkills,
        upcomingInterviews,
        recentActivity,
        statusData,
        analysisCount: analysisMetrics.analysisCount,
      })
    } catch (dashboardError) {
      console.error('Failed to load dashboard:', dashboardError)
      setError('Failed to load dashboard data.')
    } finally {
      setLoading(false)
    }
  }

  const trendDelta = metrics.applicationsLastWeek === 0
    ? (metrics.applicationsThisWeek > 0 ? 100 : 0)
    : Math.round(((metrics.applicationsThisWeek - metrics.applicationsLastWeek) / metrics.applicationsLastWeek) * 100)

  const trendLabel = trendDelta >= 0 ? `+${trendDelta}% vs last week` : `${trendDelta}% vs last week`

  const statusPieData = metrics.statusData.filter((item) => item.value > 0)

  const quickActions = QUICK_ACTIONS

  return (
    <div className="dashboard dashboard-analytics">
      <div className="dashboard-hero">
        <div>
          <p className="eyebrow">Job search control center</p>
          <h1>Dashboard</h1>
          <p className="page-description">
            A live view of your job search, resume signals, and the next best action.
          </p>
        </div>
        <div className="hero-actions">
          <Button onClick={loadDashboard} loading={loading}>
            Refresh Insights
          </Button>
          <Link to="/resume" className="hero-link">
            Review Resume <ArrowUpRight size={16} />
          </Link>
        </div>
      </div>

      {error && <div className="dashboard-error">{error}</div>}

      <div className="stats-grid stats-grid-analytics">
        <Card className="metric-card metric-card-primary">
          <div className="metric-topline">
            <div className="metric-icon-wrap">
              <ClipboardList size={22} />
            </div>
            <span className="metric-badge positive">{trendLabel}</span>
          </div>
          <p className="metric-label">Total applications</p>
          <h2 className="metric-value">{loading ? '—' : metrics.totalApplications}</h2>
          <p className="metric-subtext">
            {metrics.applicationsThisWeek} this week, {metrics.applicationsLastWeek} last week
          </p>
        </Card>

        <Card className="metric-card">
          <div className="metric-topline">
            <div className="metric-icon-wrap teal">
              <TrendingUp size={22} />
            </div>
            <span className="metric-badge">{metrics.analysisCount} analyses</span>
          </div>
          <p className="metric-label">Average ATS score</p>
          <h2 className="metric-value">{loading ? '—' : (metrics.averageScore ?? 'N/A')}</h2>
          <p className="metric-subtext">Across stored resume and job analyses</p>
        </Card>

        <Card className="metric-card">
          <div className="metric-topline">
            <div className="metric-icon-wrap amber">
              <Briefcase size={22} />
            </div>
            <span className="metric-badge">{metrics.upcomingInterviews.length} upcoming</span>
          </div>
          <p className="metric-label">Interview pipeline</p>
          <h2 className="metric-value">{loading ? '—' : metrics.upcomingInterviews.length}</h2>
          <p className="metric-subtext">Next 3 interviews sorted by date</p>
        </Card>
      </div>

      <div className="dashboard-main-grid">
        <Card title="Application Status Breakdown" className="analytics-card chart-card">
          <div className="chart-wrap">
            {statusPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusPieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={72}
                    outerRadius={108}
                    paddingAngle={3}
                  >
                    {statusPieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value, name) => [`${value}`, name]}
                    contentStyle={{
                      background: '#0f172a',
                      color: '#fff',
                      border: '1px solid rgba(148, 163, 184, 0.2)',
                      borderRadius: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state compact">
                <Circle size={32} />
                <p>No applications yet. Your chart will populate here.</p>
              </div>
            )}
          </div>
          <div className="chart-legend">
            {STATUS_ORDER.map((status) => {
              const item = metrics.statusData.find((entry) => entry.name === status)
              return (
                <div key={status} className="legend-item">
                  <span className="legend-dot" style={{ background: STATUS_COLORS[status] }} />
                  <span>{status}</span>
                  <strong>{item?.value ?? 0}</strong>
                </div>
              )
            })}
          </div>
        </Card>

        <div className="right-rail">
          <Card title="Top 5 Missing Skills" className="analytics-card skills-card">
            {metrics.topMissingSkills.length > 0 ? (
              <div className="skill-list">
                {metrics.topMissingSkills.map((skill) => (
                  <div key={skill.skill} className="skill-row">
                    <span>{skill.skill}</span>
                    <span className="skill-count">{skill.count}x</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state compact">
                <Sparkles size={28} />
                <p>No saved analysis data yet.</p>
              </div>
            )}
          </Card>

          <Card title="Upcoming Interviews" className="analytics-card interviews-card">
            {metrics.upcomingInterviews.length > 0 ? (
              <div className="interview-list">
                {metrics.upcomingInterviews.map((interview) => (
                  <div key={interview.id} className="interview-row">
                    <div>
                      <p className="interview-company">{interview.company}</p>
                      <p className="interview-role">{interview.role}</p>
                    </div>
                    <div className="interview-meta">
                      <CalendarDays size={14} />
                      <span>{formatShortDate(interview.interview_date)}</span>
                    </div>
                    <div className="interview-meta muted">
                      <Clock3 size={14} />
                      <span>{formatRelativeDate(interview.interview_date)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state compact">
                <CalendarDays size={28} />
                <p>No upcoming interviews scheduled.</p>
              </div>
            )}
          </Card>
        </div>
      </div>

      <div className="lower-grid">
        <Card title="Recent Activity" className="analytics-card activity-card">
          {metrics.recentActivity.length > 0 ? (
            <div className="activity-feed">
              {metrics.recentActivity.map((activity) => (
                <div key={activity.id} className="activity-row">
                  <div className={`activity-dot activity-${activity.tone.toLowerCase()}`} />
                  <div className="activity-body">
                    <p>{activity.label}</p>
                    {activity.meta && <span>{activity.meta}</span>}
                  </div>
                  <div className="activity-time">{formatRelativeDate(activity.date)}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state compact">
              <Activity size={28} />
              <p>No recent activity yet.</p>
            </div>
          )}
        </Card>

        <Card title="Quick Actions" className="analytics-card quick-actions-card">
          <div className="quick-actions-grid analytics-actions">
            {quickActions.map((action) => {
              const Icon = action.icon
              return (
                <Link key={action.path} to={action.path} className="quick-action analytics-action">
                  <div className="action-icon">
                    <Icon size={20} />
                  </div>
                  <div>
                    <span>{action.label}</span>
                    <p>Open workspace</p>
                  </div>
                </Link>
              )
            })}
          </div>
        </Card>
      </div>

      <Card title="What to do next" className="analytics-card next-step-card">
        <div className="next-step-grid">
          <div className="next-step-item">
            <BadgeCheck size={18} />
            <div>
              <strong>Review your top missing skills</strong>
              <p>Use them to target your next learning sprint.</p>
            </div>
          </div>
          <div className="next-step-item">
            <Flame size={18} />
            <div>
              <strong>Push applications into Interviewing</strong>
              <p>Keep the pipeline moving with a follow-up cadence.</p>
            </div>
          </div>
          <div className="next-step-item">
            <Users size={18} />
            <div>
              <strong>Keep your dashboard current</strong>
              <p>Refresh after every resume analysis or new application.</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default Dashboard
