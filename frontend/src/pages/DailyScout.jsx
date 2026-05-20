import { useEffect, useRef, useState } from 'react'
import Button from '../components/Button'
import { applicationsAPI, dailyScoutAPI } from '../api/client'
import './DailyScout.css'

const LOCATION_OPTIONS = ['Pakistan', 'Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'UAE', 'UK', 'Remote']

const resolveExternalJobUrl = (job) => {
  const raw = String(job?.url || job?.apply_url || '').trim()
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
    if (score >= 80) return 'score good'
    if (score >= 60) return 'score warning'
    return 'score bad'
  }

  const saveJob = async (job) => {
    const created = await applicationsAPI.create({
      company: job.company,
      role: job.title,
      status: 'Saved',
      source: 'Daily Scout',
      notes: `Match score: ${Math.round(job.match_score || 0)}`,
    })

    setNotice('Saved! Did you apply?')
    const yes = window.confirm('Saved! Did you apply? Click OK for Yes, Cancel for No.')
    if (yes) {
      await applicationsAPI.updateStatus(created.data.id, 'Applied')
      setNotice('Moved to Applied.')
    }
  }

  return (
    <div className="scout-page">
      <div className="page-header">
        <h1>Daily Scout</h1>
        <p className="subtitle">Run automated searches and save high-match jobs.</p>
      </div>

      <section className="preferences-card">
        <div className="inputs-row">
          <input value={role} onChange={(event) => setRole(event.target.value)} placeholder="Job Title" />
          <select value={location} onChange={(event) => setLocation(event.target.value)}>
            {LOCATION_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <input value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="Skills" />
        </div>
        <div className="run-row">
          <Button onClick={runScout} loading={running}>Run Scout Now</Button>
          <p className="status">{statusText}</p>
        </div>
      </section>

      {notice && <p className="notice">{notice}</p>}

      <div className="jobs-grid">
        {jobs.map((job, index) => (
          <article className="job-card" key={`${job.id || index}-${job.title}`}>
            <div className="job-top">
              <p>{job.company}</p>
              <span className={scoreClass(Math.round(job.match_score || 0))}>{Math.round(job.match_score || 0)}%</span>
            </div>
            <h3>{job.title}</h3>
            <p className="location">{job.location}</p>
            <p className="desc">{job.description}</p>
            <div className="job-actions">
              {resolveExternalJobUrl(job) ? (
                <a href={resolveExternalJobUrl(job)} target="_blank" rel="noreferrer">View Job {'->'}</a>
              ) : (
                <button type="button" disabled title="No external job link provided">View Job {'->'}</button>
              )}
              <Button size="small" variant="secondary" onClick={() => saveJob(job)}>Save to Tracker</Button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}

export default DailyScout
