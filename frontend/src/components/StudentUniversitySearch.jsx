import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './Button'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

function StudentUniversitySearch({ profileId }) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [savingId, setSavingId] = useState(null)
  const [error, setError] = useState('')
  const [results, setResults] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    country: '',
    min_ranking: '',
    max_tuition: '',
    degree_level: '',
    intake: '',
    scholarship_only: false,
  })

  const canSave = Boolean(profileId)

  const loadResults = async (nextPage = 1, append = false) => {
    setLoading(true)
    setError('')
    try {
      const response = await studentAPI.getUniversitiesFilter({
        page: nextPage,
        limit: 12,
        country: filters.country || undefined,
        min_ranking: filters.min_ranking === '' ? undefined : Number(filters.min_ranking),
        max_tuition: filters.max_tuition === '' ? undefined : Number(filters.max_tuition),
        degree_level: filters.degree_level || undefined,
        intake: filters.intake || undefined,
        scholarship_only: filters.scholarship_only,
      })
      const payload = response.data || {}
      const incoming = payload.items || []
      setTotal(Number(payload.total || 0))
      setPage(Number(payload.page || nextPage))
      setResults((prev) => (append ? [...prev, ...incoming] : incoming))
    } catch (err) {
      setError(err.userMessage || 'Could not load universities')
      if (!append) setResults([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResults(1, false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const resultCount = useMemo(() => results.reduce((count, item) => count + (item.programs?.length || 0), 0), [results])

  const saveProgram = async (universityId, programId) => {
    if (!canSave) {
      navigate('/student/profile')
      return
    }

    setSavingId(programId)
    setError('')
    try {
      await studentAPI.saveUniversity(profileId, programId)
    } catch (err) {
      setError(err.userMessage || 'Failed to save program')
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div className="study-page">
      <section className="study-hero">
        <div>
          <p className="section-label">Study Mode</p>
          <h1>University search and filter</h1>
          <p className="muted">Browse universities directly, then save the ones that fit your budget and academic profile.</p>
        </div>
        <div className="study-hero-actions">
          <span className="study-badge">{results.length} universities</span>
          <span className="study-badge">{resultCount} programs</span>
          <Button variant="secondary" onClick={() => navigate('/student/matches')}>View Matches</Button>
        </div>
      </section>

      <section className="study-panel">
        <div className="panel-head">
          <div>
            <p className="section-label">Filters</p>
            <h2>Refine your search</h2>
          </div>
          <div className="study-badge">{canSave ? 'Saving enabled' : 'Create a profile to save'}</div>
        </div>

        <div className="search-filters">
          <label>
            <span>Country</span>
            <input value={filters.country} onChange={(event) => setFilters({ ...filters, country: event.target.value })} placeholder="Singapore" />
          </label>
          <label>
            <span>Degree level</span>
            <input value={filters.degree_level} onChange={(event) => setFilters({ ...filters, degree_level: event.target.value })} placeholder="Masters" />
          </label>
          <label>
            <span>Intake</span>
            <input value={filters.intake} onChange={(event) => setFilters({ ...filters, intake: event.target.value })} placeholder="Fall" />
          </label>
          <label>
            <span>Min ranking</span>
            <input type="number" value={filters.min_ranking} onChange={(event) => setFilters({ ...filters, min_ranking: event.target.value })} placeholder="200" />
          </label>
          <label>
            <span>Max tuition</span>
            <input type="number" value={filters.max_tuition} onChange={(event) => setFilters({ ...filters, max_tuition: event.target.value })} placeholder="25000" />
          </label>
          <label className="checkbox-item">
            <input type="checkbox" checked={filters.scholarship_only} onChange={(event) => setFilters({ ...filters, scholarship_only: event.target.checked })} />
            <span>Scholarship only</span>
          </label>
        </div>

        <div className="modal-actions" style={{ marginTop: 14 }}>
          <Button onClick={() => loadResults(1, false)}>Search</Button>
          <Button variant="secondary" onClick={() => {
            setFilters({ country: '', min_ranking: '', max_tuition: '', degree_level: '', intake: '', scholarship_only: false })
            loadResults(1, false)
          }}>
            Reset
          </Button>
        </div>
      </section>

      {error && <p className="muted-small" style={{ color: 'var(--danger)' }}>{error}</p>}

      {loading && results.length === 0 ? (
        <div className="study-panel"><div className="loading-block">Loading universities...</div></div>
      ) : results.length > 0 ? (
        <div className="match-grid">
          {results.map((item) => (
            <article className="match-card" key={item.university.id}>
              <div className="match-card-top">
                <div>
                  <span className="ranking-pill">{item.university.country || 'Unknown country'}</span>
                  <h3>{item.university.name}</h3>
                  <p className="muted-small">{item.university.city || 'City not listed'} · {item.programs?.length || 0} programs</p>
                </div>
                <div className="score-pill warn">{item.university.ranking_global || item.university.ranking || 'N/A'}</div>
              </div>

              <div className="detail-list" style={{ marginTop: 12 }}>
                {(item.programs || []).slice(0, 3).map((program) => (
                  <div key={program.id} className="detail-card">
                    <strong>{program.name}</strong>
                    <p className="muted-small">{program.degree_level} · Tuition ${Number(program.estimated_tuition_fees || 0).toLocaleString()}</p>
                    <p className="muted-small">Scholarship: {program.scholarship_available ? 'Available' : 'Not listed'}</p>
                    <div className="button-row" style={{ marginTop: 10 }}>
                      <Button onClick={() => saveProgram(item.university.id, program.id)} loading={savingId === program.id}>Save</Button>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="study-panel">
          <div className="empty-block">
            <div>
              <p className="section-label">No results yet</p>
              <h2>Try a broader filter</h2>
              <p>Search results will appear here after you apply a filter set.</p>
            </div>
          </div>
        </div>
      )}

      {results.length > 0 && total > results.length && (
        <div className="modal-actions">
          <Button variant="secondary" loading={loading} onClick={() => loadResults(page + 1, true)}>Load More</Button>
        </div>
      )}
    </div>
  )
}

export default StudentUniversitySearch