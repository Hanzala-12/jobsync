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
    <div className="kanban-page fade-up">
      <div className="page-header kanban-header-box">
        <h1>Kanban Board</h1>
        <p className="subtitle">Track each application by stage.</p>
        <p className="summary-text">{total} total active applications</p>
      </div>

      <div className="kanban-board">
        {COLUMNS.map((column) => (
          <section
            key={column}
            className={`kanban-column ${column.toLowerCase()}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => dragId && move(dragId, column)}
          >
            <div className="column-header">
              <h3 className="column-title">{column}</h3>
              <span className="column-count">{board[column]?.length || 0}</span>
            </div>

            <div className="kanban-cards">
              {(board[column] || []).map((item) => (
                <article
                  key={item.id}
                  className="kanban-card"
                  draggable
                  onDragStart={() => setDragId(item.id)}
                  onDragEnd={() => setDragId(null)}
                >
                  <span className={`card-urgency ${urgencyColor(item)}`} />
                  <div className="card-drag-handle">
                    <GripVertical size={14} />
                  </div>
                  
                  <div className="card-body">
                    <p className="card-company">{item.company}</p>
                    <p className="card-role">{item.role}</p>
                  </div>
                  
                  <div className="card-footer">
                    <p className="card-date">{item.applied_date ? new Date(item.applied_date).toLocaleDateString() : 'No date'}</p>
                    {item.ats_score !== null && item.ats_score !== undefined && (
                      <span className="card-ats">ATS {item.ats_score}</span>
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
          <div className="email-modal-content fade-up" onClick={(event) => event.stopPropagation()}>
            <h3>{emailModal.title}</h3>
            <pre>{emailModal.text}</pre>
            <Button className="w-full" onClick={() => setEmailModal({ open: false, text: '', title: '' })}>Close</Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Kanban
