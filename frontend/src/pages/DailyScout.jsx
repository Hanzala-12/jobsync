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
    <div className="scout-page fade-up">
      <div className="page-header">
        <h1>Daily Scout</h1>
        <p className="subtitle">Run automated background searches and save high-match jobs directly to your Kanban.</p>
      </div>

      <section className="preferences-card fade-up">
        <div className="inputs-row">
          <div>
            <span className="field-label">JOB TITLE</span>
            <input className="scout-input" value={role} onChange={(event) => setRole(event.target.value)} placeholder="e.g. Software Engineer" />
          </div>
          <div>
            <span className="field-label">LOCATION</span>
            <select className="scout-input" value={location} onChange={(event) => setLocation(event.target.value)}>
              {LOCATION_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <div>
            <span className="field-label">KEY SKILLS</span>
            <input className="scout-input" value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="e.g. React, Node, SQL..." />
          </div>
        </div>
        
        <div className="run-row">
          <Button onClick={runScout} loading={running}><Search size={14} style={{ display: 'inline', marginRight: 6 }}/> Run Scout Now</Button>
          <div className="run-status">
            {running && <Loader2 size={14} className="animate-spin" />}
            {statusText}
          </div>
        </div>
      </section>

      {notice && (
        <div className="fade-up">
          <p className="scout-notice"><CheckCircle2 size={16} color="var(--j-green)" /> {notice}</p>
        </div>
      )}

      {jobs.length > 0 && (
        <div className="jobs-grid fade-up">
          {jobs.map((job, index) => (
            <article className="job-card" key={`${job.id || index}-${job.title}`}>
              <div className="job-top">
                <span className="job-company">{job.company}</span>
                <span className={`job-score ${scoreClass(Math.round(job.match_score || 0))}`}>{Math.round(job.match_score || 0)}% MATCH</span>
              </div>
              <h3 className="job-title">{job.title}</h3>
              <div className="job-loc">
                <MapPin size={14} /> {job.location}
              </div>
              <p className="job-desc">{job.description}</p>
              
              <div className="job-actions">
                <Button size="small" variant="secondary" onClick={() => saveJob(job)}>
                  <BookmarkPlus size={14} style={{ display: 'inline', marginRight: 4 }}/> Save
                </Button>
                
                {resolveExternalJobUrl(job) ? (
                  <a className="link-btn" href={resolveExternalJobUrl(job)} target="_blank" rel="noreferrer">Apply <ExternalLink size={12} /></a>
                ) : (
                  <button className="link-btn" type="button" disabled title="No external job link provided">No Link <ExternalLink size={12} /></button>
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
