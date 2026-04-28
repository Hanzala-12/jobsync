import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { applicationsAPI } from '../api/client'
import './Applications.css'

const Applications = () => {
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    company: '',
    role: '',
    notes: ''
  })

  useEffect(() => {
    loadApplications()
  }, [])

  const loadApplications = async () => {
    try {
      const response = await applicationsAPI.list()
      setApplications(response.data)
    } catch (error) {
      console.error('Failed to load applications:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await applicationsAPI.create(formData)
      setFormData({ company: '', role: '', notes: '' })
      setShowForm(false)
      loadApplications()
    } catch (error) {
      console.error('Failed to create application:', error)
    }
  }

  const handleStatusChange = async (appId, newStatus) => {
    try {
      await applicationsAPI.updateStatus(appId, newStatus)
      loadApplications()
    } catch (error) {
      console.error('Failed to update status:', error)
    }
  }

  const statusColors = {
    'Applied': '#64748b',
    'Interview': '#10b981',
    'Offer': '#f59e0b',
    'Rejected': '#ef4444'
  }

  return (
    <div className="applications-page">
      <div className="page-header">
        <div>
          <h1>Applications</h1>
          <p className="page-description">Track your job applications</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus size={20} />
          Add Application
        </Button>
      </div>

      {showForm && (
        <Card title="New Application">
          <form onSubmit={handleSubmit} className="application-form">
            <div className="form-group">
              <label>Company</label>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => setFormData({...formData, company: e.target.value})}
                required
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label>Role</label>
              <input
                type="text"
                value={formData.role}
                onChange={(e) => setFormData({...formData, role: e.target.value})}
                required
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label>Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows="3"
                className="form-input"
              />
            </div>
            <div className="form-actions">
              <Button type="submit">Create Application</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        {loading ? (
          <p>Loading applications...</p>
        ) : applications.length === 0 ? (
          <div className="empty-state">
            <p>No applications yet. Add your first application to get started.</p>
          </div>
        ) : (
          <div className="applications-list">
            {applications.map((app) => (
              <div key={app.id} className="application-item">
                <div className="application-info">
                  <h3>{app.role}</h3>
                  <p className="company-name">{app.company}</p>
                  <p className="application-date">
                    Applied: {new Date(app.applied_date).toLocaleDateString()}
                  </p>
                  {app.notes && <p className="application-notes">{app.notes}</p>}
                </div>
                <div className="application-status">
                  <select
                    value={app.status}
                    onChange={(e) => handleStatusChange(app.id, e.target.value)}
                    className="status-select"
                    style={{ borderColor: statusColors[app.status] }}
                  >
                    <option value="Applied">Applied</option>
                    <option value="Interview">Interview</option>
                    <option value="Offer">Offer</option>
                    <option value="Rejected">Rejected</option>
                  </select>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

export default Applications
