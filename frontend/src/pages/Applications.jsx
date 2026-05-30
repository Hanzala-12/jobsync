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
    <div className="applications-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        className="app-card"
        style={{
          padding: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Pipeline Tracker</p>
          <h1 style={{ marginTop: 6 }}>Applications</h1>
          <p className="subtitle">Manage every application in one table.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ padding: '10px 14px', borderRadius: 14, background: 'var(--j-surface)', border: '1px solid var(--j-border)', color: 'var(--j-text-2)', fontWeight: 600 }}>{applications.length} applications total</div>
          <Button onClick={() => setShowForm((prev) => !prev)}>+ Add Application</Button>
        </div>
      </section>

      {showForm && (
        <section className="form-box app-form-panel fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)' }}>
          <div className="form-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
            <div>
              <p className="section-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Application Form</p>
              <h2 style={{ marginTop: 6, fontSize: 20, fontWeight: 800, color: 'var(--j-text-1)' }}>{editingId ? 'Edit Application' : 'New Application'}</h2>
            </div>
            <button
              type="button"
              className="form-close"
              onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm) }}
              style={{ width: 40, height: 40, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-2)', display: 'grid', placeItems: 'center' }}
            >
              <X size={20} />
            </button>
          </div>
          <div className="form-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 14 }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Company</span>
              <input value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} placeholder="E.g. Acme Corp" style={{ minHeight: 44, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }} />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Role</span>
              <input value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} placeholder="E.g. Frontend Engineer" style={{ minHeight: 44, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }} />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Status</span>
              <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} style={{ minHeight: 44, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }}>
                {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </label>
            <label className="span-2" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Next action</span>
              <input value={form.next_action} onChange={(event) => setForm({ ...form, next_action: event.target.value })} placeholder="E.g. Follow up on Monday" style={{ minHeight: 44, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }} />
            </label>
          </div>
          <div className="form-actions" style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
            <Button onClick={save}>Save</Button>
            <Button variant="secondary" onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm) }}>Cancel</Button>
          </div>
        </section>
      )}

      <article className="table-panel" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 16, boxShadow: 'var(--j-shadow-sm)', overflowX: 'auto' }}>
        <table className="apps-table" style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '14px 12px', color: 'var(--j-text-3)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Company</th>
              <th style={{ textAlign: 'left', padding: '14px 12px', color: 'var(--j-text-3)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Role</th>
              <th style={{ textAlign: 'left', padding: '14px 12px', color: 'var(--j-text-3)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '14px 12px', color: 'var(--j-text-3)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Applied</th>
              <th style={{ textAlign: 'left', padding: '14px 12px', color: 'var(--j-text-3)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Next Action</th>
              <th style={{ textAlign: 'right', padding: '14px 12px', color: 'var(--j-text-3)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {applications.length > 0 ? applications.map((app) => (
              <tr key={app.id} style={{ borderTop: '1px solid var(--j-border)' }}>
                <td className="company-cell" style={{ padding: '14px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className="avatar-initial" style={{ width: 36, height: 36, borderRadius: 12, display: 'grid', placeItems: 'center', background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 800 }}>{String(app.company || '?').charAt(0).toUpperCase()}</span>
                  <span style={{ fontWeight: 700, color: 'var(--j-text-1)' }}>{app.company}</span>
                </td>
                <td style={{ padding: '14px 12px', color: 'var(--j-text-1)' }}>{app.role}</td>
                <td style={{ padding: '14px 12px' }}><span className={`status-pill status-${app.status}`} style={{ padding: '6px 10px', borderRadius: 999, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, fontSize: 12 }}>{app.status}</span></td>
                <td style={{ padding: '14px 12px', color: 'var(--j-text-2)' }}>{app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '-'}</td>
                <td style={{ padding: '14px 12px', color: 'var(--j-text-2)' }}>{app.next_action || '-'}</td>
                <td style={{ padding: '14px 12px', textAlign: 'right' }}>
                  <button type="button" className="icon-btn edit" onClick={() => editRow(app)} aria-label="Edit application" style={{ width: 36, height: 36, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', marginRight: 8, display: 'inline-grid', placeItems: 'center' }}><Pencil size={14} /></button>
                  <button
                    type="button"
                    className="icon-btn delete"
                    onClick={async () => {
                      await applicationsAPI.delete(app.id)
                      loadApplications()
                    }}
                    aria-label="Delete application"
                    style={{ width: 36, height: 36, borderRadius: 12, border: '1px solid rgba(239,68,68,0.18)', background: 'rgba(239,68,68,0.08)', color: '#b91c1c', display: 'inline-grid', placeItems: 'center' }}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="6" className="empty-table-cell" style={{ padding: 28 }}>
                  <div className="empty-state" style={{ minHeight: 220, borderRadius: 16, border: '1px dashed var(--j-border)', background: 'var(--j-surface-2)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                    <FileText />
                    <p style={{ margin: 0, fontWeight: 700, color: 'var(--j-text-1)' }}>Nothing here yet.</p>
                    <span style={{ color: 'var(--j-text-2)' }}>Add your first application to start tracking it.</span>
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
