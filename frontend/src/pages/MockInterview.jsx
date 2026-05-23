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
    <div className="mock-page fade-up">
      <div className="page-header">
        <h1>Mock Interview</h1>
        <p className="subtitle">Practice your answers and receive AI-guided feedback.</p>
      </div>

      <div className="mock-grid">
        <section className="panel-card fade-up">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
            <MessageSquare size={18} color="var(--j-text-2)"/>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Generate Questions</h3>
          </div>
          
          <span className="field-label">JOB TITLE</span>
          <input className="text-area" value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} placeholder="e.g. Senior Frontend Engineer" />
          
          <span className="field-label">COMPANY (OPTIONAL)</span>
          <input className="text-area" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="e.g. Spotify" />
          
          <Button className="w-full" onClick={generateQuestions} loading={loadingQ} disabled={!jobTitle}>Generate Potential Questions</Button>
          
          {questions && (
            <div className="fade-up" style={{ marginTop: 24 }}>
              <span className="field-label">GENERATED QUESTIONS</span>
              <pre className="result-box">{questions}</pre>
            </div>
          )}
        </section>

        <section className="panel-card fade-up" style={{ animationDelay: '0.1s' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
            <Sparkles size={18} color="var(--j-text-2)"/>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Evaluate Your Answer</h3>
          </div>
          
          <span className="field-label">INTERVIEW QUESTION</span>
          <textarea
            className="text-area"
            rows={3}
            value={currentQuestion}
            onChange={(event) => setCurrentQuestion(event.target.value)}
            placeholder="Type or paste the interview question here..."
          />
          
          <span className="field-label">YOUR ANSWER</span>
          <textarea
            className="text-area"
            rows={6}
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="Draft your response here..."
          />
          
          <Button className="w-full" onClick={evaluateAnswer} loading={loadingF} disabled={!answer || !currentQuestion}>Get AI Feedback</Button>
          
          {feedback && (
            <div className="fade-up" style={{ marginTop: 24 }}>
              <span className="field-label">FEEDBACK & SUGGESTIONS</span>
              <pre className="result-box">{feedback}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default MockInterview
