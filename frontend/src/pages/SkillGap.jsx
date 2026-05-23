import { useState } from 'react'
import Button from '../components/Button'
import { intelligenceAPI } from '../api/client'
import { Plus, X, BarChart2 } from 'lucide-react'
import './SkillGap.css'

function SkillGap() {
  const [jobDescriptions, setJobDescriptions] = useState([''])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const updateDescription = (index, value) => {
    const next = [...jobDescriptions]
    next[index] = value
    setJobDescriptions(next)
  }

  const removeDescription = (index) => {
    if (jobDescriptions.length === 1) {
      setJobDescriptions([''])
      return
    }
    const next = jobDescriptions.filter((_, i) => i !== index)
    setJobDescriptions(next)
  }

  const analyze = async () => {
    setLoading(true)
    try {
      const payload = jobDescriptions.filter((item) => item.trim())
      const response = await intelligenceAPI.skillGap(payload)
      setResult(response.data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="skill-gap-page fade-up">
      <div className="page-header">
        <h1>Skill Gap Analysis</h1>
        <p className="subtitle">Compare multiple job descriptions to find the most requested missing skills.</p>
      </div>

      <section className="panel-card fade-up">
        {jobDescriptions.map((description, index) => (
          <div key={index} className="jd-box fade-up">
            <span className="field-label">JOB DESCRIPTION {index + 1}</span>
            <textarea
              className="text-area"
              value={description}
              onChange={(event) => updateDescription(index, event.target.value)}
              rows={4}
              placeholder="Paste job description text here..."
              style={{ marginBottom: 16 }}
            />
            <button className="close-btn" type="button" onClick={() => removeDescription(index)} aria-label="Remove box">
              <X size={14} />
            </button>
          </div>
        ))}
        
        <div className="sg-actions">
          <Button variant="secondary" onClick={() => setJobDescriptions((prev) => [...prev, ''])}>
            <Plus size={14} style={{ display: 'inline', marginRight: 4 }}/> Add Another Job
          </Button>
          <Button onClick={analyze} loading={loading} disabled={!jobDescriptions[0].trim()}>
            <BarChart2 size={14} style={{ display: 'inline', marginRight: 4 }}/> Analyze Skill Frequencies
          </Button>
        </div>
      </section>

      {result && (
        <section className="sg-results fade-up">
          <span className="field-label" style={{ marginBottom: 24 }}>MISSING SKILLS (BY FREQUENCY)</span>
          
          {(result.missing_skills || []).length === 0 ? (
            <p className="text-area" style={{ border: 'none', background: 'transparent' }}>No missing skills found. You match perfectly!</p>
          ) : (
            (result.missing_skills || []).map((skill) => (
              <div className="skill-row fade-up" key={skill}>
                <span className="skill-name">{skill}</span>
                <span className="skill-meta">Appears in {result.frequency?.[skill] || 0} job{result.frequency?.[skill] !== 1 ? 's' : ''}</span>
              </div>
            ))
          )}
        </section>
      )}
    </div>
  )
}

export default SkillGap
