import { useEffect, useMemo, useRef, useState } from 'react'
import { Bookmark, School, Star } from 'lucide-react'
import Button from './Button'
import UniversityDetailModal from './UniversityDetailModal'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

const PAGE_SIZE = 10

function scoreClass(score) {
  if (score >= 80) return 'good'
  if (score >= 60) return 'warn'
  return 'bad'
}

function UniversityMatchList({ profileId, heading = 'University Matches', initialLimit = PAGE_SIZE, showFilters = true, onResultsLoaded }) {
  const [results, setResults] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({
    filter_countries: '',
    filter_max_tuition: '',
    filter_scholarship_only: false,
    sort_by: 'match_score',
  })
  const [rankingRange, setRankingRange] = useState({ min: '', max: '' })
  const [selected, setSelected] = useState(null)
  const [savedToast, setSavedToast] = useState('')
  const [compareIds, setCompareIds] = useState([])
  const sentinelRef = useRef(null)

  const fetchMatches = async (nextPage = 1) => {
    if (!profileId) return
    setLoading(true)
    setError('')
    try {
      const response = await studentAPI.getRecommendations(profileId, nextPage * initialLimit, {
        filter_countries: filters.filter_countries.split(',').map((item) => item.trim()).filter(Boolean),
        filter_max_tuition: filters.filter_max_tuition === '' ? undefined : Number(filters.filter_max_tuition),
        filter_scholarship_only: filters.filter_scholarship_only,
        sort_by: filters.sort_by,
      })
      const incoming = response.data?.results || []
      const minRanking = rankingRange.min === '' ? null : Number(rankingRange.min)
      const maxRanking = rankingRange.max === '' ? null : Number(rankingRange.max)
      const filtered = incoming.filter((item) => {
        const ranking = Number(item.university?.ranking_global || item.program?.ranking_global || 0)
        if (minRanking !== null && ranking && ranking > minRanking) return false
        if (maxRanking !== null && ranking && ranking < maxRanking) return false
        return true
      })
      setResults(filtered)
      onResultsLoaded?.(filtered)
    } catch (err) {
      setError(err.userMessage || 'No matches could be loaded')
      setResults([])
      onResultsLoaded?.([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMatches(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, page, filters.sort_by, filters.filter_countries, filters.filter_max_tuition, filters.filter_scholarship_only, rankingRange.min, rankingRange.max])

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting) && !loading && results.length >= page * initialLimit) {
        setPage((prev) => prev + 1)
      }
    }, { rootMargin: '120px' })

    if (sentinelRef.current) observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [loading, results.length, page])

  const compareItems = useMemo(() => results.filter((item) => compareIds.includes(item.program.id)).slice(0, 2), [results, compareIds])

  const toggleCompare = (programId) => {
    setCompareIds((prev) => prev.includes(programId) ? prev.filter((id) => id !== programId) : [...prev, programId].slice(0, 2))
  }

  const saveItem = async (item) => {
    try {
      await studentAPI.saveUniversity(profileId, item.program.id)
      setSavedToast(`${item.university.name} saved to your list`)
      setTimeout(() => setSavedToast(''), 1800)
    } catch (err) {
      setError(err.userMessage || 'Failed to save program')
    }
  }

  const visibleResults = useMemo(() => results.slice(0, Math.max(1, page * initialLimit)), [results, page, initialLimit])

  if (!profileId) {
    return (
      <div className="study-panel">
        <div className="empty-block">
          <div>
            <p className="section-label">No profile yet</p>
            <h2>Create your profile first</h2>
            <p>We need your student profile before we can rank programs and universities.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <section className="study-panel">
      <div className="panel-head">
        <div>
          <p className="section-label">{heading}</p>
          <h2>{visibleResults.length} programs ready</h2>
          <p className="muted-small">Personalized by your academic profile, budget, and country preferences.</p>
        </div>
        <div className="score-pill good">{visibleResults.length || 0}</div>
      </div>

      {showFilters && (
        <div className="match-page">
          <aside className="filter-panel match-sidebar">
            <div className="panel-head"><div><p className="section-label">Filters</p><h2>Refine matches</h2></div></div>
            <div className="filter-row">
              <label>
                <span>Countries</span>
                <input value={filters.filter_countries} onChange={(e) => setFilters({ ...filters, filter_countries: e.target.value })} placeholder="Malaysia, Singapore" />
              </label>
              <label>
                <span>Max tuition</span>
                <input type="number" value={filters.filter_max_tuition} onChange={(e) => setFilters({ ...filters, filter_max_tuition: e.target.value })} placeholder="25000" />
              </label>
              <label>
                <span>Ranking min</span>
                <input type="number" value={rankingRange.min} onChange={(e) => setRankingRange({ ...rankingRange, min: e.target.value })} placeholder="Top 200" />
              </label>
              <label>
                <span>Ranking max</span>
                <input type="number" value={rankingRange.max} onChange={(e) => setRankingRange({ ...rankingRange, max: e.target.value })} placeholder="Top 50" />
              </label>
              <label>
                <span>Sort by</span>
                <select value={filters.sort_by} onChange={(e) => setFilters({ ...filters, sort_by: e.target.value })}>
                  <option value="match_score">Match score</option>
                  <option value="ranking">Ranking</option>
                  <option value="tuition">Tuition</option>
                  <option value="country">Country</option>
                </select>
              </label>
              <label className="checkbox-item">
                <input type="checkbox" checked={filters.filter_scholarship_only} onChange={(e) => setFilters({ ...filters, filter_scholarship_only: e.target.checked })} />
                <span>Scholarship only</span>
              </label>
            </div>
            <div className="modal-actions" style={{ marginTop: 14 }}>
              <Button onClick={() => { setPage(1); fetchMatches(1) }}>Apply Filters</Button>
              <Button variant="secondary" onClick={() => {
                setFilters({ filter_countries: '', filter_max_tuition: '', filter_scholarship_only: false, sort_by: 'match_score' })
                setRankingRange({ min: '', max: '' })
                setPage(1)
              }}>Reset</Button>
            </div>
          </aside>

          <div>
            {savedToast && <p className="muted-small" style={{ marginBottom: 10, color: 'var(--success)' }}>{savedToast}</p>}
            {error && <p className="muted-small" style={{ marginBottom: 10, color: 'var(--danger)' }}>{error}</p>}
            {loading && results.length === 0 ? (
              <div className="loading-block">Loading matches...</div>
            ) : visibleResults.length > 0 ? (
              <div className="match-grid">
                {visibleResults.map((item) => {
                  const ranking = item.university.ranking_global || item.program.ranking_global || item.university.ranking || 'N/A'
                  const score = item.match.match_score || 0
                  return (
                    <article className="match-card" key={item.program.id}>
                      <div className="match-card-top">
                        <div>
                          <span className="ranking-pill">Rank {ranking}</span>
                          <h3>{item.university.name}</h3>
                          <p className="muted-small">{item.university.country} · {item.program.name}</p>
                        </div>
                        <div className={`score-pill ${scoreClass(score)}`}>{score}%</div>
                      </div>
                      <div className="meta">
                        <span className="tag-pill"><School size={14} /> Tuition ${Number(item.program.estimated_tuition_fees || 0).toLocaleString()}</span>
                        <span className="tag-pill"><Star size={14} /> {item.program.scholarship_available ? 'Scholarship' : 'No scholarship'}</span>
                        <span className="tag-pill"><Bookmark size={14} /> {item.vector_similarity}% vector fit</span>
                      </div>
                      <div className="button-row" style={{ marginTop: 14 }}>
                        <Button onClick={() => setSelected(item)}>View Details</Button>
                        <Button variant="secondary" onClick={() => saveItem(item)}>Save</Button>
                        <Button variant="secondary" onClick={() => toggleCompare(item.program.id)}>{compareIds.includes(item.program.id) ? 'Remove' : 'Compare'}</Button>
                      </div>
                    </article>
                  )
                })}
              </div>
            ) : (
              <div className="empty-block">
                <div>
                  <p className="section-label">No matches found</p>
                  <h2>Try relaxing the filters</h2>
                  <p>We couldn’t find any programs that match the current filters.</p>
                </div>
              </div>
            )}
            <div ref={sentinelRef} />
            <div className="modal-actions" style={{ marginTop: 16 }}>
              <Button variant="secondary" disabled={page === 1} onClick={() => setPage((prev) => Math.max(1, prev - 1))}>Previous</Button>
              <Button variant="secondary" onClick={() => setPage((prev) => prev + 1)}>Load More</Button>
            </div>
            {compareItems.length > 0 && (
              <div className="compare-grid" style={{ marginTop: 18 }}>
                {compareItems.map((item) => (
                  <article key={item.program.id} className="compare-card">
                    <p className="section-label">Compare</p>
                    <h3>{item.university.name}</h3>
                    <p className="muted-small">{item.program.name}</p>
                    <p className="muted-small">Match {item.match.match_score}% · Tuition ${Number(item.program.estimated_tuition_fees || 0).toLocaleString()}</p>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {!showFilters && (
        <div className="match-grid">
          {visibleResults.map((item) => (
            <article className="match-card" key={item.program.id}>
              <h3>{item.university.name}</h3>
              <p className="muted-small">{item.program.name}</p>
            </article>
          ))}
        </div>
      )}

      <UniversityDetailModal
        open={!!selected}
        matchItem={selected}
        studentProfileId={profileId}
        onClose={() => setSelected(null)}
        onSaved={() => fetchMatches(page)}
      />
    </section>
  )
}

export default UniversityMatchList