import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './Button'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

const STATUS_COLUMNS = ['saved', 'applied', 'interviewing', 'offered', 'rejected']

function titleCase(value) {
  return String(value || '').replace(/\b\w/g, (char) => char.toUpperCase())
}

function MyApplications({ profileId }) {
  const navigate = useNavigate()
  const [applications, setApplications] = useState([])
  const [savedPrograms, setSavedPrograms] = useState([])
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState(null)
  const [notesDraft, setNotesDraft] = useState({})
  const [error, setError] = useState('')

  const loadData = async () => {
    if (!profileId) {
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const [applicationsRes, savedRes] = await Promise.all([
        studentAPI.getApplications(profileId),
        studentAPI.getSavedUniversities(profileId),
      ])
      const appData = applicationsRes.data
      const appArray = Array.isArray(appData) ? appData : (appData?.applications || appData?.data || [])
      setApplications(appArray)
      
      const savedData = savedRes.data
      const savedArray = Array.isArray(savedData) ? savedData : (savedData?.saved || savedData?.data || [])
      setSavedPrograms(savedArray)
      
      const draft = {}
      appArray.forEach((item) => {
        draft[item.id] = item.notes || ''
      })
      setNotesDraft(draft)
    } catch (err) {
      setError(err.userMessage || 'Could not load applications')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId])

  const cardsByStatus = useMemo(() => {
    const map = { saved: [], applied: [], interviewing: [], offered: [], rejected: [] }
    savedPrograms.forEach((item) => {
      if (item.program) {
        map.saved.push({ ...item, pseudoStatus: 'saved' })
      }
    })
    applications.forEach((item) => {
      const key = String(item.status || 'saved').toLowerCase()
      if (!map[key]) map[key] = []
      map[key].push(item)
    })
    return map
  }, [applications, savedPrograms])

  const updateStatus = async (application, nextStatus) => {
    setSavingId(application.id)
    setError('')
    try {
      await studentAPI.updateApplication(application.id, { status: nextStatus, notes: notesDraft[application.id] || application.notes || '' })
      await loadData()
    } catch (err) {
      setError(err.userMessage || 'Failed to update application')
    } finally {
      setSavingId(null)
    }
  }

  const applySavedProgram = async (item) => {
    setSavingId(item.program.id)
    setError('')
    try {
      await studentAPI.applyProgram(profileId, item.program.id)
      await loadData()
    } catch (err) {
      setError(err.userMessage || 'Failed to move program to applications')
    } finally {
      setSavingId(null)
    }
  }

  if (!profileId) {
    return (
      <div className="study-page">
        <div className="study-panel">
          <div className="empty-block">
            <div>
              <p className="section-label">Start here</p>
              <h2>Create your profile first</h2>
              <p>Create a student profile so your saved universities and study applications persist in the database instead of disappearing on refresh.</p>
              <div style={{ marginTop: 12 }}>
                <Button onClick={() => navigate('/student/profile')}>Create Profile</Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="study-page">
      <section className="study-hero">
        <div>
          <p className="section-label">My Applications</p>
          <h1>Track universities and deadlines</h1>
          <p className="muted">Move programs through your study pipeline and keep notes per application.</p>
        </div>
        <div className="study-hero-actions">
          <Button onClick={loadData}>Refresh</Button>
        </div>
      </section>

      {error && <p className="muted-small" style={{ color: 'var(--danger)' }}>{error}</p>}
      {loading ? (
        <div className="study-panel"><div className="loading-block">Loading applications...</div></div>
      ) : (
        <div className="board-columns">
          {STATUS_COLUMNS.map((status) => (
            <div className="board-column" key={status}>
              <div className="column-label">
                <span>{titleCase(status)}</span>
                <strong>{cardsByStatus[status]?.length || 0}</strong>
              </div>
              <div className="column-list">
                {cardsByStatus[status]?.length > 0 ? cardsByStatus[status].map((item) => (
                  <article className="application-card" key={item.id || item.program?.id}>
                    <div className="application-card-top">
                      <div>
                        <h3>{item.university?.name || 'University'}</h3>
                        <p className="muted-small">{item.program?.name || 'Program'}</p>
                      </div>
                      <span className="status-pill">{titleCase(item.status || item.pseudoStatus || status)}</span>
                    </div>
                    <p className="muted-small">Deadline: {item.deadline || item.program?.application_deadline || 'TBD'}</p>
                    <label style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                      <span className="muted-small">Notes</span>
                      <textarea
                        rows="4"
                        value={notesDraft[item.id] || item.notes || ''}
                        onChange={(event) => setNotesDraft((prev) => ({ ...prev, [item.id]: event.target.value }))}
                        placeholder="Add reminders, document checklists, and follow-up notes"
                      />
                    </label>
                    <div className="card-actions" style={{ marginTop: 12 }}>
                      {status !== 'saved' && item.id ? (
                        <>
                          <select value={item.status || status} onChange={(event) => updateStatus(item, event.target.value)} disabled={savingId === item.id}>
                            {STATUS_COLUMNS.map((column) => <option key={column} value={column}>{titleCase(column)}</option>)}
                          </select>
                          <Button variant="secondary" onClick={() => updateStatus(item, item.status || status)} loading={savingId === item.id}>Save Notes</Button>
                        </>
                      ) : (
                        <Button onClick={() => applySavedProgram(item)} loading={savingId === item.program?.id}>Apply</Button>
                      )}
                    </div>
                  </article>
                )) : (
                  <div className="empty-block"><p>No items in this column yet.</p></div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default MyApplications