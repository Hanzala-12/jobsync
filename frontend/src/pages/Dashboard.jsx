import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Briefcase, ClipboardList, TrendingUp } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { applicationsAPI } from '../api/client'
import './Dashboard.css'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalApplications: 0,
    interviews: 0,
    offers: 0,
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const response = await applicationsAPI.list()
      const applications = response.data
      
      setStats({
        totalApplications: applications.length,
        interviews: applications.filter(app => app.status === 'Interview').length,
        offers: applications.filter(app => app.status === 'Offer').length,
      })
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const statCards = [
    { 
      label: 'Total Applications', 
      value: stats.totalApplications, 
      icon: ClipboardList,
      color: '#2563eb'
    },
    { 
      label: 'Interviews', 
      value: stats.interviews, 
      icon: Briefcase,
      color: '#10b981'
    },
    { 
      label: 'Offers', 
      value: stats.offers, 
      icon: TrendingUp,
      color: '#f59e0b'
    },
  ]

  const quickActions = [
    { label: 'Analyze Resume', path: '/resume', icon: FileText },
    { label: 'Search Jobs', path: '/jobs', icon: Briefcase },
    { label: 'Track Applications', path: '/applications', icon: ClipboardList },
    { label: 'Generate Cover Letter', path: '/cover-letter', icon: FileText },
  ]

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p className="page-description">Welcome to JobSync. Track your job search progress.</p>
      </div>

      <div className="stats-grid">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="stat-card">
              <div className="stat-icon" style={{ backgroundColor: `${stat.color}15`, color: stat.color }}>
                <Icon size={24} />
              </div>
              <div className="stat-info">
                <p className="stat-label">{stat.label}</p>
                <p className="stat-value">{loading ? '-' : stat.value}</p>
              </div>
            </Card>
          )
        })}
      </div>

      <Card title="Quick Actions" className="quick-actions-card">
        <div className="quick-actions-grid">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link key={action.path} to={action.path} className="quick-action">
                <Icon size={24} />
                <span>{action.label}</span>
              </Link>
            )
          })}
        </div>
      </Card>

      <Card title="Getting Started">
        <div className="getting-started">
          <ol className="steps-list">
            <li>Upload your resume to get an ATS score and improvement tips</li>
            <li>Search for jobs that match your skills and experience</li>
            <li>Track your applications and update their status</li>
            <li>Generate tailored cover letters for each position</li>
            <li>Prepare for interviews with AI-generated questions</li>
          </ol>
          <Link to="/resume">
            <Button>Get Started</Button>
          </Link>
        </div>
      </Card>
    </div>
  )
}

export default Dashboard
