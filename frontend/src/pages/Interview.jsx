import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { interviewAPI, resumeAPI } from '../api/client'
import { Target, ChevronDown, ChevronUp, Play } from 'lucide-react'
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
    resumeAPI.listVersions().then((res) => {
      const d = res.data
      setVersions(Array.isArray(d) ? d : (d?.versions || d?.data || []))
    }).catch(() => setVersions([]))
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
      const d = response.data
      setQuestions(Array.isArray(d) ? d : (d?.questions || d?.data || []))
    } finally {
      setLoading(false)
    }
  }

  const section = (title, items, className = '') => {
    if (!items || items.length === 0) return null
    return (
      <section className="question-section fade-up">
        <h3>{title}</h3>
        {items.map((item, index) => {
          const key = `${title}-${index}`
          const open = !!openItems[key]
          return (
            <article className={`question-card ${className} fade-up`} key={key}>
              <p className="question-title">{item.question}</p>
              <p className="question-why">Why they'll ask this: {item.why_asked}</p>
              <button
                className="toggle-btn"
                type="button"
                onClick={() => setOpenItems((prev) => ({ ...prev, [key]: !open }))}
              >
                {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                {open ? 'Hide Strong Answer Framework' : 'Show Strong Answer Framework'}
              </button>
              {open && (
                <ul>
                  {(item.strong_answer_includes || []).map((entry) => <li key={entry}>{entry}</li>)}
                </ul>
              )}
              <div className="question-foot">
                <span className="diff-badge">{item.difficulty}</span>
                <Button
                  size="small"
                  variant="secondary"
                  onClick={() => navigate('/mock-interview', { state: { question: item.question } })}
                >
                  <Play size={12} style={{ display: 'inline', marginRight: 4 }}/> Practice This
                </Button>
              </div>
            </article>
          )
        })}
      </section>
    )
  }

  return (
    <div className="interview-page fade-up">
      <div className="page-header">
        <h1>Interview Prediction</h1>
        <p className="subtitle">Analyze your resume against a job description to predict likely questions.</p>
      </div>

      <section className="panel-card fade-up">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
          <Target size={18} color="var(--j-text-2)"/>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--j-text-1)', margin: 0 }}>Prediction Engine</h3>
        </div>

        <span className="field-label">YOUR RESUME / BACKGROUND</span>
        <textarea
          className="text-area"
          rows={7}
          value={resumeText}
          onChange={(event) => setResumeText(event.target.value)}
          placeholder="Paste resume text or load from versions below..."
          style={{ marginBottom: 12 }}
        />
        
        {versions.length > 0 && (
          <select
            className="text-area"
            style={{ padding: '0 12px', height: 44 }}
            onChange={(event) => {
              const selected = versions.find((version) => String(version.id) === event.target.value)
              if (selected) {
                setResumeText(selected.content)
                localStorage.setItem('jobsync_resume_text', selected.content)
              }
            }}
            defaultValue=""
          >
            <option value="">Load from saved tailored versions...</option>
            {versions.map((version) => <option key={version.id} value={version.id}>{version.name}</option>)}
          </select>
        )}
        
        <span className="field-label">TARGET JOB DESCRIPTION</span>
        <textarea
          className="text-area"
          rows={7}
          value={jobDescription}
          onChange={(event) => setJobDescription(event.target.value)}
          placeholder="Paste job description..."
        />
        
        <div className="inline-inputs">
          <div style={{ flex: 1 }}>
            <span className="field-label">COMPANY</span>
            <input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="e.g. Acme Corp" />
          </div>
          <div style={{ flex: 1 }}>
            <span className="field-label">ROLE</span>
            <input value={role} onChange={(event) => setRole(event.target.value)} placeholder="e.g. Senior Dev" />
          </div>
        </div>
        
        <Button onClick={predict} loading={loading} disabled={!resumeText || !jobDescription}>Predict My Questions</Button>
      </section>

      {questions.length > 0 && (
        <div className="fade-up">
          {section('TECHNICAL & ROLE-SPECIFIC', grouped.technical)}
          {section('BEHAVIORAL & CULTURE FIT', grouped.behavioral)}
          {section('WEAKNESS / VULNERABILITY QUESTIONS', grouped.gap, 'gap')}
          {section('CURVEBALL QUESTIONS', grouped.curveball, 'curveball')}
        </div>
      )}
    </div>
  )
}

export default Interview
