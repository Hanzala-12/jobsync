import { useEffect, useRef, useState } from 'react'
import Button from '../components/Button'
import { applicationsAPI, dailyScoutAPI } from '../api/client'
import { Search, Loader2, MapPin, ExternalLink, BookmarkPlus, CheckCircle2 } from 'lucide-react'
import './DailyScout.css'

const LOCATION_OPTIONS = ['Pakistan', 'Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'UAE', 'UK', 'Remote']

const resolveExternalJobUrl = (job) => {
  const raw = String(job?.url || job?.apply_url || job?.external_id || '').trim()
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw
  return ''
}

function DailyScout() {
  const [role, setRole] = useState('software engineer')
  const [location, setLocation] = useState('Pakistan')
  const [skills, setSkills] = useState('React, Node.js')
  const [running, setRunning] = useState(false)
  const [statusText, setStatusText] = useState('Ready')
  const [jobs, setJobs] = useState([])
  const [notice, setNotice] = useState('')
  const pollRef = useRef(null)

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const pollStatus = async () => {
    const response = await dailyScoutAPI.status()
    const data = response.data || {}
    if (data.running) {
      setStatusText(`Searching... found ${data.found || 0} jobs so far`)
    } else {
      setStatusText('Ready')
      stopPolling()
    }
  }

  useEffect(() => {
    return () => stopPolling()
  }, [])

  const runScout = async () => {
    setRunning(true)
    setStatusText('Searching...')
    stopPolling()
    pollRef.current = setInterval(pollStatus, 2000)

    try {
      const response = await dailyScoutAPI.run({ role, location, skills, min_score: 60, page: 1 })
      setJobs(response.data?.discovered_jobs || [])
      setStatusText(`Done. Found ${(response.data?.discovered_jobs || []).length} jobs.`)
    } finally {
      setRunning(false)
      stopPolling()
    }
  }

  const scoreClass = (score) => {
    if (score >= 80) return 'score-good'
    if (score >= 60) return 'score-warn'
    return 'score-bad'
  }

  const saveJob = async (job) => {
    const created = await applicationsAPI.create({
      company: job.company,
      role: job.title,
      status: 'Saved',
      source: 'Daily Scout',
      notes: `Match score: ${Math.round(job.match_score || 0)}`,
    })

    setNotice(`Saved ${job.company} to Kanban!`)
    const yes = window.confirm('Saved! Did you apply already? Click OK for Yes, Cancel to just keep it Saved.')
    if (yes) {
      await applicationsAPI.updateStatus(created.data.id, 'Applied')
      setNotice(`Moved ${job.company} to Applied in Kanban.`)
    }
    
    setTimeout(() => setNotice(''), 4000)
  }

  return (
    <div className="scout-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section className="app-card" style={{ padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Automated Scout</p>
          <h1 style={{ marginTop: 6 }}>Daily Scout</h1>
          <p className="subtitle">Run automated background searches and save high-match jobs directly to your Kanban.</p>
        </div>
        <div style={{ padding: '10px 14px', borderRadius: 14, background: 'var(--j-surface)', border: '1px solid var(--j-border)', color: 'var(--j-text-2)', fontWeight: 700 }}>{statusText}</div>
      </section>

      <section className="preferences-card fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)' }}>
        <div className="inputs-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 14 }}>
          <div>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Job Title</span>
            <input className="scout-input" value={role} onChange={(event) => setRole(event.target.value)} placeholder="e.g. Software Engineer" style={{ marginTop: 10, width: '100%', minHeight: 46, borderRadius: 14, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }} />
          </div>
          <div>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Location</span>
            <select className="scout-input" value={location} onChange={(event) => setLocation(event.target.value)} style={{ marginTop: 10, width: '100%', minHeight: 46, borderRadius: 14, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }}>
              {LOCATION_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <div>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Key Skills</span>
            <input className="scout-input" value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="e.g. React, Node, SQL..." style={{ marginTop: 10, width: '100%', minHeight: 46, borderRadius: 14, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-1)', padding: '0 12px' }} />
          </div>
        </div>

        <div className="run-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
          <Button onClick={runScout} loading={running}><Search size={14} style={{ display: 'inline', marginRight: 6 }}/> Run Scout Now</Button>
          <div className="run-status" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--j-text-2)' }}>
            {running && <Loader2 size={14} className="animate-spin" />}
            {statusText}
          </div>
        </div>
      </section>

      {notice && (
        <div className="fade-up">
          <p className="scout-notice" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 14px', borderRadius: 14, background: 'rgba(16,185,129,0.10)', color: '#047857', fontWeight: 700 }}><CheckCircle2 size={16} color="var(--j-green)" /> {notice}</p>
        </div>
      )}

      {jobs.length > 0 && (
        <div className="jobs-grid fade-up" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
          {jobs.map((job, index) => (
            <article className="job-card" key={`${job.id || index}-${job.title}`} style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 20, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="job-top" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                <span className="job-company" style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--j-text-2)' }}>{job.company}</span>
                <span className={`job-score ${scoreClass(Math.round(job.match_score || 0))}`} style={{ padding: '6px 10px', borderRadius: 999, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, fontSize: 12 }}>{Math.round(job.match_score || 0)}% MATCH</span>
              </div>
              <h3 className="job-title" style={{ margin: 0, fontSize: 18, fontWeight: 800, color: 'var(--j-text-1)' }}>{job.title}</h3>
              <div className="job-loc" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--j-text-2)' }}>
                <MapPin size={14} /> {job.location}
              </div>
              <p className="job-desc" style={{ margin: 0, color: 'var(--j-text-2)', lineHeight: 1.7 }}>{job.description}</p>

              <div className="job-actions" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', marginTop: 'auto' }}>
                <Button size="small" variant="secondary" onClick={() => saveJob(job)}>
                  <BookmarkPlus size={14} style={{ display: 'inline', marginRight: 4 }}/> Save
                </Button>

                {resolveExternalJobUrl(job) ? (
                  <a className="link-btn" href={resolveExternalJobUrl(job)} target="_blank" rel="noreferrer" style={{ minHeight: 38, padding: '0 12px', borderRadius: 12, border: '1px solid rgba(58,87,232,0.18)', background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 6 }}>Apply <ExternalLink size={12} /></a>
                ) : (
                  <button className="link-btn" type="button" disabled title="No external job link provided" style={{ minHeight: 38, padding: '0 12px', borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-3)', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 6 }}>No Link <ExternalLink size={12} /></button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

export default DailyScout
