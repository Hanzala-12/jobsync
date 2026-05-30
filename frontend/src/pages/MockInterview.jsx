import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Button from '../components/Button'
import { interviewAPI } from '../api/client'
import { MessageSquare, Sparkles } from 'lucide-react'
import './MockInterview.css'

function MockInterview() {
  const location = useLocation()
  const [jobTitle, setJobTitle] = useState('')
  const [company, setCompany] = useState('')
  const [questions, setQuestions] = useState('')
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState('')
  const [loadingQ, setLoadingQ] = useState(false)
  const [loadingF, setLoadingF] = useState(false)

  useEffect(() => {
    if (location.state?.question) {
      setCurrentQuestion(location.state.question)
    }
  }, [location.state])

  const generateQuestions = async () => {
    if (!jobTitle) return
    setLoadingQ(true)
    try {
      const response = await interviewAPI.generateQuestions({ job_title: jobTitle, company })
      setQuestions(response.data.questions || '')
    } finally {
      setLoadingQ(false)
    }
  }

  const evaluateAnswer = async () => {
    if (!currentQuestion || !answer) return
    setLoadingF(true)
    try {
      const response = await interviewAPI.evaluate({ question: currentQuestion, answer })
      setFeedback(response.data.feedback || '')
    } finally {
      setLoadingF(false)
    }
  }

  return (
    <div className="mock-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section className="app-card" style={{ padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Practice Mode</p>
          <h1 style={{ marginTop: 6 }}>Mock Interview</h1>
          <p className="subtitle">Practice your answers and receive AI-guided feedback.</p>
        </div>
        <div style={{ padding: '10px 14px', borderRadius: 14, background: 'var(--j-surface)', border: '1px solid var(--j-border)', color: 'var(--j-text-2)', fontWeight: 700 }}>One prompt at a time</div>
      </section>

      <div className="mock-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20, alignItems: 'start' }}>
        <section className="panel-card fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <MessageSquare size={18} color="var(--j-text-2)"/>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--j-text-1)' }}>Generate Questions</h3>
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            <div>
              <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Job Title</span>
              <input className="text-area" value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} placeholder="e.g. Senior Frontend Engineer" style={{ marginTop: 10, minHeight: 46, borderRadius: 14 }} />
            </div>

            <div>
              <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Company (Optional)</span>
              <input className="text-area" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="e.g. Spotify" style={{ marginTop: 10, minHeight: 46, borderRadius: 14 }} />
            </div>
          </div>

          <Button className="w-full" onClick={generateQuestions} loading={loadingQ} disabled={!jobTitle}>Generate Potential Questions</Button>

          {questions && (
            <div className="fade-up" style={{ marginTop: 8 }}>
              <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Generated Questions</span>
              <pre className="result-box" style={{ marginTop: 10, whiteSpace: 'pre-wrap', lineHeight: 1.7, background: 'var(--j-surface-2)', border: '1px solid var(--j-border)', borderRadius: 16, padding: 16 }}>{questions}</pre>
            </div>
          )}
        </section>

        <section className="panel-card fade-up" style={{ animationDelay: '0.1s', background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} color="var(--j-text-2)"/>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--j-text-1)' }}>Evaluate Your Answer</h3>
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            <div>
              <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Interview Question</span>
              <textarea
                className="text-area"
                rows={3}
                value={currentQuestion}
                onChange={(event) => setCurrentQuestion(event.target.value)}
                placeholder="Type or paste the interview question here..."
                style={{ marginTop: 10, borderRadius: 14 }}
              />
            </div>

            <div>
              <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Your Answer</span>
              <textarea
                className="text-area"
                rows={6}
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder="Draft your response here..."
                style={{ marginTop: 10, borderRadius: 14 }}
              />
            </div>
          </div>

          <Button className="w-full" onClick={evaluateAnswer} loading={loadingF} disabled={!answer || !currentQuestion}>Get AI Feedback</Button>

          {feedback && (
            <div className="fade-up" style={{ marginTop: 8 }}>
              <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Feedback & Suggestions</span>
              <pre className="result-box" style={{ marginTop: 10, whiteSpace: 'pre-wrap', lineHeight: 1.7, background: 'var(--j-surface-2)', border: '1px solid var(--j-border)', borderRadius: 16, padding: 16 }}>{feedback}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default MockInterview
