import { useState } from 'react'
import Button from '../components/Button'
import { intelligenceAPI } from '../api/client'
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
    <div className="skill-gap-page">
      <div className="page-header">
        <h1>Skill Gap</h1>
        <p className="subtitle">Compare job requirements and identify missing skills.</p>
      </div>

      <section className="skill-form">
        {jobDescriptions.map((description, index) => (
          <textarea
            key={index}
            value={description}
            onChange={(event) => updateDescription(index, event.target.value)}
            rows={4}
            placeholder={`Job description ${index + 1}`}
          />
        ))}
        <div className="actions">
          <Button variant="secondary" onClick={() => setJobDescriptions((prev) => [...prev, ''])}>Add Another</Button>
          <Button onClick={analyze} loading={loading}>Analyze Skills</Button>
        </div>
      </section>

      {result && (
        <section className="result-box">
          <p className="section-label">MISSING SKILLS</p>
          {(result.missing_skills || []).map((skill) => (
            <div className="skill-row" key={skill}>
              <span>{skill}</span>
              <small>Appears in {result.frequency?.[skill] || 0} job(s)</small>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}

export default SkillGap
