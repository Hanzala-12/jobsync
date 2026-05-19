import { useEffect, useMemo, useState } from 'react'
import apiClient from '../api/client'
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
    if (item.urgency?.level === 'red') return 'dot-red'
    if (item.urgency?.level === 'yellow') return 'dot-yellow'
    return 'dot-green'
  }

  return (
    <div className="kanban-page">
      <div className="page-header">
        <h1>Kanban Board</h1>
        <p className="subtitle">Track each application by stage.</p>
      </div>

      <p className="summary">{total} total cards</p>

      <div className="board-grid">
        {COLUMNS.map((column) => (
          <section
            key={column}
            className={`board-column ${column.toLowerCase()}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => dragId && move(dragId, column)}
          >
            <header>
              <h3>{column}</h3>
              <span>{board[column]?.length || 0}</span>
            </header>

            <div className="cards">
              {(board[column] || []).map((item) => (
                <article
                  key={item.id}
                  className="kanban-card"
                  draggable
                  onDragStart={() => setDragId(item.id)}
                  onDragEnd={() => setDragId(null)}
                >
                  <span className={`urgency ${urgencyColor(item)}`} />
                  <p className="company">{item.company}</p>
                  <p className="role">{item.role}</p>
                  <p className="date">{item.applied_date || '-'}</p>
                  {item.ats_score !== null && item.ats_score !== undefined && (
                    <span className="ats-pill">ATS {item.ats_score}</span>
                  )}
                  <p className="drag-handle">⠿</p>
                  <button
                    type="button"
                    className="follow-link"
                    onClick={async () => {
                      const response = await apiClient.post('/kanban/follow-up-email', { id: item.id })
                      setEmailModal({
                        open: true,
                        text: response.data?.draft || '',
                        title: `${item.role} at ${item.company}`,
                      })
                    }}
                  >
                    Generate Follow-up Email
                  </button>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>

      {emailModal.open && (
        <div className="modal" onClick={() => setEmailModal({ open: false, text: '', title: '' })}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>{emailModal.title}</h3>
            <pre>{emailModal.text}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default Kanban
