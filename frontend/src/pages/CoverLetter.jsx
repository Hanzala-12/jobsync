import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Button from '../components/Button'
import { coverLetterAPI } from '../api/client'
import { FileText, Copy, Download, RefreshCw } from 'lucide-react'
import './CoverLetter.css'

const tones = ['Professional', 'Enthusiastic', 'Concise']

function CoverLetter() {
  const location = useLocation()
  const [jobTitle, setJobTitle] = useState('')
  const [company, setCompany] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [tone, setTone] = useState('Professional')
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (location.state?.job) {
      setJobTitle(location.state.job.title || '')
      setCompany(location.state.job.company || '')
      setJobDescription(location.state.job.description || '')
    }
  }, [location.state])

  const wordCount = useMemo(() => draft.trim().split(/\s+/).filter(Boolean).length, [draft])
  const readingTime = Math.max(1, Math.ceil(wordCount / 200))

  const generate = async () => {
    setLoading(true)
    try {
      const response = await coverLetterAPI.generate({
        role: jobTitle,
        company,
        job_description: jobDescription,
        tone: tone.toLowerCase(),
      })
      setDraft(response.data?.draft || '')
    } finally {
      setLoading(false)
    }
  }

  const copyDraft = async () => {
    await navigator.clipboard.writeText(draft)
  }

  const downloadPdf = async () => {
    setDownloading(true)
    try {
      const response = await coverLetterAPI.download({
        role: jobTitle,
        company,
        job_description: jobDescription,
        tone: tone.toLowerCase(),
      })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `cover-letter-${(jobTitle || 'draft').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="cover-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        className="app-card"
        style={{
          padding: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>AI Writing Studio</p>
          <h1 style={{ marginTop: 6 }}>Cover Letter Generator</h1>
          <p className="subtitle">Craft tailored, professional cover letters instantly based on specific job descriptions.</p>
        </div>
        <div
          style={{
            padding: 16,
            borderRadius: 16,
            background: 'linear-gradient(135deg, rgba(58,87,232,0.10), rgba(16,185,129,0.08))',
            border: '1px solid rgba(58,87,232,0.12)',
            minWidth: 220,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <FileText size={18} color="var(--j-accent)" />
            <strong style={{ color: 'var(--j-text-1)' }}>Fast draft output</strong>
          </div>
          <p style={{ margin: 0, color: 'var(--j-text-2)', lineHeight: 1.6 }}>Generate a polished letter, review the draft, and export a PDF in one flow.</p>
        </div>
      </section>

      <div className="cover-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 0.95fr) minmax(0, 1.05fr)', gap: 20, alignItems: 'start' }}>
        <section className="panel-card fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'grid', gap: 12 }}>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Job Title</span>
            <input
              className="text-area"
              style={{ marginBottom: 0, minHeight: 46, borderRadius: 14 }}
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
              placeholder="e.g. Senior Frontend Engineer"
            />

            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Company</span>
            <input
              className="text-area"
              style={{ marginBottom: 0, minHeight: 46, borderRadius: 14 }}
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="e.g. Acme Corp"
            />

            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Job Description</span>
            <textarea
              className="text-area"
              rows={10}
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the full job description here..."
              style={{ marginBottom: 0, borderRadius: 14 }}
            />
          </div>

          <div>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Tone and Style</span>
            <div className="tone-row" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
              {tones.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`tone-btn ${tone === item ? 'active' : ''}`}
                  onClick={() => setTone(item)}
                  style={{ minHeight: 38, padding: '0 14px', borderRadius: 999, border: tone === item ? '1px solid rgba(58,87,232,0.18)' : '1px solid var(--j-border)', background: tone === item ? 'rgba(58,87,232,0.10)' : 'var(--j-surface-2)', color: tone === item ? 'var(--j-accent)' : 'var(--j-text-2)', fontWeight: 700 }}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <Button className="w-full" onClick={generate} loading={loading}>Generate Cover Letter</Button>
        </section>

        <section className="panel-card fade-up" style={{ animationDelay: '0.1s', background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', minHeight: 520 }}>
          {!draft ? (
            <div className="empty-results" style={{ minHeight: 420, borderRadius: 16, background: 'linear-gradient(180deg, rgba(248,250,252,0.9), rgba(255,255,255,0.95))', border: '1px dashed var(--j-border)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <FileText size={32} />
              <p>Your generated letter will appear here.</p>
            </div>
          ) : (
            <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Generated Draft</span>
                <div className="letter-meta" style={{ color: 'var(--j-text-2)', fontSize: 13 }}>{wordCount} words • Est. {readingTime} min read</div>
              </div>

              <div className="letter-content" style={{ flex: 1, whiteSpace: 'pre-wrap', lineHeight: 1.75, color: 'var(--j-text-1)', background: 'var(--j-surface-2)', border: '1px solid var(--j-border)', borderRadius: 16, padding: 20 }}>{draft}</div>

              <div className="letter-actions" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button type="button" className="icon-btn-text" onClick={copyDraft} style={{ minHeight: 40, padding: '0 14px', borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface)', color: 'var(--j-text-1)', display: 'inline-flex', alignItems: 'center', gap: 8 }}><Copy size={14} /> Copy Document</button>
                  <button type="button" className="icon-btn-text" onClick={downloadPdf} disabled={downloading} style={{ minHeight: 40, padding: '0 14px', borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface)', color: 'var(--j-text-1)', display: 'inline-flex', alignItems: 'center', gap: 8 }}><Download size={14} /> Download as PDF</button>
                </div>
                <button type="button" className="regen-btn" onClick={generate} style={{ minHeight: 40, padding: '0 14px', borderRadius: 12, border: '1px solid rgba(58,87,232,0.18)', background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, display: 'inline-flex', alignItems: 'center' }}><RefreshCw size={12} style={{ display: 'inline', marginRight: 4 }}/>Regenerate</button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default CoverLetter
