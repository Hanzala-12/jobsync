import { useEffect, useMemo, useRef, useState } from 'react'
import { apiActions, jobsAPI } from '../api/client'
import Button from './Button'
import { CheckCircle2, Download, X, RefreshCw, AlertTriangle } from 'lucide-react'
import './ResumeModal.css'

function scoreClass(score) {
  if (score < 50) return 'bad'
  if (score < 76) return 'ok'
  return 'good'
}

function buildStandaloneHtml(result) {
  const text = String(result?.fixed_resume_text || result?.rewritten || result?.simple_text_version || '').trim()
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const sections = []
  let current = null

  const headingMap = {
    'summary': 'Summary',
    'professional summary': 'Summary',
    'profile': 'Summary',
    'skills': 'Skills',
    'core skills': 'Skills',
    'technical skills': 'Skills',
    'experience': 'Experience',
    'professional experience': 'Experience',
    'work experience': 'Experience',
    'education': 'Education',
    'academic background': 'Education',
    'projects': 'Projects',
    'project experience': 'Projects',
    'contact': 'Contact',
  }

  const pushCurrent = () => {
    if (current && current.lines.length) {
      sections.push(current)
    }
  }

  const normalizeHeading = (line) => line.toLowerCase().replace(/[:\-]+$/, '').trim()

  for (const line of lines) {
    const canonicalHeading = headingMap[normalizeHeading(line)]
    if (canonicalHeading) {
      pushCurrent()
      current = { title: canonicalHeading, lines: [] }
      continue
    }
    if (!current) {
      current = { title: 'Summary', lines: [] }
    }
    current.lines.push(line)
  }
  pushCurrent()

  const fontStack = 'Arial, Calibri, sans-serif'
  const displayTitles = {
    Summary: 'Professional Summary',
    Skills: 'Core Skills',
    Experience: 'Experience',
    Education: 'Education',
    Projects: 'Projects',
    Contact: 'Contact',
  }
  const sectionMarkup = sections
    .map((section) => {
      const bullets = section.lines.filter((line) => /^[-•]\s+/.test(line))
      const prose = section.lines.filter((line) => !/^[-•]\s+/.test(line))
      const bulletMarkup = bullets.length
        ? `<ul>${bullets.map((line) => `<li>${line.replace(/^[-•]\s+/, '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</li>`).join('')}</ul>`
        : ''
      const proseMarkup = prose.map((line) => `<p>${line.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`).join('')
      return `<section class="resume-fallback-section"><h2>${displayTitles[section.title] || section.title}</h2>${proseMarkup}${bulletMarkup}</section>`
    })
    .join('')

  return `<!doctype html>
<html><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
body{font-family:${fontStack};margin:0;padding:24px;color:#101828;background:#fff;line-height:1.5}
.resume-fallback-wrap{max-width:860px;margin:0 auto;padding:24px;border:1px solid #d0d5dd;border-radius:16px}
.resume-fallback-header{padding-bottom:16px;margin-bottom:20px;border-bottom:1px solid #d0d5dd}
.resume-fallback-header h1{margin:0 0 6px;font-size:28px}
.resume-fallback-header p{margin:0;color:#475467;font-size:13px}
.resume-fallback-section{margin-bottom:18px}
.resume-fallback-section h2{margin:0 0 10px;font-size:15px;padding-bottom:6px;border-bottom:1px solid #d0d5dd}
.resume-fallback-section p{margin:0 0 8px;font-size:13px}
.resume-fallback-section ul{margin:0 0 8px 18px;padding:0;font-size:13px}
.resume-fallback-section li{margin:0 0 6px}
@media print{body{padding:0}.resume-fallback-wrap{border:0;border-radius:0;padding:0}}
</style></head><body>
<div class="resume-fallback-wrap" id="resume-export-root">
<div class="resume-fallback-header"><h1>${String(result?.candidate_name || 'Tailored Resume').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</h1><p>${String(result?.tagline || 'ATS-friendly resume preview').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p></div>
${sectionMarkup || `<section class="resume-fallback-section"><h2>Summary</h2><p>${text.replace(/\n/g, '<br />')}</p></section>`}
</div></body></html>`
}

function ResumeModal({ open, job, onClose }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [showAfter, setShowAfter] = useState(true)
  const [resolvedJobId, setResolvedJobId] = useState(null)
  const iframeRef = useRef(null)

  const pdfReady = Boolean(result) && Boolean(resolvedJobId)
  const isExternalResult = Boolean(job?.previewResult)
  const previewHtml = result?.html_resume || buildStandaloneHtml(result)

  useEffect(() => {
    if (!open || !job) return
    if (isExternalResult) {
      setLoading(false)
      setError('')
      setResult(job.previewResult)
      setResolvedJobId(job.id || null)
      setShowAfter(true)
      return undefined
    }
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError('')
      setResult(null)
      setResolvedJobId(job.id || null)
      try {
        let jobId = job.id
        if (!jobId) {
          const upsert = await jobsAPI.upsert(job)
          jobId = upsert.data?.id || upsert.data?.job_id || null
        }

        if (!jobId) {
          throw new Error('Could not prepare this job for resume tailoring.')
        }

        const response = await apiActions.buildResume(jobId)
        if (!cancelled) {
          setResult(response.data)
          setResolvedJobId(jobId)
          setShowAfter(true)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.userMessage || err?.message || 'Resume tailoring failed.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [open, job, isExternalResult])

  const score = useMemo(() => Math.round(result?.ats_score || 0), [result])
  const scoreWidth = `${Math.max(0, Math.min(100, score))}%`

  const downloadPdf = async () => {
    if (!resolvedJobId) return
    const response = await apiActions.downloadResumePdf(resolvedJobId)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'tailored_resume.pdf'
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    window.setTimeout(() => {
      link.remove()
      window.URL.revokeObjectURL(url)
    }, 1000)
  }

  if (!open) return null

  return (
    <div className="resume-modal-overlay" onClick={onClose}>
      <div className="resume-modal" onClick={(event) => event.stopPropagation()}>
        <div className="resume-modal-header">
          <div>
            <p className="resume-modal-kicker">ATS RESUME BUILDER</p>
            <h3>{job?.title || 'Tailored Resume'}</h3>
            <p className="resume-modal-subtitle">{job?.company || 'Target company'} · {job?.location || 'Remote'}</p>
          </div>
          <button type="button" className="resume-modal-close" onClick={onClose} aria-label="Close resume builder">
            <X size={18} />
          </button>
        </div>

        {loading && (
          <div className="resume-modal-loading">
            <div className="resume-spinner" />
            <p>Analyzing the source resume, fixing weak phrasing, and generating ATS-friendly output...</p>
          </div>
        )}

        {!loading && error && (
          <div className="resume-modal-error">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {!loading && result && (
          <div className="resume-modal-body">
            <div className="resume-score-card">
              <div className={`resume-score-circle ${scoreClass(score)}`}>{score}</div>
              <div className="resume-score-copy">
                <p className="field-label">ATS MATCH SCORE</p>
                <p>{result.validation_message || 'Your resume passed ATS validation.'}</p>
                <div className="resume-score-bar">
                  <div className={`resume-score-bar-fill ${scoreClass(score)}`} style={{ width: scoreWidth }} />
                </div>
                <div className="resume-status-row">
                  <span className={`resume-status-pill ${result.validation_passed ? 'good' : 'warn'}`}>
                    <CheckCircle2 size={12} /> {result.validation_passed ? 'Validation passed' : 'Validation warning'}
                  </span>
                  <span className="resume-status-pill neutral">{result.cached ? 'Cached result' : 'Fresh build'}</span>
                </div>
              </div>
            </div>

            <div className="resume-toggle-row">
              <button type="button" className={`resume-toggle ${showAfter ? 'active' : ''}`} onClick={() => setShowAfter(true)}>
                After
              </button>
              <button type="button" className={`resume-toggle ${!showAfter ? 'active' : ''}`} onClick={() => setShowAfter(false)}>
                Before
              </button>
            </div>

            <div className="resume-diff-grid">
              <section className="resume-diff-card">
                <h4>{showAfter ? 'OPTIMIZED RESUME' : 'ORIGINAL RESUME'}</h4>
                <pre className="resume-diff-text">{showAfter ? result.fixed_resume_text : result.original_resume}</pre>
              </section>
              <section className="resume-diff-card">
                <h4>WHAT CHANGED</h4>
                <ul className="resume-change-list">
                  {(result.changes_made || []).map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </section>
            </div>

            <section className="resume-html-panel">
              <div className="resume-panel-header">
                <h4>HTML PREVIEW</h4>
                <span>{pdfReady ? 'PDF export ready' : 'Loading PDF library...'}</span>
              </div>
              <iframe ref={iframeRef} title="Tailored resume preview" className="resume-preview-frame" srcDoc={previewHtml} />
            </section>

            {result?.keyword_debug?.missing_keywords && result.keyword_debug.missing_keywords.length > 0 && (
              <section className="resume-missing-keywords">
                <h4>Missing keywords for higher ATS score</h4>
                <div className="missing-keywords-list">
                  {result.keyword_debug.missing_keywords.map((kw, idx) => (
                    <span key={`${kw}-${idx}`} className="missing-keyword-badge">{kw}</span>
                  ))}
                </div>
                <p className="missing-keywords-note">Add these keywords to your experience bullets or skills to improve your match score.</p>
              </section>
            )}

            <div className="resume-modal-actions">
              <Button variant="secondary" onClick={() => setShowAfter((value) => !value)}>
                <RefreshCw size={14} style={{ marginRight: 6 }} /> Toggle before/after
              </Button>
              <Button variant="secondary" onClick={downloadPdf} disabled={!pdfReady}>
                <Download size={14} style={{ marginRight: 6 }} /> {pdfReady ? 'Download PDF' : 'Preparing PDF...'}
              </Button>
              <Button onClick={onClose}>Close</Button>
            </div>

          </div>
        )}
      </div>
    </div>
  )
}

export default ResumeModal
