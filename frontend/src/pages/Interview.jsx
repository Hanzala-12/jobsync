import { useState } from 'react'
import { MessageSquare } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { intelligenceAPI } from '../api/client'
import './Interview.css'

const Interview = () => {
  const [role, setRole] = useState('')
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)

  const handleGenerate = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await intelligenceAPI.interviewPrep(role)
      setQuestions(response.data.questions)
    } catch (error) {
      console.error('Failed to generate questions:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="interview-page">
      <div className="page-header">
        <h1>Interview Preparation</h1>
        <p className="page-description">Get AI-generated interview questions and answers</p>
      </div>

      <Card title="Generate Questions">
        <form onSubmit={handleGenerate} className="interview-form">
          <div className="form-group">
            <label>Role</label>
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g., Software Engineer"
              required
              className="form-input"
            />
          </div>
          <Button type="submit" loading={loading}>
            <MessageSquare size={20} />
            Generate Questions
          </Button>
        </form>
      </Card>

      {questions.length > 0 && (
        <div className="questions-list">
          {questions.map((q, index) => (
            <Card key={index} title={`Question ${index + 1}`}>
              <div className="question-item">
                <p className="question-text">{q.question}</p>
                {q.suggested_answer && (
                  <div className="answer-section">
                    <h4>Suggested Answer:</h4>
                    <p className="answer-text">{q.suggested_answer}</p>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default Interview
