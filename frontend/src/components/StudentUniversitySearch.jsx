import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './Button'
import { studentAPI } from '../api/client'
import { Search, MapPin, GraduationCap, DollarSign, Award, Target, Filter, ChevronRight, BookmarkPlus } from 'lucide-react'
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
    <div className="study-page fade-up">
      <section className="study-hero">
        <div>
          <p className="section-label"><Search size={14} /> EXPLORE</p>
          <h1>University Search</h1>
          <p className="muted">Browse universities globally, then save the ones that fit your budget and academic profile.</p>
        </div>
        <div className="study-hero-actions">
          <span className="study-badge"><Target size={12} style={{display: 'inline', marginRight: 4}}/> {results.length} universities found</span>
          <Button variant="secondary" onClick={() => navigate('/student/matches')}>
            View Auto-Matches <ChevronRight size={14} style={{ display: 'inline', marginLeft: 4 }}/>
          </Button>
        </div>
      </section>

      <section className="study-panel border-box">
        <div className="panel-head">
          <div>
            <p className="section-label"><Filter size={14} /> FILTERS</p>
            <h2>Refine your search</h2>
          </div>
          {!canSave && (
            <div className="study-badge">Create a profile to save programs</div>
          )}
        </div>

        <div className="form-grid">
          <label>
            Country
            <div style={{ position: 'relative' }}>
              <input value={filters.country} onChange={(event) => setFilters({ ...filters, country: event.target.value })} placeholder="e.g. Singapore" style={{ paddingLeft: 32 }} />
              <MapPin size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--j-text-3)' }} />
            </div>
          </label>
          <label>
            Degree Level
            <div style={{ position: 'relative' }}>
              <input value={filters.degree_level} onChange={(event) => setFilters({ ...filters, degree_level: event.target.value })} placeholder="e.g. Masters" style={{ paddingLeft: 32 }} />
              <GraduationCap size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--j-text-3)' }} />
            </div>
          </label>
          <label>
            Min Ranking
            <div style={{ position: 'relative' }}>
              <input type="number" value={filters.min_ranking} onChange={(event) => setFilters({ ...filters, min_ranking: event.target.value })} placeholder="e.g. 200" style={{ paddingLeft: 32 }} />
              <Award size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--j-text-3)' }} />
            </div>
          </label>
          <label>
            Max Tuition
            <div style={{ position: 'relative' }}>
              <input type="number" value={filters.max_tuition} onChange={(event) => setFilters({ ...filters, max_tuition: event.target.value })} placeholder="e.g. 25000" style={{ paddingLeft: 32 }} />
              <DollarSign size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--j-text-3)' }} />
            </div>
          </label>
          <label>
            Intake
            <input value={filters.intake} onChange={(event) => setFilters({ ...filters, intake: event.target.value })} placeholder="e.g. Fall" />
          </label>
        </div>

        <div className="checkbox-grid" style={{ marginTop: 16 }}>
          <label className="checkbox-item">
            <input type="checkbox" checked={filters.scholarship_only} onChange={(event) => setFilters({ ...filters, scholarship_only: event.target.checked })} />
            Scholarship Available Only
          </label>
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <Button onClick={() => loadResults(1, false)}><Search size={14} style={{display: 'inline', marginRight: 6}}/> Search</Button>
          <Button variant="secondary" onClick={() => {
            setFilters({ country: '', min_ranking: '', max_tuition: '', degree_level: '', intake: '', scholarship_only: false })
            loadResults(1, false)
          }}>
            Clear Filters
          </Button>
        </div>
      </section>

      {error && <p className="muted-small" style={{ color: 'var(--j-red)' }}>{error}</p>}

      {loading && results.length === 0 ? (
        <div className="study-panel"><div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--j-text-3)' }}>Searching universities...</div></div>
      ) : results.length > 0 ? (
        <div className="grid-cols-2">
          {results.map((item) => (
            <article className="uni-card fade-up" key={item.university.id}>
              <div className="uni-header">
                <div>
                  <h3 className="uni-title">{item.university.name}</h3>
                  <div className="uni-meta">
                    <MapPin size={12} /> {item.university.city || 'Location not listed'}, {item.university.country || 'Unknown'}
                  </div>
                </div>
                <div className="match-score score-med">#{item.university.ranking_global || item.university.ranking || 'N/A'}</div>
              </div>

              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <p className="section-label">Top Programs</p>
                {(item.programs || []).slice(0, 3).map((program) => (
                  <div key={program.id} style={{ background: 'var(--j-surface-1)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--j-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <strong style={{ fontSize: 13, color: 'var(--j-text-1)', lineHeight: 1.4 }}>{program.name}</strong>
                      <span className="study-badge" style={{ whiteSpace: 'nowrap', marginLeft: 12 }}>{program.degree_level}</span>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                      <div>
                        <span style={{ fontSize: 11, color: 'var(--j-text-3)', display: 'block', textTransform: 'uppercase', marginBottom: 2 }}>Tuition</span>
                        <span style={{ fontSize: 13, color: 'var(--j-text-2)', fontWeight: 500 }}>${Number(program.estimated_tuition_fees || 0).toLocaleString()}</span>
                      </div>
                      <div>
                        <span style={{ fontSize: 11, color: 'var(--j-text-3)', display: 'block', textTransform: 'uppercase', marginBottom: 2 }}>Scholarship</span>
                        <span style={{ fontSize: 13, color: program.scholarship_available ? 'var(--j-green)' : 'var(--j-text-2)', fontWeight: 500 }}>
                          {program.scholarship_available ? 'Available' : 'None listed'}
                        </span>
                      </div>
                    </div>
                    
                    <Button size="small" variant="secondary" onClick={() => saveProgram(item.university.id, program.id)} loading={savingId === program.id} style={{ width: '100%' }}>
                      <BookmarkPlus size={14} style={{ display: 'inline', marginRight: 6 }}/> Save Program
                    </Button>
                  </div>
                ))}
                
                {(item.programs?.length || 0) > 3 && (
                  <div style={{ textAlign: 'center', marginTop: 4 }}>
                    <span style={{ fontSize: 12, color: 'var(--j-text-3)' }}>+ {(item.programs?.length || 0) - 3} more programs available</span>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Search size={32} color="var(--j-text-3)" opacity={0.5} />
          <p className="section-label" style={{ marginBottom: 0 }}>NO RESULTS</p>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--j-text-1)' }}>Try a broader filter</h2>
          <p style={{ color: 'var(--j-text-2)' }}>We couldn't find any universities matching your exact criteria.<br/>Try removing some filters.</p>
          <Button variant="secondary" onClick={() => {
            setFilters({ country: '', min_ranking: '', max_tuition: '', degree_level: '', intake: '', scholarship_only: false })
            loadResults(1, false)
          }}>
            Clear Filters
          </Button>
        </div>
      )}

      {results.length > 0 && total > results.length && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
          <Button variant="secondary" loading={loading} onClick={() => loadResults(page + 1, true)}>Load More Universities</Button>
        </div>
      )}
    </div>
  )
}

export default StudentUniversitySearch