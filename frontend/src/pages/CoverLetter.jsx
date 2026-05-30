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
    <div className="cover-page fade-up">
      <div className="page-header">
        <h1>Cover Letter Generator</h1>
        <p className="subtitle">Craft tailored, professional cover letters instantly based on specific job descriptions.</p>
      </div>

      <div className="cover-grid">
        <section className="panel-card fade-up">
          <span className="field-label">JOB TITLE</span>
          <input 
            className="text-area" 
            style={{ marginBottom: 16 }}
            value={jobTitle} 
            onChange={(event) => setJobTitle(event.target.value)} 
            placeholder="e.g. Senior Frontend Engineer" 
          />
          
          <span className="field-label">COMPANY</span>
          <input 
            className="text-area" 
            style={{ marginBottom: 16 }}
            value={company} 
            onChange={(event) => setCompany(event.target.value)} 
            placeholder="e.g. Acme Corp" 
          />
          
          <span className="field-label">JOB DESCRIPTION</span>
          <textarea
            className="text-area"
            rows={10}
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            placeholder="Paste the full job description here..."
            style={{ marginBottom: 16 }}
          />
          
          <span className="field-label">TONE AND STYLE</span>
          <div className="tone-row">
            {tones.map((item) => (
              <button key={item} className={`tone-btn ${tone === item ? 'active' : ''}`} onClick={() => setTone(item)}>
                {item}
              </button>
            ))}
          </div>
          <Button className="w-full" onClick={generate} loading={loading}>Generate Cover Letter</Button>
        </section>

        <section className="panel-card fade-up" style={{ animationDelay: '0.1s' }}>
          {!draft ? (
            <div className="empty-results">
              <FileText size={32} />
              <p>Your generated letter will appear here.</p>
            </div>
          ) : (
            <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <span className="field-label">GENERATED DRAFT</span>
              <div className="letter-content">{draft}</div>
              
              <div className="letter-meta">
                {wordCount} words • Est. {readingTime} min read
              </div>
              
              <div className="letter-actions">
                <div>
                  <button className="icon-btn-text" onClick={copyDraft}><Copy size={14} /> Copy Document</button>
                  <button className="icon-btn-text" onClick={downloadPdf} disabled={downloading}><Download size={14} /> Download as PDF</button>
                </div>
                <button type="button" className="regen-btn" onClick={generate}><RefreshCw size={12} style={{ display: 'inline', marginRight: 4 }}/>Regenerate</button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default CoverLetter
