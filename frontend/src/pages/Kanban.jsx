import { useEffect, useMemo, useState } from 'react'
import { CalendarDays, Mail, MoveRight, ShieldAlert, Sparkles } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import apiClient from '../api/client'
import './Kanban.css'

const STATUSES = ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected']

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function calculateUrgency(urgency, status) {
  if (urgency?.level === 'red') return 'urgent-red'
  if (urgency?.level === 'yellow') return 'urgent-yellow'
  if (status === 'Interviewing') return 'urgent-red'
  return 'urgent-green'
}

function Kanban() {
  const [board, setBoard] = useState({
    Saved: [],
    Applied: [],
    Interviewing: [],
    Rejected: [],
    Offered: [],
  })
  const [loading, setLoading] = useState(true)
  const [draggingId, setDraggingId] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [followUpDraft, setFollowUpDraft] = useState('')
  const [draftTitle, setDraftTitle] = useState('')
  const [draftMeta, setDraftMeta] = useState('')
  const [selectedCard, setSelectedCard] = useState(null)
  const [draftLoading, setDraftLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBoard()
  }, [])

  const flattenedCards = useMemo(() => Object.values(board).flat(), [board])

  const fetchBoard = async () => {
    try {
      const response = await apiClient.get('/kanban/board')
      setBoard(response.data)
      setError(null)
    } catch (requestError) {
      console.error('Error fetching board:', requestError)
      setError('Failed to load Kanban board.')
    } finally {
      setLoading(false)
    }
  }

  const moveApplication = async (appId, newStatus) => {
    try {
      await apiClient.post('/kanban/move', { id: appId, new_status: newStatus })
      await fetchBoard()
    } catch (requestError) {
      console.error('Error moving application:', requestError)
      setError('Could not update application status.')
    }
  }

  const handleDragStart = (appId) => {
    setDraggingId(appId)
  }

  const handleDrop = async (status) => {
    if (!draggingId) return
    await moveApplication(draggingId, status)
    setDraggingId(null)
  }

  const openFollowUpModal = async (card) => {
    setSelectedCard(card)
    setDraftLoading(true)
    setModalOpen(true)
    setDraftTitle(`${card.role} at ${card.company}`)
    setDraftMeta(card.status)
    setFollowUpDraft('')

    try {
      const response = await apiClient.post('/kanban/follow-up-email', { id: card.id })
      setFollowUpDraft(response.data?.draft || '')
    } catch (requestError) {
      console.error('Error generating follow-up draft:', requestError)
      setFollowUpDraft('Failed to generate follow-up draft. Please try again.')
    } finally {
      setDraftLoading(false)
    }
  }

  const selectedCount = flattenedCards.length

  if (loading) {
    return (
      <div className="kanban-container">
        <h1>Loading Kanban Board...</h1>
      </div>
    )
  }

  return (
    <div className="kanban-container kanban-analytics">
      <div className="kanban-header">
        <div>
          <p className="eyebrow">Pipeline control</p>
          <h1>Application Tracker</h1>
          <p className="subtitle">Drag cards between stages, keep follow-ups visible, and act on urgency.</p>
        </div>
        <div className="kanban-header-stats">
          <div className="kanban-stat">
            <span>Total cards</span>
            <strong>{selectedCount}</strong>
          </div>
          <Button variant="outline" onClick={fetchBoard}>
            Refresh Board
          </Button>
        </div>
      </div>

      {error && <div className="kanban-error">{error}</div>}

      <div className="kanban-board">
        {STATUSES.map((status) => {
          const apps = board[status] || []
          return (
            <div
              key={status}
              className={`kanban-column ${draggingId ? 'droppable' : ''}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => handleDrop(status)}
            >
              <div className="column-header">
                <h3>{status}</h3>
                <span className="count">{apps.length}</span>
              </div>

              <div className="column-content">
                {apps.map((app) => {
                  const urgencyClass = calculateUrgency(app.urgency, app.status)
                  return (
                    <Card
                      key={app.id}
                      className={`kanban-card ${draggingId === app.id ? 'dragging' : ''}`}
                      draggable
                      onDragStart={() => handleDragStart(app.id)}
                      onDragEnd={() => setDraggingId(null)}
                    >
                      <div className="card-topline">
                        <div>
                          <h4>{app.role}</h4>
                          <p className="company">{app.company}</p>
                        </div>
                        <span className={`urgency-pill ${urgencyClass}`}>
                          {app.urgency?.label || 'On track'}
                        </span>
                      </div>

                      <div className="card-meta-grid">
                        <div className="card-meta-item">
                          <CalendarDays size={14} />
                          <span>Applied {formatDate(app.applied_date)}</span>
                        </div>
                        <div className="card-meta-item">
                          <Sparkles size={14} />
                          <span>ATS {app.ats_score ?? 'N/A'}</span>
                        </div>
                      </div>

                      {app.interview_date && (
                        <p className="date interview">Interview: {formatDate(app.interview_date)}</p>
                      )}

                      {app.next_action && <p className="next-action">{app.next_action}</p>}

                      <div className="move-buttons">
                        {status !== 'Saved' && (
                          <button onClick={() => moveApplication(app.id, 'Saved')}>← Saved</button>
                        )}
                        {status !== 'Applied' && (
                          <button onClick={() => moveApplication(app.id, 'Applied')}>Applied</button>
                        )}
                        {status !== 'Interviewing' && (
                          <button onClick={() => moveApplication(app.id, 'Interviewing')}>Interviewing</button>
                        )}
                        {status !== 'Offered' && status !== 'Rejected' && (
                          <>
                            <button onClick={() => moveApplication(app.id, 'Offered')} className="success">Offered</button>
                            <button onClick={() => moveApplication(app.id, 'Rejected')} className="danger">Rejected</button>
                          </>
                        )}
                      </div>

                      <div className="card-actions">
                        <button className="followup-button" onClick={() => openFollowUpModal(app)}>
                          <Mail size={14} /> Generate Follow-up Email
                        </button>
                        <button className="quick-move-button" onClick={() => moveApplication(app.id, status === 'Applied' ? 'Interviewing' : 'Applied')}>
                          <MoveRight size={14} /> Quick Shift
                        </button>
                      </div>
                    </Card>
                  )
                })}

                {apps.length === 0 && (
                  <div className="empty-column">
                    <ShieldAlert size={22} />
                    <p>No applications</p>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {modalOpen && (
        <div className="kanban-modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="kanban-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <p className="eyebrow">Follow-up email</p>
                <h3>{draftTitle}</h3>
                <p className="subtitle">Status: {draftMeta}</p>
              </div>
              <button className="modal-close" onClick={() => setModalOpen(false)}>×</button>
            </div>

            {draftLoading ? (
              <div className="modal-loading">
                <div className="skeleton skeleton-line" />
                <div className="skeleton skeleton-block" />
                <div className="skeleton skeleton-line short" />
              </div>
            ) : (
              <>
                <pre className="modal-draft">{followUpDraft}</pre>
                <div className="modal-actions">
                  <Button onClick={() => navigator.clipboard.writeText(followUpDraft)}>Copy</Button>
                  <Button variant="outline" onClick={() => selectedCard && openFollowUpModal(selectedCard)}>
                    Regenerate
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Kanban
