import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import { applicationsAPI, jobsAPI, profileAPI } from '../api/client'
import { Search, MapPin, ExternalLink, CheckCircle2 } from 'lucide-react'
import './Jobs.css'
import ResumeModal from '../components/ResumeModal'

const PAGE_SIZE = 20

const LOCATION_OPTIONS = ['Pakistan', 'Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Remote']
const PAK_CITIES = ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad']
// Job actions should be available once the profile is reasonably complete.
const PROFILE_COMPLETENESS_THRESHOLD = 30

const countryMap = {
  Pakistan: 'pk',
  Karachi: 'pk',
  Lahore: 'pk',
  Islamabad: 'pk',
  Rawalpindi: 'pk',
  Faisalabad: 'pk',
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
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState('')
  const [searchAttempted, setSearchAttempted] = useState(false)
  
  const [matchModalOpen, setMatchModalOpen] = useState(false)
  const [matchModalLoading, setMatchModalLoading] = useState(false)
  const [matchModalResult, setMatchModalResult] = useState(null)
  
  const [toast, setToast] = useState('')
  const [profileExists, setProfileExists] = useState(false)
  const [profileCompleteness, setProfileCompleteness] = useState(0)
  const [salaryCard, setSalaryCard] = useState(null)
  const [salaryData, setSalaryData] = useState(null)
  const [resumeModalOpen, setResumeModalOpen] = useState(false)
  const [resumeModalJob, setResumeModalJob] = useState(null)
  
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)

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

  const fetchJobsPage = async (pageNumber = 1, { replace = true } = {}) => {
    setIsSearching(true)
    setSearchAttempted(true)
    setError('')
    setSalaryCard(null)
    setSalaryData(null)
    const selectedRemote = remoteOnly || location === 'Remote'
    const cityParam = location === 'Pakistan' || location === 'UAE' || location === 'UK' || location === 'Remote' ? '' : location

    try {
      if (replace && pageNumber === 1) {
        setJobs([])
      }
      const response = await jobsAPI.search({
        query,
        location,
        city: cityParam,
        remote_only: selectedRemote,
        pakistan_only: pakistanOnly,
        country_code: countryMap[location] || 'pk',
        page: pageNumber,
        limit: PAGE_SIZE,
      })
      const incoming = response.data || []
      setHasMore(incoming.length === PAGE_SIZE)
      setPage(pageNumber)
      setJobs((current) => (replace || pageNumber === 1 ? incoming : [...current, ...incoming]))
      if (!incoming.length) {
        setError('No live jobs found. Try again later.')
      }
    } catch (e) {
      console.error('Search error:', e)
      setError('No live jobs found. Try again later.')
      setJobs([])
      setHasMore(false)
    }
    setIsSearching(false)
  }

  const search = async () => {
    await fetchJobsPage(1, { replace: true })
  }

  const loadMore = async () => {
    if (!hasMore || isSearching) return
    await fetchJobsPage(page + 1, { replace: false })
  }

  const previousPage = async () => {
    if (page <= 1 || isSearching) return
    await fetchJobsPage(page - 1, { replace: true })
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
      setMatchModalResult({
        match_percentage: null,
        explanation: e?.userMessage || 'Failed to fetch match',
        missing_skills: null,
        error: true,
      })
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

  const openResumeBuilder = async (job) => {
    try {
      let jobRecord = job
      if (!jobRecord?.id) {
        const upsert = await jobsAPI.upsert(job)
        const jobId = upsert.data?.id || upsert.data?.job_id || null
        if (jobId) {
          jobRecord = { ...job, id: jobId }
        }
      }
      setResumeModalJob(jobRecord)
      setResumeModalOpen(true)
    } catch (e) {
      console.error('Failed to prepare resume builder', e)
      alert('Could not prepare the resume builder for this job yet.')
    }
  }

  const sourceBadge = (source) => {
    if (source === 'adzuna') return 'adzuna'
    if (source === 'jobicy') return 'jobicy'
    if (source === 'remotive') return 'remote'
    return String(source || 'remote')
  }

  const parseCompleteness = (value) => {
    const num = Number(value)
    if (Number.isFinite(num)) return Math.max(0, Math.min(100, Math.round(num)))
    return null
  }

  const deriveCompletenessFromProfile = (profile) => {
    if (!profile || typeof profile !== 'object') return 0

    const explicit = parseCompleteness(profile.profile_completeness)
    if (explicit !== null) return explicit

    // Fallback heuristic if API omits profile_completeness in selected payload.
    let score = 0
    if (String(profile.full_name || '').trim()) score += 10
    if (String(profile.email || '').trim()) score += 10
    if (String(profile.phone || '').trim()) score += 10
    if (String(profile.location || '').trim()) score += 10
    if (String(profile.summary || '').trim()) score += 15
    if (Array.isArray(profile.skills) && profile.skills.length > 0) score += 15
    if (Array.isArray(profile.work_experience) && profile.work_experience.length > 0) score += 15
    if (Array.isArray(profile.education) && profile.education.length > 0) score += 15
    return Math.min(100, score)
  }

  const refreshProfileStatus = async () => {
    try {
      let selectedProfile = null
      let selectedProfileId = null

      try {
        const selectedResponse = await profileAPI.selected()
        selectedProfile = selectedResponse?.data?.profile || null
        selectedProfileId = selectedResponse?.data?.selected_profile_id ?? selectedProfile?.id ?? null
      } catch {
        selectedProfile = null
        selectedProfileId = null
      }

      const listResponse = await profileAPI.list(1, 50)
      const profiles = Array.isArray(listResponse?.data?.profiles) ? listResponse.data.profiles : []
      const listSelectedId = listResponse?.data?.selected_profile_id ?? null
      const effectiveSelectedId = selectedProfileId ?? listSelectedId

      const selectedFromList = profiles.find((item) => item?.id === effectiveSelectedId) || null
      const completeness =
        parseCompleteness(selectedFromList?.profile_completeness) ??
        deriveCompletenessFromProfile(selectedProfile)

      setProfileCompleteness(completeness)

      const isCompleteByFlag = Boolean(selectedProfile?.is_complete || selectedFromList?.is_complete)
      const hasSelectedProfile = Boolean(effectiveSelectedId)
      const isCompleteByScore = completeness >= PROFILE_COMPLETENESS_THRESHOLD

      setProfileExists(Boolean(hasSelectedProfile && (isCompleteByFlag || isCompleteByScore)))
    } catch {
      setProfileExists(false)
      setProfileCompleteness(0)
    }
  }

  useEffect(() => {
    void refreshProfileStatus()
    const onFocus = () => {
      void refreshProfileStatus()
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('focus', onFocus)
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('focus', onFocus)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const getScoreTone = (score) => {
    if (score >= 70) {
      return { background: 'rgba(16, 185, 129, 0.10)', color: '#047857', borderColor: 'rgba(16, 185, 129, 0.18)' }
    }
    if (score >= 40) {
      return { background: 'rgba(245, 158, 11, 0.12)', color: '#b45309', borderColor: 'rgba(245, 158, 11, 0.20)' }
    }
    return { background: 'rgba(239, 68, 68, 0.10)', color: '#b91c1c', borderColor: 'rgba(239, 68, 68, 0.18)' }
  }

  const getScoreLabel = (score) => {
    if (score >= 70) return 'High'
    if (score >= 40) return 'Medium'
    return 'Low'
  }

  // Intentionally do not auto-search on mount.
  // Users should trigger search explicitly to avoid unexpected job loads.

  return (
    <div className="jobs-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div className="page-header">
        <p style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>
          Job search
        </p>
        <h1 style={{ marginTop: '6px' }}>Jobs</h1>
        <p className="subtitle">Search and save jobs with location-first filters.</p>
      </div>

      <section className="app-card" style={{ padding: '22px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ position: 'relative', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
              <Search size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--j-text-3)', pointerEvents: 'none' }} />
              <input
                value={query}
                onChange={(event) => handleQueryChange(event.target.value)}
                onFocus={() => query.length > 0 && setShowSuggestions(true)}
                placeholder="Search jobs by title, company, or keyword"
                style={{
                  width: '100%',
                  minHeight: '54px',
                  padding: '0 16px 0 46px',
                  borderRadius: '16px',
                  border: '1px solid var(--j-border)',
                  background: 'var(--j-surface)',
                  color: 'var(--j-text-1)',
                  outline: 'none',
                  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.72)',
                }}
              />

              {showSuggestions && suggestions.length > 0 && (
                <div className="autocomplete-dropdown" style={{ left: 0, right: 0, top: 'calc(100% + 8px)', borderRadius: '16px', boxShadow: 'var(--j-shadow-md)' }}>
                  {suggestions.map((suggestion, index) => (
                    <div key={index} className="autocomplete-item" onClick={() => selectSuggestion(suggestion)}>
                      {suggestion}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Button onClick={search} loading={isSearching}>Search</Button>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '14px', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {LOCATION_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setLocation(option)}
                  style={{
                    minHeight: '36px',
                    padding: '0 14px',
                    borderRadius: '999px',
                    border: location === option ? '1px solid rgba(58,87,232,0.24)' : '1px solid var(--j-border)',
                    background: location === option ? 'rgba(58,87,232,0.10)' : 'var(--j-surface-2)',
                    color: location === option ? 'var(--j-accent)' : 'var(--j-text-2)',
                    fontSize: '13px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {option}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '8px 12px', borderRadius: '999px', border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-2)', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
                <input type="checkbox" checked={pakistanOnly} onChange={(e) => { setPakistanOnly(e.target.checked); if (e.target.checked) setRemoteOnly(false); }} />
                Pakistan only
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '8px 12px', borderRadius: '999px', border: '1px solid var(--j-border)', background: 'var(--j-surface-2)', color: 'var(--j-text-2)', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
                <input type="checkbox" checked={remoteOnly} onChange={(e) => { setRemoteOnly(e.target.checked); if (e.target.checked) setPakistanOnly(false); }} />
                Remote only
              </label>
            </div>
          </div>
        </div>
      </section>

      {error && <p className="status-message error">{error}</p>}
      {!profileExists && <p className="status-message warning">⚠️ Please complete your profile first — Match Me and Resume will prompt you to finish it.</p>}
      {profileExists && <p className="status-message success">Profile ready ({profileCompleteness}% complete). Job search, Match Me, and Tailor Resume are enabled.</p>}
      {toast && <p className="status-message success">{toast}</p>}
      
      {!isSearching && jobs.length > 0 && <p className="results-count">{resultText}</p>}
      
      {isSearching && (
        <div className="search-loader">
          <div className="loader-text">Gathering live jobs from Rozee, Mustakbil, and other boards... This may take 10-15 seconds.</div>
          <div className="loader-bar-wrap">
            <div className="loader-bar" style={{ width: '70%' }} />
          </div>
        </div>
      )}

      {!isSearching && searchAttempted && jobs.length === 0 && (
        <div className="empty-state">
          <Search size={32} color="var(--j-text-3)" opacity={0.5} />
          <p className="section-label" style={{ marginBottom: 0 }}>NO LIVE JOBS FOUND</p>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--j-text-1)' }}>{error || 'Try again later.'}</h2>
          <p style={{ color: 'var(--j-text-2)' }}>We searched the live job boards but couldn’t get a fresh result set for this query yet.<br />Try again in a moment or broaden the role title.</p>
        </div>
      )}

      {!isSearching && !searchAttempted && jobs.length === 0 && (
        <div className="empty-state">
          <Search size={32} color="var(--j-text-3)" opacity={0.5} />
          <p className="section-label" style={{ marginBottom: 0 }}>SEARCH LIVE JOB BOARDS</p>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--j-text-1)' }}>Run a search to fetch current openings</h2>
          <p style={{ color: 'var(--j-text-2)' }}>Use the search button to load fresh jobs from the live sources.</p>
        </div>
      )}

      <div className="jobs-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '18px' }}>
        {jobs.map((job, index) => (
          <article
            key={`${job.id || index}-${job.title}`}
            className="job-card fade-up"
            style={{
              background: 'var(--j-surface)',
              border: '1px solid var(--j-border)',
              borderRadius: '22px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              boxShadow: 'var(--j-shadow-sm)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
              <div style={{ minWidth: 0 }}>
                <span style={{ display: 'inline-flex', fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>
                  {sourceBadge(job.source)}
                </span>
                <h3 style={{ marginTop: '8px', fontSize: '17px', lineHeight: 1.25, fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--j-text-1)' }}>
                  {job.title}
                </h3>
                <p style={{ marginTop: '4px', fontSize: '13px', color: 'var(--j-text-2)', fontWeight: 600 }}>
                  {job.company}
                </p>
              </div>

              <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                {(() => {
                  const score = Number(job.match_percentage ?? job.match_score ?? job.score ?? 0)
                  const tone = getScoreTone(score)
                  return (
                    <span className="status-pill" style={{ ...tone, minWidth: '72px', justifyContent: 'center' }}>
                      {score > 0 ? `${Math.round(score)}% ${getScoreLabel(score)}` : 'New'}
                    </span>
                  )
                })()}
                {resolveExternalJobUrl(job) ? (
                  <a href={resolveExternalJobUrl(job)} target="_blank" rel="noreferrer" style={{ fontSize: '12px', fontWeight: 700, color: 'var(--j-accent)' }}>
                    View role
                  </a>
                ) : null}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--j-text-2)', fontSize: '13px' }}>
              <MapPin size={14} />
              <span>{job.location || 'Remote'}</span>
            </div>

            <div style={{ flex: 1, color: 'var(--j-text-2)', fontSize: '13px', lineHeight: 1.6, maxHeight: '96px', overflow: 'hidden' }}>
              {job.description || 'No description available.'}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: 'auto', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => {
                  if (!profileExists) {
                    alert('Please complete your profile first')
                    return
                  }
                  openMatch(job)
                }}
                style={{
                  minHeight: '42px',
                  padding: '0 15px',
                  borderRadius: '14px',
                  border: '0',
                  background: 'linear-gradient(135deg, var(--j-accent), var(--j-accent-2))',
                  color: '#fff',
                  fontWeight: 700,
                  cursor: profileExists ? 'pointer' : 'not-allowed',
                  opacity: profileExists ? 1 : 0.55,
                  boxShadow: '0 12px 24px rgba(58,87,232,0.18)',
                }}
                disabled={!profileExists}
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
                  openResumeBuilder(job)
                }}
                style={{
                  minHeight: '42px',
                  padding: '0 15px',
                  borderRadius: '14px',
                  border: '1px solid var(--j-border)',
                  background: 'rgba(255,255,255,0.96)',
                  color: 'var(--j-text-1)',
                  fontWeight: 700,
                  cursor: profileExists ? 'pointer' : 'not-allowed',
                  opacity: profileExists ? 1 : 0.55,
                }}
                disabled={!profileExists}
                title={profileExists ? 'Generate a tailored resume for this job' : 'Complete your profile to use Tailor Resume'}
              >
                Tailor Resume
              </button>
              <button
                type="button"
                onClick={() => saveToTracker(job)}
                aria-label="Save job"
                title="Save job"
                style={{
                  marginLeft: 'auto',
                  width: '42px',
                  height: '42px',
                  borderRadius: '14px',
                  border: '1px solid var(--j-border)',
                  background: 'rgba(255,255,255,0.96)',
                  color: 'var(--j-accent)',
                  fontSize: '18px',
                  lineHeight: 1,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                ♥
              </button>
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

      <div className="modal-actions" style={{ marginTop: 16, display: 'flex', gap: '12px', justifyContent: 'center' }}>
        <Button variant="secondary" disabled={page <= 1 || isSearching} onClick={previousPage}>Previous</Button>
        <Button variant="secondary" disabled={!hasMore || isSearching} onClick={loadMore}>Load More</Button>
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

      <ResumeModal
        open={resumeModalOpen}
        job={resumeModalJob}
        onClose={() => {
          setResumeModalOpen(false)
          setResumeModalJob(null)
        }}
      />
    </div>
  )
}

export default Jobs
