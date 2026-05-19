import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { interviewAPI, resumeAPI } from '../api/client'
import './Interview.css'

function Interview() {
  const navigate = useNavigate()
  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [loading, setLoading] = useState(false)
  const [questions, setQuestions] = useState([])
  const [versions, setVersions] = useState([])
  const [openItems, setOpenItems] = useState({})

  useEffect(() => {
    const stored = localStorage.getItem('jobsync_resume_text')
    if (stored) setResumeText(stored)
    resumeAPI.listVersions().then((res) => setVersions(res.data || []))
  }, [])

  const grouped = useMemo(() => ({
    technical: questions.filter((q) => q.type === 'technical'),
    behavioral: questions.filter((q) => q.type === 'behavioral'),
    gap: questions.filter((q) => q.type === 'gap'),
    curveball: questions.filter((q) => q.type === 'curveball'),
  }), [questions])

  const predict = async () => {
    setLoading(true)
    try {
      const response = await interviewAPI.predict({
        job_description: jobDescription,
        resume_text: resumeText,
        company,
        role,
      })
      setQuestions(response.data || [])
    } finally {
      setLoading(false)
    }
  }

  const section = (title, items, className = '') => (
    <section className="question-section">
      <h3>{title}</h3>
      {items.map((item, index) => {
        const key = `${title}-${index}`
        const open = !!openItems[key]
        return (
          <article className={`question-card ${className}`} key={key}>
            <p className="question-title">{item.question}</p>
            <p className="why">Why they'll ask this: {item.why_asked}</p>
            <button
              className="toggle"
              type="button"
              onClick={() => setOpenItems((prev) => ({ ...prev, [key]: !open }))}
            >
              {open ? 'Hide' : 'Show'} Strong Answer Should Include
            </button>
            {open && (
              <ul>
                {(item.strong_answer_includes || []).map((entry) => <li key={entry}>{entry}</li>)}
              </ul>
            )}
            <div className="question-foot">
              <span className="badge">{item.difficulty}</span>
              <Button
                size="small"
                variant="secondary"
                onClick={() => navigate('/mock-interview', { state: { question: item.question } })}
              >
                Practice This
              </Button>
            </div>
          </article>
        )
      })}
    </section>
  )

  return (
    <div className="interview-page">
      <div className="page-header">
        <h1>Interview Prep</h1>
        <p className="subtitle">Predict the likely questions for your exact profile.</p>
      </div>

      <section className="predict-inputs">
        <textarea
          rows={7}
          value={resumeText}
          onChange={(event) => setResumeText(event.target.value)}
          placeholder="Paste resume text or load from versions"
        />
        <select
          onChange={(event) => {
            const selected = versions.find((version) => String(version.id) === event.target.value)
            if (selected) {
              setResumeText(selected.content)
              localStorage.setItem('jobsync_resume_text', selected.content)
            }
          }}
          defaultValue=""
        >
          <option value="">Load from versions</option>
          {versions.map((version) => <option key={version.id} value={version.id}>{version.name}</option>)}
        </select>
        <textarea
          rows={7}
          value={jobDescription}
          onChange={(event) => setJobDescription(event.target.value)}
          placeholder="Paste job description"
        />
        <div className="inline-inputs">
          <input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Company" />
          <input value={role} onChange={(event) => setRole(event.target.value)} placeholder="Role" />
        </div>
        <Button onClick={predict} loading={loading}>Predict My Questions</Button>
      </section>

      {section('TECHNICAL QUESTIONS', grouped.technical)}
      {section('BEHAVIORAL QUESTIONS', grouped.behavioral)}
      {section('GAP QUESTIONS', grouped.gap, 'gap')}
      {section('CURVEBALL', grouped.curveball, 'curveball')}
    </div>
  )
}

export default Interview
