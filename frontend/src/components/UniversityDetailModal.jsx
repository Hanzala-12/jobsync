import { useEffect, useMemo, useState } from 'react'
import Button from './Button'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

function UniversityDetailModal({ open, studentProfileId, matchItem, onClose, onSaved }) {
  const [detail, setDetail] = useState(null)
  const [match, setMatch] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedProgramId, setSelectedProgramId] = useState(matchItem?.program?.id || null)

  const selectedProgram = useMemo(() => {
    if (!detail?.programs?.length) return matchItem?.program || null
    return detail.programs.find((program) => program.id === selectedProgramId) || detail.programs[0]
  }, [detail, matchItem, selectedProgramId])

  useEffect(() => {
    if (!open || !matchItem?.university?.id) return

    let mounted = true
    setLoading(true)
    setError('')
    setDetail(null)
    setMatch(null)
    Promise.all([
      studentAPI.getUniversityDetail(matchItem.university.id),
      studentAPI.getProgramMatch(studentProfileId, matchItem.program.id),
    ])
      .then(([detailRes, matchRes]) => {
        if (!mounted) return
        setDetail(detailRes.data)
        setMatch(matchRes.data)
        setSelectedProgramId(matchItem.program.id)
      })
      .catch((err) => {
        if (mounted) setError(err.userMessage || 'Failed to load university details')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [open, matchItem, studentProfileId])

  useEffect(() => {
    if (!open || !selectedProgramId || !studentProfileId) return

    let mounted = true
    studentAPI.getProgramMatch(studentProfileId, selectedProgramId)
      .then((response) => {
        if (mounted) setMatch(response.data)
      })
      .catch(() => {
        if (mounted) setMatch((prev) => prev)
      })

    return () => {
      mounted = false
    }
  }, [open, selectedProgramId, studentProfileId])

  if (!open || !matchItem) return null

  const program = selectedProgram || matchItem.program
  const matchAnalysis = match?.analysis || match?.match || {}
  const matchSummary = matchAnalysis.summary || 'This score is based on the current student profile, program requirements, and cost fit.'
  const strengths = matchAnalysis.strengths || []
  const missingRequirements = matchAnalysis.missing_requirements || []

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await studentAPI.saveUniversity(studentProfileId, program.id)
      onSaved?.()
    } catch (err) {
      setError(err.userMessage || 'Failed to save program')
    } finally {
      setSaving(false)
    }
  }

  const apply = async () => {
    setApplying(true)
    setError('')
    try {
      await studentAPI.applyProgram(studentProfileId, program.id)
      onSaved?.()
    } catch (err) {
      setError(err.userMessage || 'Failed to create application')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="panel-head">
          <div>
            <p className="section-label">University detail</p>
            <h2>{detail?.university?.name || matchItem.university.name}</h2>
            <p className="muted-small">{detail?.university?.country || matchItem.university.country} · Ranking {detail?.university?.ranking_global || matchItem.university.ranking_global || matchItem.university.ranking || 'N/A'}</p>
          </div>
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>

        {error && <p className="muted-small" style={{ color: 'var(--danger)' }}>{error}</p>}
        {loading ? (
          <div className="loading-block">Loading university details...</div>
        ) : (
          <>
            <div className="summary-grid">
              <div className="study-panel">
                <p className="section-label">Match Score</p>
                <p className="match-score-large">{matchAnalysis.match_score || match?.match_score || 0}%</p>
                <p className="muted-small">Academic {matchAnalysis.academic_fit || 0} · Budget {matchAnalysis.budget_fit || 0} · Location {matchAnalysis.location_fit || 0}</p>
                <p className="muted-small" style={{ marginTop: 8 }}>{matchSummary}</p>
              </div>
              <div className="study-panel">
                <p className="section-label">University facts</p>
                <p>{detail?.university?.acceptance_rate ? `${detail.university.acceptance_rate}% acceptance rate` : 'Acceptance rate not listed'}</p>
                <p className="muted-small">{detail?.university?.accreditation || 'No accreditation listed'}</p>
              </div>
              <div className="study-panel">
                <p className="section-label">Quick actions</p>
                <div className="modal-actions">
                  <Button onClick={save} loading={saving}>Save to My List</Button>
                  <Button variant="secondary" onClick={apply} loading={applying}>Apply Now</Button>
                </div>
              </div>
            </div>

            <div className="detail-tabs">
              {['overview', 'programs', 'analysis'].map((tab) => (
                <button key={tab} type="button" className={`detail-tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div className="detail-head">
                <div className="study-panel">
                  <p className="section-label">Programs</p>
                  <div className="detail-list">
                    {(detail?.programs || [matchItem.program]).map((item) => (
                      <button key={item.id} type="button" className={`detail-tab ${selectedProgramId === item.id ? 'active' : ''}`} onClick={() => setSelectedProgramId(item.id)}>
                        <strong>{item.name}</strong>
                        <span className="muted-small">{item.degree_level} · ${Number(item.estimated_tuition_fees || 0).toLocaleString()}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="study-panel">
                  <p className="section-label">Scholarships</p>
                  <div className="detail-list">
                    {(detail?.scholarships || []).length > 0 ? detail.scholarships.map((item) => (
                      <div key={item.id} className="detail-card">
                        <strong>{item.name}</strong>
                        <p className="muted-small">${item.amount_usd || 0} · Deadline {item.deadline || 'TBD'}</p>
                        <p className="muted-small">{item.eligibility_criteria || 'Eligibility not listed'}</p>
                      </div>
                    )) : <p className="muted-small">No scholarships listed for this university.</p>}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'programs' && (
              <div className="study-panel">
                <p className="section-label">Program requirements</p>
                <div className="detail-list">
                  <div className="detail-card">
                    <h3>{program.name}</h3>
                    <p className="muted-small">Tuition: ${Number(program.estimated_tuition_fees || 0).toLocaleString()} per year</p>
                    <p className="muted-small">Living cost: ${Number(program.living_cost_estimate || 0).toLocaleString()} per year</p>
                    <p className="muted-small">Deadline: {program.application_deadline || 'TBD'} · Intake: {program.semester_intake || 'TBD'}</p>
                    <p className="muted-small">Minimum GPA: {program.min_gpa ?? 'N/A'} · IELTS: {program.min_ielts ?? 'N/A'} · TOEFL: {program.min_toefl ?? 'N/A'}</p>
                    <p className="muted-small">Scholarship: {program.scholarship_available ? 'Available' : 'Not listed'}</p>
                    <div className="modal-actions" style={{ marginTop: 12 }}>
                      {program.program_url ? <a className="btn btn-primary" href={program.program_url} target="_blank" rel="noreferrer">Apply Now</a> : null}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'analysis' && (
              <div className="study-panel">
                <p className="section-label">Match analysis</p>
                <div className="summary-grid" style={{ marginBottom: 16 }}>
                  <div className="detail-card"><strong>Academic fit</strong><p>{matchAnalysis.academic_fit || 0}%</p></div>
                  <div className="detail-card"><strong>Budget fit</strong><p>{matchAnalysis.budget_fit || 0}%</p></div>
                  <div className="detail-card"><strong>Location fit</strong><p>{matchAnalysis.location_fit || 0}%</p></div>
                </div>
                <div className="detail-list">
                  <div className="detail-card">
                    <strong>Strengths</strong>
                    <ul className="bullet-list">{strengths.map((item) => <li key={item}>{item}</li>)}</ul>
                  </div>
                  <div className="detail-card">
                    <strong>Missing requirements</strong>
                    <ul className="bullet-list">{missingRequirements.map((item) => <li key={item}>{item}</li>)}</ul>
                  </div>
                  <div className="detail-card">
                    <strong>Recommendations</strong>
                    <ul className="bullet-list">{(matchAnalysis.recommendations || []).map((item) => <li key={item}>{item}</li>)}</ul>
                  </div>
                  <div className="detail-card">
                    <strong>Summary</strong>
                    <p>{matchAnalysis.summary || 'Analysis will appear here once the match is loaded.'}</p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default UniversityDetailModal