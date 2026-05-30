import { useEffect, useMemo, useState } from 'react'
import apiClient from '../api/client'
import { GripVertical, Mail } from 'lucide-react'
import Button from '../components/Button'
import './Kanban.css'

const COLUMNS = ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected']

function Kanban() {
  const [board, setBoard] = useState({ Saved: [], Applied: [], Interviewing: [], Offered: [], Rejected: [] })
  const [dragId, setDragId] = useState(null)
  const [emailModal, setEmailModal] = useState({ open: false, text: '', title: '' })

  const loadBoard = async () => {
    const response = await apiClient.get('/kanban/board')
    setBoard(response.data || board)
  }

  useEffect(() => {
    loadBoard()
  }, [])

  const total = useMemo(() => Object.values(board).flat().length, [board])

  const move = async (id, status) => {
    await apiClient.post('/kanban/move', { id, new_status: status })
    loadBoard()
  }

  const urgencyColor = (item) => {
    if (item.urgency?.level === 'red') return 'urgency-red'
    if (item.urgency?.level === 'yellow') return 'urgency-yellow'
    return 'urgency-green'
  }

  return (
    <div className="kanban-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
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
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Pipeline Board</p>
          <h1 style={{ marginTop: 6 }}>Kanban Board</h1>
          <p className="subtitle">Track each application by stage.</p>
        </div>
        <div style={{ padding: '10px 14px', borderRadius: 14, background: 'var(--j-surface)', border: '1px solid var(--j-border)', color: 'var(--j-text-2)', fontWeight: 700 }}>{total} total active applications</div>
      </section>

      <div className="kanban-board" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16, alignItems: 'start' }}>
        {COLUMNS.map((column) => (
          <section
            key={column}
            className={`kanban-column ${column.toLowerCase()}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => dragId && move(dragId, column)}
            style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 16, boxShadow: 'var(--j-shadow-sm)', minHeight: 360 }}
          >
            <div className="column-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 14 }}>
              <h3 className="column-title" style={{ margin: 0, fontSize: 16, fontWeight: 800, color: 'var(--j-text-1)' }}>{column}</h3>
              <span className="column-count" style={{ padding: '6px 10px', borderRadius: 999, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, fontSize: 12 }}>{board[column]?.length || 0}</span>
            </div>

            <div className="kanban-cards" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {(board[column] || []).map((item) => (
                <article
                  key={item.id}
                  className="kanban-card"
                  draggable
                  onDragStart={() => setDragId(item.id)}
                  onDragEnd={() => setDragId(null)}
                  style={{ position: 'relative', border: '1px solid var(--j-border)', borderRadius: 16, padding: 16, background: 'var(--j-surface-2)', display: 'flex', flexDirection: 'column', gap: 12, boxShadow: '0 8px 20px rgba(15, 23, 42, 0.04)' }}
                >
                  <span className={`card-urgency ${urgencyColor(item)}`} style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, borderRadius: '16px 0 0 16px' }} />
                  <div className="card-drag-handle" style={{ display: 'inline-flex', width: 28, height: 28, alignItems: 'center', justifyContent: 'center', borderRadius: 10, background: 'var(--j-surface)', color: 'var(--j-text-3)' }}>
                    <GripVertical size={14} />
                  </div>
                  
                  <div className="card-body">
                    <p className="card-company" style={{ margin: 0, fontSize: 13, fontWeight: 700, color: 'var(--j-text-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{item.company}</p>
                    <p className="card-role" style={{ margin: '4px 0 0', fontSize: 15, fontWeight: 800, color: 'var(--j-text-1)' }}>{item.role}</p>
                  </div>
                  
                  <div className="card-footer" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
                    <p className="card-date" style={{ margin: 0, color: 'var(--j-text-2)', fontSize: 13 }}>{item.applied_date ? new Date(item.applied_date).toLocaleDateString() : 'No date'}</p>
                    {item.ats_score !== null && item.ats_score !== undefined && (
                      <span className="card-ats" style={{ padding: '6px 10px', borderRadius: 999, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, fontSize: 12 }}>ATS {item.ats_score}</span>
                    )}
                  </div>
                  
                  <button
                    type="button"
                    className="follow-btn"
                    onClick={async () => {
                      const response = await apiClient.post('/kanban/follow-up-email', { id: item.id })
                      setEmailModal({
                        open: true,
                        text: response.data?.draft || '',
                        title: `Follow-up: ${item.role} at ${item.company}`,
                      })
                    }}
                    style={{ minHeight: 38, borderRadius: 12, border: '1px solid rgba(58,87,232,0.18)', background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                  >
                    <Mail size={12} /> Email Draft
                  </button>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>

      {emailModal.open && (
        <div className="email-modal-overlay" onClick={() => setEmailModal({ open: false, text: '', title: '' })}>
          <div className="email-modal-content fade-up" onClick={(event) => event.stopPropagation()} style={{ width: 'min(100%, 760px)', maxHeight: '80vh', overflow: 'auto', background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-lg)' }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--j-text-1)' }}>{emailModal.title}</h3>
            <pre style={{ marginTop: 16, whiteSpace: 'pre-wrap', lineHeight: 1.7, color: 'var(--j-text-2)', background: 'var(--j-surface-2)', border: '1px solid var(--j-border)', borderRadius: 16, padding: 16 }}>{emailModal.text}</pre>
            <Button className="w-full" onClick={() => setEmailModal({ open: false, text: '', title: '' })}>Close</Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Kanban
