import { useMemo, useState } from 'react'
import { FileText, Download, Copy, RefreshCw } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { coverLetterAPI } from '../api/client'
import './CoverLetter.css'

const toneOptions = [
  { value: 'professional', label: 'Professional' },
  { value: 'warm', label: 'Warm' },
  { value: 'bold', label: 'Bold' },
  { value: 'concise', label: 'Concise' },
]

const CoverLetter = () => {
  const [formData, setFormData] = useState({
    company: '',
    role: '',
    job_description: '',
    tone: 'professional',
  })
  const [coverLetter, setCoverLetter] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  const wordCount = useMemo(
    () => coverLetter.trim().split(/\s+/).filter(Boolean).length,
    [coverLetter],
  )

  const readingTime = Math.max(1, Math.ceil(wordCount / 200))

  const handleGenerate = async (e) => {
    e.preventDefault()
    setLoading(true)
    setStatus('Generating a tailored draft...')

    try {
      const response = await coverLetterAPI.generate(formData)
      setCoverLetter(response.data.draft)
      setStatus('Draft ready')
    } catch (error) {
      console.error('Failed to generate cover letter:', error)
      setStatus('Generation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!coverLetter) return
    await navigator.clipboard.writeText(coverLetter)
    setStatus('Copied to clipboard')
  }

  const handleDownload = () => {
    if (!coverLetter) return
    const blob = new Blob([coverLetter], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${formData.company || 'cover-letter'}-${formData.role || 'draft'}.txt`
    link.click()
    URL.revokeObjectURL(url)
    setStatus('Downloaded draft')
  }

  return (
    <div className="cover-letter-page">
      <section className="cover-hero">
        <div>
          <p className="eyebrow">Cover Letter Generator</p>
          <h1>Draft polished letters with the right tone and a clear call to action.</h1>
          <p className="page-description">
            Generate a tailored cover letter, adjust the voice, and export a clean draft for editing.
          </p>
        </div>
        <div className="hero-metrics">
          <div>
            <span>Word Count</span>
            <strong>{wordCount}</strong>
          </div>
          <div>
            <span>Reading Time</span>
            <strong>{readingTime} min</strong>
          </div>
        </div>
      </section>

      <div className="cover-layout">
        <Card className="panel-card">
          <h2>Job Details</h2>
          <form onSubmit={handleGenerate} className="cover-letter-form">
            <div className="form-grid">
              <div className="form-group">
                <label>Company</label>
                <input
                  type="text"
                  value={formData.company}
                  onChange={(event) => setFormData({ ...formData, company: event.target.value })}
                  required
                  className="form-input"
                  placeholder="Acme Inc."
                />
              </div>

              <div className="form-group">
                <label>Role</label>
                <input
                  type="text"
                  value={formData.role}
                  onChange={(event) => setFormData({ ...formData, role: event.target.value })}
                  required
                  className="form-input"
                  placeholder="Frontend Engineer"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Tone</label>
              <div className="tone-grid">
                {toneOptions.map((tone) => (
                  <button
                    key={tone.value}
                    type="button"
                    className={`tone-pill ${formData.tone === tone.value ? 'selected' : ''}`}
                    onClick={() => setFormData({ ...formData, tone: tone.value })}
                  >
                    {tone.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label>Job Description</label>
              <textarea
                value={formData.job_description}
                onChange={(event) => setFormData({ ...formData, job_description: event.target.value })}
                rows="10"
                required
                className="form-input"
                placeholder="Paste the job description here..."
              />
            </div>

            <div className="action-row">
              <Button type="submit" loading={loading}>
                <FileText size={18} />
                Generate Draft
              </Button>
              <Button type="button" variant="secondary" onClick={handleGenerate} disabled={loading}>
                <RefreshCw size={18} />
                Regenerate
              </Button>
            </div>
          </form>
        </Card>

        <Card className="panel-card draft-panel">
          <div className="draft-header">
            <div>
              <h2>Draft Preview</h2>
              <p>{status || 'Your generated letter will appear here.'}</p>
            </div>
            <div className="draft-actions">
              <Button type="button" variant="secondary" onClick={handleCopy} disabled={!coverLetter}>
                <Copy size={16} />
                Copy
              </Button>
              <Button type="button" variant="secondary" onClick={handleDownload} disabled={!coverLetter}>
                <Download size={16} />
                Download
              </Button>
            </div>
          </div>

          {!coverLetter && !loading && (
            <div className="draft-empty">
              <p>Generate a draft to see a formatted cover letter preview.</p>
            </div>
          )}

          {loading && (
            <div className="draft-skeleton">
              <span className="skeleton-line wide" />
              <span className="skeleton-line" />
              <span className="skeleton-line" />
              <span className="skeleton-line medium" />
            </div>
          )}

          {coverLetter && !loading && (
            <div className="letter-preview">
              <div className="letter-meta">
                <span>{formData.company || 'Company'}</span>
                <span>{formData.role || 'Role'}</span>
                <span>{formData.tone}</span>
              </div>
              <pre>{coverLetter}</pre>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

export default CoverLetter
