import { useEffect, useState } from 'react'
import Button from '../components/Button'
import { applicationsAPI } from '../api/client'
import './Applications.css'

const STATUSES = ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected']

const emptyForm = {
  company: '',
  role: '',
  status: 'Saved',
  next_action: '',
}

function Applications() {
  const [applications, setApplications] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const loadApplications = async () => {
    const response = await applicationsAPI.list()
    setApplications(response.data || [])
  }

  useEffect(() => {
    loadApplications()
  }, [])

  const save = async () => {
    if (editingId) {
      await applicationsAPI.update(editingId, form)
    } else {
      await applicationsAPI.create(form)
    }
    setForm(emptyForm)
    setShowForm(false)
    setEditingId(null)
    loadApplications()
  }

  const editRow = (app) => {
    setEditingId(app.id)
    setForm({
      company: app.company,
      role: app.role,
      status: app.status,
      next_action: app.next_action || '',
    })
    setShowForm(true)
  }

  return (
    <div className="applications-page">
      <div className="page-header">
        <h1>Applications</h1>
        <p className="subtitle">Manage every application in one table.</p>
      </div>

      <div className="table-head">
        <p>{applications.length} applications</p>
        <Button onClick={() => setShowForm((prev) => !prev)}>+ Add</Button>
      </div>

      {showForm && (
        <section className="form-box panel-raised app-form-panel">
          <div className="form-header">
            <div>
              <p className="section-label">Application form</p>
              <h2>{editingId ? 'Edit Application' : 'New Application'}</h2>
            </div>
            <button
              type="button"
              className="form-close"
              onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm) }}
            >
              ×
            </button>
          </div>
          <div className="form-grid">
            <label>
              <span>Company</span>
              <input value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} placeholder="Company" />
            </label>
            <label>
              <span>Role</span>
              <input value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} placeholder="Role" />
            </label>
            <label>
              <span>Status</span>
              <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </label>
            <label className="span-2">
              <span>Next action</span>
              <input value={form.next_action} onChange={(event) => setForm({ ...form, next_action: event.target.value })} placeholder="Next action" />
            </label>
          </div>
          <div className="form-actions">
            <Button onClick={save}>Save</Button>
            <Button variant="secondary" onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm) }}>Cancel</Button>
          </div>
        </section>
      )}

      <article className="panel table-panel">
        <table className="apps-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Role</th>
              <th>Status</th>
              <th>Applied</th>
              <th>Next Action</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {applications.length > 0 ? applications.map((app) => (
              <tr key={app.id}>
                <td className="company-cell">
                  <span className="avatar-initial">{String(app.company || '?').charAt(0).toUpperCase()}</span>
                  <span>{app.company}</span>
                </td>
                <td>{app.role}</td>
                <td><span className={`status-badge status-${app.status}`}>{app.status}</span></td>
                <td>{app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '-'}</td>
                <td>{app.next_action || '-'}</td>
                <td>
                  <button className="icon-btn edit" onClick={() => editRow(app)} aria-label="Edit application">✎</button>
                  <button
                    className="icon-btn delete"
                    onClick={async () => {
                      await applicationsAPI.delete(app.id)
                      loadApplications()
                    }}
                    aria-label="Delete application"
                  >
                    🗑
                  </button>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="6" className="empty-state">
                  <div>
                    <p>Nothing here yet.</p>
                    <span>Add your first application to start tracking it.</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </article>
    </div>
  )
}

export default Applications
