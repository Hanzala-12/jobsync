import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Button from '../components/Button'
import { interviewAPI } from '../api/client'
import './MockInterview.css'

function MockInterview() {
  const location = useLocation()
  const [jobTitle, setJobTitle] = useState('')
  const [company, setCompany] = useState('')
  const [questions, setQuestions] = useState('')
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (location.state?.question) {
      setCurrentQuestion(location.state.question)
    }
  }, [location.state])

  const generateQuestions = async () => {
    if (!jobTitle) return
    setLoading(true)
    try {
      const response = await interviewAPI.generateQuestions({ job_title: jobTitle, company })
      setQuestions(response.data.questions || '')
    } finally {
      setLoading(false)
    }
  }

  const evaluateAnswer = async () => {
    if (!currentQuestion || !answer) return
    setLoading(true)
    try {
      const response = await interviewAPI.evaluate({ question: currentQuestion, answer })
      setFeedback(response.data.feedback || '')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mock-page">
      <div className="page-header">
        <h1>Mock Interview</h1>
        <p className="subtitle">Practice answers and get instant feedback.</p>
      </div>

      <div className="mock-grid">
        <section className="card-box">
          <h3>Generate Interview Questions</h3>
          <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} placeholder="Job title" />
          <input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Company (optional)" />
          <Button onClick={generateQuestions} loading={loading}>Generate Questions</Button>
          {questions && <pre className="result-box">{questions}</pre>}
        </section>

        <section className="card-box">
          <h3>Evaluate Your Answer</h3>
          <textarea
            rows={3}
            value={currentQuestion}
            onChange={(event) => setCurrentQuestion(event.target.value)}
            placeholder="Interview question"
          />
          <textarea
            rows={6}
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="Your answer"
          />
          <Button onClick={evaluateAnswer} loading={loading}>Get Feedback</Button>
          {feedback && <pre className="result-box">{feedback}</pre>}
        </section>
      </div>
    </div>
  )
}

export default MockInterview
