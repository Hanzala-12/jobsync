import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import MatchPanel from '../components/MatchPanel'
import { applicationsAPI, jobsAPI } from '../api/client'
import './Jobs.css'

const LOCATION_OPTIONS = ['Pakistan', 'Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'UAE', 'UK', 'Remote']
const PAK_CITIES = ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad']

const countryMap = {
  Pakistan: 'pk',
  Karachi: 'pk',
  Lahore: 'pk',
  Islamabad: 'pk',
  Rawalpindi: 'pk',
  Faisalabad: 'pk',
  UAE: 'ae',
  UK: 'gb',
  Remote: 'pk',
}

function Jobs() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('software engineer')
  const [location, setLocation] = useState('Pakistan')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [pakistanOnly, setPakistanOnly] = useState(false)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [page, setPage] = useState(2)
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelJob, setPanelJob] = useState(null)
  const [matchData, setMatchData] = useState(null)
  const [toast, setToast] = useState('')
  const [salaryCard, setSalaryCard] = useState(null)
  const [salaryData, setSalaryData] = useState(null)

  const localCount = useMemo(() => jobs.filter((job) => job.source === 'adzuna').length, [jobs])
  const remoteCount = useMemo(() => jobs.filter((job) => job.source !== 'adzuna').length, [jobs])
  const resultText = useMemo(() => `${jobs.length} jobs found for "${query}"`, [jobs, query])

  const isCitySearch = PAK_CITIES.includes(location)

  const search = async () => {
    setLoading(true)
    setError('')
    setJobs([])
    setSalaryCard(null)
    setSalaryData(null)
    try {
      const selectedRemote = remoteOnly || location === 'Remote'
      const response = await jobsAPI.search({
        query,
        location,
        city: location === 'Pakistan' || location === 'UAE' || location === 'UK' || location === 'Remote' ? '' : location,
        remote_only: selectedRemote,
        pakistan_only: pakistanOnly,
        country_code: countryMap[location] || 'pk',
      })
      setJobs(response.data || [])
    } catch {
      setError('Could not fetch jobs. Please try again.')
      setJobs([])
    } finally {
      setLoading(false)
    }
  }

  const saveToTracker = async (job) => {
    const created = await applicationsAPI.create({
      company: job.company,
      role: job.title,
      source: job.source,
      status: 'Saved',
      notes: `Saved from Jobs page for ${job.location}`,
    })

    setToast('Saved! Did you apply?')
    const yes = window.confirm('Saved! Did you apply? Click OK for Yes, Cancel for No.')
    if (yes) {
      await applicationsAPI.updateStatus(created.data.id, 'Applied')
      setToast('Moved to Applied.')
    }
  }

  const openMatch = async (job) => {
    setPanelOpen(true)
    setPanelJob(job)
    setMatchData(null)

    const resumeText = localStorage.getItem('jobsync_resume_text') || ''
    try {
      const response = await jobsAPI.explainMatch({
        job_description: job.description,
        resume_text: resumeText,
      })
      setMatchData(response.data)
    } catch {
      setMatchData(null)
    }
  }

  const openSalary = async (job, index) => {
    if (salaryCard === index) {
      setSalaryCard(null)
      setSalaryData(null)
      return
    }

    setSalaryCard(index)
    setSalaryData(null)
    try {
      const response = await jobsAPI.salaryEstimate({
        title: job.title,
        location: job.location || location,
        experience_level: 'mid',
        skills: [],
      })
      setSalaryData(response.data)
    } catch {
      setSalaryData({
        local_min: 120000,
        local_max: 220000,
        remote_min: 1500,
        remote_max: 3500,
        market_demand: 'medium',
        negotiation_tip: 'Use quantified impact in negotiation.',
      })
    }
  }

  const sourceBadge = (source) => {
    if (source === 'adzuna') return 'adzuna'
    if (source === 'jobicy') return 'jobicy'
    if (source === 'remotive') return 'remote'
    return String(source || 'remote')
  }

  return (
    <div className="jobs-page">
      <div className="page-header">
        <h1>Jobs</h1>
        <p className="subtitle">Search and save jobs with location-first filters.</p>
      </div>

      <div className="search-card">
        <div className="search-row">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search software engineer, data analyst, frontend..."
          />
          <Button onClick={search} loading={loading}>Search</Button>
        </div>

        <div className="location-row-wrap">
          <p className="section-label">Location</p>
          <div className="locations">
            {LOCATION_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                className={location === option ? 'loc-btn active' : 'loc-btn'}
                onClick={() => setLocation(option)}
              >
                {option}
              </button>
            ))}
          </div>
          <div className="toggle-group">
            <label className="remote-toggle">
              <input
                type="checkbox"
                checked={pakistanOnly}
                onChange={(event) => {
                  const next = event.target.checked
                  setPakistanOnly(next)
                  if (next) setRemoteOnly(false)
                }}
              />
              Pakistan only
            </label>
            <label className="remote-toggle">
              <input
                type="checkbox"
                checked={remoteOnly}
                onChange={(event) => {
                  const next = event.target.checked
                  setRemoteOnly(next)
                  if (next) setPakistanOnly(false)
                }}
              />
              Remote only
            </label>
          </div>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {toast && <p className="toast-text">{toast}</p>}
      <p className="muted-text">{resultText}</p>

      {remoteCount > 0 && !remoteOnly && location !== 'Remote' && (
        <p className="notice-text">Showing {localCount} local jobs and {remoteCount} remote jobs for {location}</p>
      )}

      {isCitySearch && localCount < 5 && remoteCount > 0 && !pakistanOnly && (
        <p className="limited-text">Limited local jobs found for {location}. Showing remote jobs that accept Pakistan candidates.</p>
      )}

      <div className="jobs-grid">
        {jobs.map((job, index) => (
          <article key={`${job.id || index}-${job.title}`} className="job-card">
            <div className="card-top-meta">
              <span className="company-meta">{job.company}</span>
              <span className="source-pill">{sourceBadge(job.source)}</span>
            </div>
            <h3>{job.title}</h3>
            <p className="job-location">{job.location || 'Remote'}</p>
            <p className="job-description">{job.description || 'No description available.'}</p>
            <div className="divider" />
            <div className="job-actions">
              <a href={job.url} target="_blank" rel="noreferrer">View Job {'->'}</a>
              <button type="button" onClick={() => openMatch(job)}>Match Me</button>
              <button type="button" className="salary-link" onClick={() => openSalary(job, index)}>Est. Salary</button>
              <Button size="small" variant="secondary" onClick={() => saveToTracker(job)}>Save</Button>
            </div>

            {salaryCard === index && salaryData && (
              <div className="salary-popover">
                <p>PKR {salaryData.local_min}-{salaryData.local_max}/month · ${salaryData.remote_min}-${salaryData.remote_max} remote</p>
                <p>Demand: <strong className="demand-badge">{salaryData.market_demand}</strong></p>
                <p>{salaryData.negotiation_tip}</p>
                <small>AI estimate</small>
              </div>
            )}
          </article>
        ))}
      </div>

      <div className="pagination">{'<- Previous  Page '}{page}{' of 8  Next ->'}</div>

      <MatchPanel
        open={panelOpen}
        job={panelJob}
        matchData={matchData}
        onClose={() => setPanelOpen(false)}
        onRewrite={(jobDescription) => {
          setPanelOpen(false)
          navigate('/resume', { state: { tab: 'rewrite', jobDescription } })
        }}
      />
    </div>
  )
}

export default Jobs
