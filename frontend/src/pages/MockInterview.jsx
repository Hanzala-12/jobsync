import { useState } from 'react';
import Card from '../components/Card';
import Button from '../components/Button';
import apiClient from '../api/client'
import './MockInterview.css';

function MockInterview() {
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [questions, setQuestions] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateQuestions = async () => {
    if (!jobTitle) {
      alert('Please enter a job title');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.post('/interview/generate-questions', null, {
        params: { job_title: jobTitle, company }
      })
      setQuestions(response.data.questions)
      setLoading(false)
    } catch (error) {
      console.error('Error generating questions:', error)
      alert('Failed to generate questions')
      setLoading(false)
    }
  };

  const evaluateAnswer = async () => {
    if (!currentQuestion || !answer) {
      alert('Please enter both question and answer');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.post('/interview/evaluate', {
        question: currentQuestion,
        answer: answer
      })
      setFeedback(response.data.feedback)
      setLoading(false)
    } catch (error) {
      console.error('Error evaluating answer:', error)
      alert('Failed to evaluate answer')
      setLoading(false)
    }
  };

  return (
    <div className="mock-interview-container">
        <h1>Mock Interview Practice</h1>
        <p className="subtitle">Practice with AI-powered feedback</p>

        <div className="interview-sections">
          {/* Question Generator */}
          <Card>
            <h2>Generate Interview Questions</h2>
            <div className="form-group">
              <label>Job Title *</label>
              <input
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g., Software Engineer"
              />
            </div>
            
            <div className="form-group">
              <label>Company (Optional)</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g., Google"
              />
            </div>

            <Button onClick={generateQuestions} disabled={loading}>
              {loading ? 'Generating...' : 'Generate Questions'}
            </Button>

            {questions && (
              <div className="questions-result">
                <h3>Generated Questions:</h3>
                <pre>{questions}</pre>
              </div>
            )}
          </Card>

          {/* Answer Evaluator */}
          <Card>
            <h2>Evaluate Your Answer</h2>
            <div className="form-group">
              <label>Interview Question *</label>
              <textarea
                value={currentQuestion}
                onChange={(e) => setCurrentQuestion(e.target.value)}
                placeholder="Enter the interview question..."
                rows="3"
              />
            </div>

            <div className="form-group">
              <label>Your Answer *</label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type or paste your answer here..."
                rows="6"
              />
            </div>

            <Button onClick={evaluateAnswer} disabled={loading}>
              {loading ? 'Evaluating...' : 'Get Feedback'}
            </Button>

            {feedback && (
              <div className="feedback-result">
                <h3>AI Feedback:</h3>
                <div className="feedback-content">
                  {feedback}
                </div>
              </div>
            )}
          </Card>
        </div>

        <Card className="tips-card">
          <h3>💡 Interview Tips</h3>
          <ul>
            <li>Use the STAR method (Situation, Task, Action, Result) for behavioral questions</li>
            <li>Be specific with examples from your experience</li>
            <li>Practice out loud to improve your delivery</li>
            <li>Research the company before the interview</li>
            <li>Prepare questions to ask the interviewer</li>
          </ul>
        </Card>
      </div>
  );
}

export default MockInterview;
