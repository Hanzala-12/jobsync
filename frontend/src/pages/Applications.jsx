import { useEffect, useState } from 'react'
import Button from '../components/Button'
import { applicationsAPI } from '../api/client'
import { Pencil, Trash2, X, FileText } from 'lucide-react'
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
    const data = response.data
    setApplications(Array.isArray(data) ? data : (data?.jobs || data?.items || data?.applications || []))
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
    <div className="applications-page fade-up">
      <div className="page-header">
        <h1>Applications</h1>
        <p className="subtitle">Manage every application in one table.</p>
      </div>

      <div className="table-head">
        <p>{applications.length} applications total</p>
        <Button onClick={() => setShowForm((prev) => !prev)}>+ Add Application</Button>
      </div>

      {showForm && (
        <section className="form-box app-form-panel fade-up">
          <div className="form-header">
            <div>
              <p className="section-label">APPLICATION FORM</p>
              <h2>{editingId ? 'Edit Application' : 'New Application'}</h2>
            </div>
            <button
              type="button"
              className="form-close"
              onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm) }}
            >
              <X size={20} />
            </button>
          </div>
          <div className="form-grid">
            <label>
              <span>Company</span>
              <input value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} placeholder="E.g. Acme Corp" />
            </label>
            <label>
              <span>Role</span>
              <input value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} placeholder="E.g. Frontend Engineer" />
            </label>
            <label>
              <span>Status</span>
              <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </label>
            <label className="span-2">
              <span>Next action</span>
              <input value={form.next_action} onChange={(event) => setForm({ ...form, next_action: event.target.value })} placeholder="E.g. Follow up on Monday" />
            </label>
          </div>
          <div className="form-actions">
            <Button onClick={save}>Save</Button>
            <Button variant="secondary" onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm) }}>Cancel</Button>
          </div>
        </section>
      )}

      <article className="table-panel">
        <table className="apps-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Role</th>
              <th>Status</th>
              <th>Applied</th>
              <th>Next Action</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
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
                <td><span className={`status-pill status-${app.status}`}>{app.status}</span></td>
                <td>{app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '-'}</td>
                <td>{app.next_action || '-'}</td>
                <td style={{ textAlign: 'right' }}>
                  <button className="icon-btn edit" onClick={() => editRow(app)} aria-label="Edit application"><Pencil size={14} /></button>
                  <button
                    className="icon-btn delete"
                    onClick={async () => {
                      await applicationsAPI.delete(app.id)
                      loadApplications()
                    }}
                    aria-label="Delete application"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="6" className="empty-table-cell">
                  <div className="empty-state">
                    <FileText />
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
