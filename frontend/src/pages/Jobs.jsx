import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import MatchPanel from '../components/MatchPanel'
import { applicationsAPI, jobsAPI, profileAPI, apiActions } from '../api/client'
import searchStream from '../services/searchStream'
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

const resolveExternalJobUrl = (job) => {
  const raw = String(job?.url || job?.apply_url || job?.external_id || '').trim()
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw
  return ''
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
  const [streamingCount, setStreamingCount] = useState(0)
  const [streamElapsed, setStreamElapsed] = useState(0)
  const [page, setPage] = useState(1)
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelJob, setPanelJob] = useState(null)
  const [matchData, setMatchData] = useState(null)
  const [matchModalOpen, setMatchModalOpen] = useState(false)
  const [matchModalLoading, setMatchModalLoading] = useState(false)
  const [matchModalResult, setMatchModalResult] = useState(null)
  const [toast, setToast] = useState('')
  const [profileExists, setProfileExists] = useState(false)
  const [salaryCard, setSalaryCard] = useState(null)
  const [salaryData, setSalaryData] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const localCount = useMemo(() => jobs.filter((job) => job.source === 'adzuna').length, [jobs])
  const remoteCount = useMemo(() => jobs.filter((job) => job.source !== 'adzuna').length, [jobs])
  const resultText = useMemo(() => `${jobs.length} jobs found for "${query}"`, [jobs, query])

  const isCitySearch = PAK_CITIES.includes(location)

  const handleQueryChange = async (value) => {
    setQuery(value)
    if (value.length > 0) {
      try {
        const response = await jobsAPI.autocomplete(value)
        setSuggestions(response.data?.suggestions || [])
        setShowSuggestions(true)
      } catch {
        setSuggestions([])
      }
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  const selectSuggestion = (suggestion) => {
    setQuery(suggestion)
    setSuggestions([])
    setShowSuggestions(false)
  }

  const search = async () => {
    setLoading(true)
    setError('')
    setJobs([])
    setSalaryCard(null)
    setSalaryData(null)
    setStreamingCount(0)
    setStreamElapsed(0)
    const selectedRemote = remoteOnly || location === 'Remote'
    const API_BASE = import.meta.env.VITE_API_URL || '/api'
    const cityParam = location === 'Pakistan' || location === 'UAE' || location === 'UK' || location === 'Remote' ? '' : location
    const url = `${API_BASE}/jobs/search/stream?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&city=${encodeURIComponent(cityParam)}&remote_only=${selectedRemote}&pakistan_only=${pakistanOnly}&country_code=${countryMap[location] || 'pk'}`

    try {
      // Start or reuse shared background stream so it continues across navigation
      searchStream.start(url)
      setLoading(true)
    } catch (e) {
      console.error('Search error:', e)
      setError('Could not fetch jobs. Please try again.')
      setJobs([])
      setLoading(false)
    }
  }

  // Subscribe to shared search stream updates. Unsubscribe on unmount but keep stream running.
  useEffect(() => {
    const unsub = searchStream.subscribe((s) => {
      setJobs(s.jobs || [])
      setStreamingCount(s.streamingCount || 0)
      setStreamElapsed(s.streamElapsed || 0)
      setLoading(Boolean(s.loading))
    })
    return () => { unsub() }
  }, [])

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
    if (!profileExists) {
      alert('Please complete your profile first')
      return
    }

    setMatchModalOpen(true)
    setMatchModalLoading(true)
    setMatchModalResult(null)
    try {
      let jobId = job.id
      // If the job isn't stored locally yet, upsert it first so we have an id to match against
      if (!jobId) {
        try {
          const up = await jobsAPI.upsert(job)
          jobId = up.data?.id || up.data?.job_id || null
          // update local job object so buttons/UX reflect stored state
          if (jobId) job.id = jobId
        } catch (upErr) {
          console.error('Upsert failed', upErr)
        }
      }

      if (!jobId) {
        // couldn't create job on server
        setMatchModalResult({ match_percentage: null, explanation: 'Failed to create job record on server', missing_skills: null, error: true })
        return
      }

      const res = await jobsAPI.match(jobId)
      setMatchModalResult(res.data)
    } catch (e) {
      // Mark as an error result so the UI can show a proper message
      setMatchModalResult({ match_percentage: null, explanation: 'Failed to fetch match', missing_skills: null, error: true })
    } finally {
      setMatchModalLoading(false)
    }
  }

  const handleBuildResume = (job) => {
    navigate('/resume', { state: { tab: 'rewrite', jobDescription: job.description } })
  }

  const handleCoverLetter = (job) => {
    navigate('/cover-letter', { state: { job } })
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

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const res = await profileAPI.list(1, 10)
        // API returns { exists, profiles, selected_profile_id, ... }
        if (mounted) setProfileExists(Boolean(res.data?.exists || (res.data?.selected_profile_id !== null)))
      } catch (e) {
        if (mounted) setProfileExists(false)
      }
    })()
    return () => { mounted = false }
  }, [])

  return (
    <div className="jobs-page">
      <div className="page-header">
        <h1>Jobs</h1>
        <p className="subtitle">Search and save jobs with location-first filters.</p>
      </div>

      <div className="search-card">
        <div className="search-row">
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              value={query}
              onChange={(event) => handleQueryChange(event.target.value)}
              onFocus={() => query.length > 0 && setShowSuggestions(true)}
              placeholder="Search software engineer, data analyst, frontend..."
            />
            {showSuggestions && suggestions.length > 0 && (
              <div className="autocomplete-dropdown">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="autocomplete-item"
                    onClick={() => selectSuggestion(suggestion)}
                  >
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>
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
      {!profileExists && (
        <p className="warning-text">⚠️ Please complete your profile first — Match, Build Resume and Cover Letter are disabled.</p>
      )}
      {toast && <p className="toast-text">{toast}</p>}
      <p className="muted-text">{resultText}</p>
      {loading && (
        <div>
          <p className="muted-text">
            <span className="spinner" aria-hidden="true" />
            {' '}
            Streaming results: {streamingCount} so far · {streamElapsed}s elapsed
          </p>
          <div className="progress-wrap" aria-hidden>
            {/* If we have a combined_count we show a heuristic determinate width, otherwise indeterminate */}
            {streamingCount > 0 ? (
              <div className="progress-bar" style={{ width: Math.min(100, streamingCount * 6) + '%' }} />
            ) : (
              <div className="progress-bar progress-indeterminate" style={{ width: '40%' }} />
            )}
          </div>
        </div>
      )}

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
              {resolveExternalJobUrl(job) ? (
                <a href={resolveExternalJobUrl(job)} target="_blank" rel="noreferrer">View Job {'->'}</a>
              ) : (
                <button type="button" disabled title="No external job link provided">View Job {'->'}</button>
              )}
              <button
                type="button"
                onClick={() => openMatch(job)}
                disabled={!profileExists}
                title={!profileExists ? 'Complete your profile' : ''}
              >
                Match Me
              </button>
              <button type="button" onClick={() => handleBuildResume(job)} disabled={!profileExists} title={!profileExists ? 'Complete your profile' : ''}>Build Resume</button>
              <button type="button" onClick={() => handleCoverLetter(job)} disabled={!profileExists} title={!profileExists ? 'Complete your profile' : ''}>Cover Letter</button>
              <button type="button" className="salary-link" onClick={() => openSalary(job, index)}>Est. Salary</button>
              <Button size="small" variant="secondary" onClick={() => saveToTracker(job)}>Save</Button>
            </div>

            {salaryCard === index && salaryData && (
              <div className="salary-popover">
                <p>PKR {salaryData.local_min}-{salaryData.local_max}/month · ${salaryData.remote_min}-{salaryData.remote_max} remote</p>
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

      {matchModalOpen && (
        <div className="match-modal-overlay" onClick={() => setMatchModalOpen(false)}>
          <div className="match-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            {matchModalLoading ? (
              <div className="match-loading-container">
                <div className="spinner" style={{ width: 40, height: 40, borderWidth: 4 }} />
                <p>Analyzing job fit with AI...</p>
              </div>
            ) : (
              <div className="match-modal-body">
                <h3>Match Score: {matchModalResult && matchModalResult.match_percentage !== null ? Math.round(matchModalResult.match_percentage) + '%' : 'N/A'}</h3>
                <div className="match-progress">
                  <div
                    className="match-progress-bar"
                    style={{ width: `${matchModalResult && matchModalResult.match_percentage !== null ? Math.min(100, matchModalResult.match_percentage) : 0}%` }}
                  />
                </div>

                {matchModalResult && matchModalResult.error ? (
                  <div className="match-error">
                    <p><strong>Analysis unavailable:</strong> {matchModalResult.explanation}</p>
                    <p>Please try again later.</p>
                  </div>
                ) : (
                  <>
                    <h4>Missing Skills</h4>
                    <div className="missing-skills-container">
                      {matchModalResult && Array.isArray(matchModalResult.missing_skills) ? (
                        matchModalResult.missing_skills.length > 0 ? (
                          matchModalResult.missing_skills.map((s, i) => (
                            <span key={i} className="missing-skill-chip">{s}</span>
                          ))
                        ) : (
                          // Only show "Perfect Match" when the score is effectively 100%
                          (matchModalResult.match_percentage !== null && matchModalResult.match_percentage >= 99) ? (
                            <span className="missing-skill-chip" style={{ background: '#f0fdf4', color: '#16a34a', borderColor: '#dcfce7' }}>None (Perfect Match!)</span>
                          ) : (
                            // For empty arrays that are not true perfect matches, show a clearer message
                            <span className="missing-skill-chip" style={{ background: '#fff7ed', color: '#92400e', borderColor: '#ffedd5' }}>No detailed analysis available</span>
                          )
                        )
                      ) : (
                        <span className="missing-skill-chip" style={{ background: '#fff7ed', color: '#92400e', borderColor: '#ffedd5' }}>No analysis available</span>
                      )}
                    </div>

                    <h4>Analysis Explanation</h4>
                    <p className="match-explanation">
                      {matchModalResult && matchModalResult.explanation ? matchModalResult.explanation : 'No explanation available.'}
                    </p>
                  </>
                )}

                <div className="match-modal-actions">
                  <button className="match-modal-close-btn" onClick={() => setMatchModalOpen(false)}>Close</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Jobs
