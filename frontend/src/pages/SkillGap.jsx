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
    <div className="skill-gap-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section className="app-card" style={{ padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Market Analysis</p>
          <h1 style={{ marginTop: 6 }}>Skill Gap Analysis</h1>
          <p className="subtitle">Compare multiple job descriptions to find the most requested missing skills.</p>
        </div>
        <div style={{ padding: '10px 14px', borderRadius: 14, background: 'var(--j-surface)', border: '1px solid var(--j-border)', color: 'var(--j-text-2)', fontWeight: 700 }}>Benchmark your stack</div>
      </section>

      <section className="panel-card fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {jobDescriptions.map((description, index) => (
          <div key={index} className="jd-box fade-up" style={{ position: 'relative', padding: 16, borderRadius: 16, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)' }}>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Job Description {index + 1}</span>
            <textarea
              className="text-area"
              value={description}
              onChange={(event) => updateDescription(index, event.target.value)}
              rows={4}
              placeholder="Paste job description text here..."
              style={{ marginTop: 10, marginBottom: 0, borderRadius: 14 }}
            />
            <button className="close-btn" type="button" onClick={() => removeDescription(index)} aria-label="Remove box" style={{ position: 'absolute', top: 12, right: 12, width: 32, height: 32, borderRadius: 10, border: '1px solid var(--j-border)', background: 'var(--j-surface)', display: 'grid', placeItems: 'center', color: 'var(--j-text-2)' }}>
              <X size={14} />
            </button>
          </div>
        ))}

        <div className="sg-actions" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Button variant="secondary" onClick={() => setJobDescriptions((prev) => [...prev, ''])}>
            <Plus size={14} style={{ display: 'inline', marginRight: 4 }}/> Add Another Job
          </Button>
          <Button onClick={analyze} loading={loading} disabled={!jobDescriptions[0].trim()}>
            <BarChart2 size={14} style={{ display: 'inline', marginRight: 4 }}/> Analyze Skill Frequencies
          </Button>
        </div>
      </section>

      {result && (
        <section className="sg-results fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)' }}>
          <span className="field-label" style={{ marginBottom: 16, display: 'block', fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Missing Skills (By Frequency)</span>

          {(result.missing_skills || []).length === 0 ? (
            <p className="text-area" style={{ border: 'none', background: 'transparent', margin: 0, color: 'var(--j-text-2)' }}>No missing skills found. You match perfectly!</p>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {(result.missing_skills || []).map((skill) => (
                <div className="skill-row fade-up" key={skill} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: 14, borderRadius: 14, background: 'var(--j-surface-2)', border: '1px solid var(--j-border)' }}>
                  <span className="skill-name" style={{ fontWeight: 700, color: 'var(--j-text-1)' }}>{skill}</span>
                  <span className="skill-meta" style={{ color: 'var(--j-text-2)' }}>Appears in {result.frequency?.[skill] || 0} job{result.frequency?.[skill] !== 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}

export default SkillGap
