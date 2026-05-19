import { useEffect, useRef, useState } from 'react'
import Card from '../components/Card'
import Button from '../components/Button'
import { applicationsAPI, dailyScoutAPI, resumeAPI } from '../api/client'
import './DailyScout.css'

function DailyScout() {
  const [query, setQuery] = useState('software engineer')
  const [location, setLocation] = useState('remote')
  const [minScore, setMinScore] = useState(75)
  const [filterLocation, setFilterLocation] = useState('')
  const [filterScore, setFilterScore] = useState(70)
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [jobs, setJobs] = useState([])
  const [status, setStatus] = useState({ running: false, progress: 0, message: 'Idle' })
  const [notice, setNotice] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [savingJobKey, setSavingJobKey] = useState(null)
  const pollRef = useRef(null)

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const refreshStatus = async () => {
    try {
      const response = await dailyScoutAPI.status()
      setStatus(response.data)

      if (!response.data.running) {
        stopPolling()
      }
    } catch (error) {
      console.error('Failed to refresh scout status:', error)
    }
  }

  useEffect(() => {
    refreshStatus()

    return () => {
      stopPolling()
    }
  }, [])

  const runScout = async () => {
    setLoading(true)
    setNotice('')
    setAnalysis(null)
    setResult(null)
    setJobs([])
    setStatus((current) => ({
      ...current,
      running: true,
      progress: 0,
      message: 'Starting scout',
    }))

    stopPolling()
    pollRef.current = setInterval(refreshStatus, 2000)

    try {
      const response = await dailyScoutAPI.run({
        query,
        location,
        min_score: Number(minScore),
      })

      setResult(response.data)
      setJobs(response.data.discovered_jobs || [])
      setFilterLocation(location)
      setFilterScore(Number(minScore))
      setStatus((current) => ({
        ...current,
        running: false,
        progress: 100,
        message: response.data.success ? 'Scout complete' : 'Scout finished with warnings',
      }))
    } catch (error) {
      console.error('Error running scout:', error)
      setResult({ error: 'Failed to run scout. Check console for details.' })
      setStatus((current) => ({
        ...current,
        running: false,
        progress: 100,
        message: 'Scout failed',
      }))
    } finally {
      setLoading(false)
      await refreshStatus()
    }
  }

  const saveToTracker = async (job) => {
    const jobKey = job.id || `${job.title}-${job.company}`
    setSavingJobKey(jobKey)
    setNotice('')

    try {
      await applicationsAPI.create({
        company: job.company,
        role: job.title,
        notes: `Saved from Daily Scout. Match score: ${job.match_score}%`,
        status: 'Saved',
        source: 'Daily Scout',
      })
      setNotice(`Saved ${job.title} at ${job.company} to the tracker.`)
    } catch (error) {
      console.error('Failed to save job:', error)
      setNotice('Could not save this job right now.')
    } finally {
      setSavingJobKey(null)
    }
  }

  const analyzeResume = async (job) => {
    if (!job.description) {
      setAnalysis({
        error: 'This job listing does not include a description to analyze.',
      })
      return
    }

    try {
      setAnalysis({ loading: true, job })
      const response = await resumeAPI.reanalyze(job.description)
      setAnalysis({
        job,
        loading: false,
        data: response.data,
      })
    } catch (error) {
      console.error('Failed to analyze resume:', error)
      setAnalysis({
        job,
        error: 'Resume analysis failed for this job.',
      })
    }
  }

  const filteredJobs = jobs.filter((job) => {
    const score = Number(job.match_score || 0)
    const locationText = (job.location || '').toLowerCase()
    const companyText = (job.company || '').toLowerCase()
    const titleText = (job.title || '').toLowerCase()
    const requestedLocation = filterLocation.trim().toLowerCase()
    const isRemote = locationText.includes('remote')

    if (score < Number(filterScore)) {
      return false
    }

    if (remoteOnly && !isRemote) {
      return false
    }

    if (requestedLocation && !locationText.includes(requestedLocation) && !companyText.includes(requestedLocation) && !titleText.includes(requestedLocation)) {
      return false
    }

    return true
  })

  const runningProgress = typeof status.progress === 'number' ? status.progress : 0

  return (
    <div className="daily-scout-page">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Daily Scout</p>
          <h1>Automated job discovery with live progress and one-click actions.</h1>
          <p className="hero-copy">
            Search new roles, score them against your resume, and push the best matches straight into the tracker.
          </p>
        </div>

        <div className="status-panel">
          <div className="status-header">
            <div>
              <span className={`status-pill ${status.running ? 'active' : 'idle'}`}>
                {status.running ? 'Running' : 'Ready'}
              </span>
              <p>{status.message || 'Idle'}</p>
            </div>
            <strong>{runningProgress}%</strong>
          </div>

          <div className="progress-bar">
            <span style={{ width: `${runningProgress}%` }} />
          </div>

          <div className="status-meta">
            <span>Location: {location}</span>
            <span>Minimum score: {minScore}%</span>
            <span>Matched jobs: {jobs.length}</span>
          </div>
        </div>
      </section>

      <section className="control-grid">
        <Card className="control-card">
          <h2>Scout Settings</h2>
          <p className="description">
            Tune the search before you launch the scout. The result cards below can be filtered independently.
          </p>

          <div className="form-grid">
            <div className="form-group">
              <label>Job Query</label>
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="software engineer, data analyst, product manager"
              />
            </div>

            <div className="form-group">
              <label>Search Location</label>
              <input
                type="text"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="remote, Austin, London"
              />
            </div>
          </div>

          <div className="form-group slider-group">
            <label>Minimum Match Score: {minScore}%</label>
            <input
              type="range"
              min="50"
              max="100"
              value={minScore}
              onChange={(event) => setMinScore(event.target.value)}
            />
            <div className="slider-labels">
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          <div className="button-row">
            <Button onClick={runScout} disabled={loading}>
              {loading ? 'Searching...' : 'Run Scout Now'}
            </Button>
          </div>
        </Card>

        <Card className="control-card filter-card">
          <h2>Result Filters</h2>
          <p className="description">Refine the discovered jobs before saving or analyzing them.</p>

          <div className="form-group">
            <label>Location Filter</label>
            <input
              type="text"
              value={filterLocation}
              onChange={(event) => setFilterLocation(event.target.value)}
              placeholder="Filter by city, state, or remote"
            />
          </div>

          <div className="form-group slider-group">
            <label>Displayed Score Threshold: {filterScore}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={filterScore}
              onChange={(event) => setFilterScore(event.target.value)}
            />
            <div className="slider-labels">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          <label className="toggle-row">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(event) => setRemoteOnly(event.target.checked)}
            />
            <span>Remote only</span>
          </label>
        </Card>
      </section>

      {notice && (
        <Card className="notice-card">
          <p>{notice}</p>
        </Card>
      )}

      {result && result.error && (
        <Card className="error-card">
          <h3>Scout Error</h3>
          <p>{result.error}</p>
        </Card>
      )}

      {result && !result.error && (
        <section className="summary-grid">
          <Card className="summary-card summary-highlight">
            <span className="summary-label">Jobs Found</span>
            <strong>{result.found}</strong>
          </Card>
          <Card className="summary-card">
            <span className="summary-label">Saved</span>
            <strong>{result.saved}</strong>
          </Card>
          <Card className="summary-card">
            <span className="summary-label">Duplicates Skipped</span>
            <strong>{result.duplicates_skipped}</strong>
          </Card>
        </section>
      )}

      {!!filteredJobs.length && (
        <section className="jobs-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Discovered Jobs</p>
              <h2>{filteredJobs.length} matches ready for action</h2>
            </div>
            <p className="section-copy">Save the ones you want to track, or analyze a posting against your resume immediately.</p>
          </div>

          <div className="jobs-grid">
            {filteredJobs.map((job) => {
              const jobKey = job.id || `${job.title}-${job.company}`
              return (
                <Card key={jobKey} className="job-card">
                  <div className="job-card-top">
                    <div>
                      <p className="job-company">{job.company}</p>
                      <h3>{job.title}</h3>
                    </div>
                    <span className="score-badge">{Math.round(job.match_score || 0)}%</span>
                  </div>

                  <p className="job-location">{job.location || 'Location not listed'}</p>
                  <p className="job-description">
                    {job.description || 'No description available from the job feed.'}
                  </p>

                  <div className="job-actions">
                    <Button
                      onClick={() => saveToTracker(job)}
                      disabled={savingJobKey === jobKey}
                    >
                      {savingJobKey === jobKey ? 'Saving...' : 'Save to Tracker'}
                    </Button>

                    <Button variant="secondary" onClick={() => analyzeResume(job)}>
                      Analyze Resume
                    </Button>

                    {job.url && (
                      <a className="job-link" href={job.url} target="_blank" rel="noreferrer">
                        Open posting
                      </a>
                    )}
                  </div>
                </Card>
              )
            })}
          </div>
        </section>
      )}

      {analysis && (
        <Card className="analysis-card">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Resume Analysis</p>
              <h2>{analysis.job?.title}</h2>
            </div>
          </div>

          {analysis.loading && <p>Analyzing your resume against this role...</p>}

          {analysis.error && <p className="analysis-error">{analysis.error}</p>}

          {analysis.data && (
            <div className="analysis-results">
              <div className="analysis-score">
                <span>ATS Score</span>
                <strong>{analysis.data.ats_score}%</strong>
              </div>

              <div className="analysis-columns">
                <div>
                  <h3>Matched Skills</h3>
                  <div className="chip-list">
                    {(analysis.data.matched_skills || []).slice(0, 8).map((skill) => (
                      <span key={skill} className="chip chip-positive">{skill}</span>
                    ))}
                  </div>
                </div>

                <div>
                  <h3>Missing Keywords</h3>
                  <div className="chip-list">
                    {(analysis.data.missing_keywords || []).slice(0, 8).map((keyword) => (
                      <span key={keyword} className="chip chip-muted">{keyword}</span>
                    ))}
                  </div>
                </div>
              </div>

              {analysis.data.tips && analysis.data.tips.length > 0 && (
                <div>
                  <h3>Suggestions</h3>
                  <ul className="tips-list">
                    {analysis.data.tips.slice(0, 4).map((tip, index) => (
                      <li key={`${tip}-${index}`}>{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      <Card className="info-card">
        <h3>How It Works</h3>
        <ol>
          <li>Search pulls live jobs from the JSearch API.</li>
          <li>The engine scores each role against your uploaded resume.</li>
          <li>Progress updates are polled while the scout runs.</li>
          <li>Save any promising job directly into the tracker as Saved.</li>
          <li>Analyze a job posting instantly to compare it with your resume.</li>
        </ol>
      </Card>
    </div>
  )
}

export default DailyScout
