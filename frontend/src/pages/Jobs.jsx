import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { applicationsAPI, jobsAPI, profileAPI, API_BASE_URL, getStoredAuthToken } from '../api/client'
import searchStream from '../services/searchStream'
import { Search, MapPin, ExternalLink, Activity, FileText, CheckCircle2 } from 'lucide-react'
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
  if (/^\/\//.test(raw)) return `${window.location.protocol}${raw}`
  if (raw.includes('.') && !raw.includes(':')) return `https://${raw}`
  return ''
}

const normalizeSkillList = (values) => {
  if (!values) return []
  const items = Array.isArray(values) ? values : [values]
  return items
    .flatMap((item) => String(item || '').split(/[\n,;|•]+/g))
    .map((item) => item.trim())
    .filter((item, index, array) => item.length > 1 && array.findIndex((value) => value.toLowerCase() === item.toLowerCase()) === index)
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
    const isLocalBackend = API_BASE_URL === 'http://localhost:8000' || API_BASE_URL === 'http://127.0.0.1:8000'
    const API_BASE = import.meta.env.DEV && isLocalBackend ? '/api' : (API_BASE_URL || '/api').replace(/\/$/, '')
    const cityParam = location === 'Pakistan' || location === 'UAE' || location === 'UK' || location === 'Remote' ? '' : location
    const token = getStoredAuthToken()
    const url = `${API_BASE}/jobs/search/stream?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&city=${encodeURIComponent(cityParam)}&remote_only=${selectedRemote}&pakistan_only=${pakistanOnly}&country_code=${countryMap[location] || 'pk'}${token ? `&token=${encodeURIComponent(token)}` : ''}`

    try {
      searchStream.start(url)
      setLoading(true)
    } catch (e) {
      console.error('Search error:', e)
      setError('Could not fetch jobs. Please try again.')
      setJobs([])
      setLoading(false)
    }
  }

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
      if (!jobId) {
        try {
          const up = await jobsAPI.upsert(job)
          jobId = up.data?.id || up.data?.job_id || null
          if (jobId) job.id = jobId
        } catch (upErr) {
          console.error('Upsert failed', upErr)
        }
      }

      if (!jobId) {
        setMatchModalResult({ match_percentage: null, explanation: 'Failed to create job record on server', missing_skills: null, error: true })
        return
      }

      const res = await jobsAPI.match(jobId)
      setMatchModalResult(res.data)
    } catch (e) {
      setMatchModalResult({ match_percentage: null, explanation: 'Failed to fetch match', missing_skills: null, error: true })
    } finally {
      setMatchModalLoading(false)
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

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const res = await profileAPI.list(1, 10)
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

      <div className="search-box">
        <div className="search-bar">
          <Search className="search-icon" size={18} />
          <input
            value={query}
            onChange={(event) => handleQueryChange(event.target.value)}
            onFocus={() => query.length > 0 && setShowSuggestions(true)}
            placeholder="Search software engineer, data analyst, frontend..."
          />
          <Button onClick={search} loading={loading}>Search</Button>
          
          {showSuggestions && suggestions.length > 0 && (
            <div className="autocomplete-dropdown">
              {suggestions.map((suggestion, index) => (
                <div key={index} className="autocomplete-item" onClick={() => selectSuggestion(suggestion)}>
                  {suggestion}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="filters-row">
          <div className="location-pills">
            {LOCATION_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                className={`location-pill ${location === option ? 'active' : ''}`}
                onClick={() => setLocation(option)}
              >
                {option}
              </button>
            ))}
          </div>
          <div className="checkbox-filters">
            <label>
              <input type="checkbox" checked={pakistanOnly} onChange={(e) => { setPakistanOnly(e.target.checked); if (e.target.checked) setRemoteOnly(false); }} />
              Pakistan only
            </label>
            <label>
              <input type="checkbox" checked={remoteOnly} onChange={(e) => { setRemoteOnly(e.target.checked); if (e.target.checked) setPakistanOnly(false); }} />
              Remote only
            </label>
          </div>
        </div>
      </div>

      {error && <p className="status-message error">{error}</p>}
      {!profileExists && <p className="status-message warning">⚠️ Please complete your profile first — Match Me and Resume will prompt you to finish it.</p>}
      {toast && <p className="status-message success">{toast}</p>}
      
      {!loading && jobs.length > 0 && <p className="results-count">{resultText}</p>}
      
      {loading && (
        <div className="search-loader">
          <div className="loader-text">Streaming results: {streamingCount} so far · {streamElapsed}s elapsed</div>
          <div className="loader-bar-wrap">
            <div className="loader-bar" style={{ width: streamingCount > 0 ? Math.min(100, streamingCount * 6) + '%' : '30%' }} />
          </div>
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="empty-state">
          <Search size={32} color="var(--j-text-3)" opacity={0.5} />
          <p className="section-label" style={{ marginBottom: 0 }}>NO JOBS FOUND</p>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--j-text-1)' }}>Try a broader search</h2>
          <p style={{ color: 'var(--j-text-2)' }}>We couldn’t find any jobs for this query yet.<br />Try a broader role title or switch to a different location.</p>
        </div>
      )}

      <div className="jobs-grid">
        {jobs.map((job, index) => (
          <article key={`${job.id || index}-${job.title}`} className="job-card fade-up">
            <div className="card-top">
              <span className="card-company">{job.company}</span>
              <span className="card-source">{sourceBadge(job.source)}</span>
            </div>
            
            <h3 className="card-title">{job.title}</h3>
            <div className="card-location"><MapPin size={12} /> {job.location || 'Remote'}</div>
            
            <div className="card-desc-wrap">
              <p className="card-desc">{job.description || 'No description available.'}</p>
            </div>
            
            <div className="card-actions">
              {resolveExternalJobUrl(job) ? (
                <a href={resolveExternalJobUrl(job)} target="_blank" rel="noreferrer" className="action-view">View <ExternalLink size={12} /></a>
              ) : (
                <span className="action-view disabled">View <ExternalLink size={12} /></span>
              )}
              
              <button
                type="button"
                onClick={() => {
                  if (!profileExists) {
                    alert('Please complete your profile first')
                    return
                  }
                  openMatch(job)
                }}
                className="action-btn"
                title={profileExists ? 'Match your profile to this job' : 'Complete your profile to use Match Me'}
              >
                Match Me
              </button>
              <button
                type="button"
                onClick={() => {
                  if (!profileExists) {
                    alert('Please complete your profile first')
                    return
                  }
                  navigate('/resume', { state: { tab: 'rewrite', jobDescription: job.description } })
                }}
                className="action-btn"
                title={profileExists ? 'Rewrite your resume for this job' : 'Complete your profile to use Resume'}
              >
                Resume
              </button>
              <button type="button" onClick={() => openSalary(job, index)} className="action-btn">$ Est.</button>
              <button type="button" onClick={() => saveToTracker(job)} className="action-save">Save</button>
            </div>

            {salaryCard === index && salaryData && (
              <div className="salary-popover fade-up">
                <p className="sal-amount">PKR {salaryData.local_min}-{salaryData.local_max}/mo · ${salaryData.remote_min}-{salaryData.remote_max} remote</p>
                <p className="sal-demand">Demand: <span className="sal-badge">{salaryData.market_demand}</span></p>
                <p className="sal-tip">{salaryData.negotiation_tip}</p>
              </div>
            )}
          </article>
        ))}
      </div>

      {matchModalOpen && (
        <div className="match-overlay" onClick={() => setMatchModalOpen(false)}>
          <div className="match-modal fade-up" onClick={(e) => e.stopPropagation()}>
            {matchModalLoading ? (
              <div className="match-loading">
                <div className="spinner" />
                <p>Analyzing job fit...</p>
              </div>
            ) : (
              <div className="match-content">
                <div className="match-score-wrap">
                  <span className="match-score-value">{matchModalResult?.match_percentage ? Math.round(matchModalResult.match_percentage) : 0}%</span>
                  <span className="match-score-label">Match Score</span>
                </div>
                
                <div className="match-bar-wrap">
                  <div className="match-bar" style={{ width: `${matchModalResult?.match_percentage || 0}%` }} />
                </div>

                {matchModalResult?.error ? (
                  <p className="match-error">{matchModalResult.explanation}</p>
                ) : (
                  <div className="match-details">
                    <div className="match-section">
                      <h4>Missing Skills</h4>
                      <div className="match-pills">
                        {normalizeSkillList(matchModalResult?.missing_skills).length > 0 ? (
                          normalizeSkillList(matchModalResult.missing_skills).map((s, i) => <span key={i} className="skill-pill-missing">{s}</span>)
                        ) : (
                          <span className="skill-pill-ok"><CheckCircle2 size={12}/> Perfect Match</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="match-section">
                      <h4>Explanation</h4>
                      <p className="match-exp">{matchModalResult?.explanation || 'No explanation available.'}</p>
                    </div>
                  </div>
                )}
                
                <Button className="w-full" onClick={() => setMatchModalOpen(false)}>Close</Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Jobs
