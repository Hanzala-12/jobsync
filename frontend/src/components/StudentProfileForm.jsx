import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './Button'
import { studentAPI } from '../api/client'
import './UniversityModule.css'

const DEGREE_OPTIONS = ['Bachelors', 'Masters', 'PhD']
const FALLBACK_COUNTRIES = ['Malaysia', 'Singapore', 'Germany', 'Japan', 'South Korea', 'China', 'India', 'United Kingdom', 'United States']

function StudentProfileForm() {
  const navigate = useNavigate()
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [countries, setCountries] = useState(FALLBACK_COUNTRIES)
  const [majors, setMajors] = useState([])
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    gpa: 3.0,
    gre_score: '',
    toefl_score: '',
    ielts_score: '',
    budget_per_year: 25000,
    preferred_countries: [],
    intended_major: '',
    degree_level: 'Masters',
    academic_background: '',
  })

  useEffect(() => {
    let mounted = true
    studentAPI.getUniversitiesFilter({ page: 1, limit: 200 })
      .then((response) => {
        if (!mounted) return
        const groups = response.data?.items || []
        const countrySet = new Set()
        const majorSet = new Set()
        groups.forEach((group) => {
          if (group?.university?.country) countrySet.add(group.university.country)
          ;(group?.programs || []).forEach((program) => {
            if (program?.name) majorSet.add(program.name)
          })
        })
        setCountries(Array.from(countrySet).sort().slice(0, 120) || FALLBACK_COUNTRIES)
        setMajors(Array.from(majorSet).sort())
      })
      .catch(() => {
        if (mounted) {
          setCountries(FALLBACK_COUNTRIES)
          setMajors([])
        }
      })
      .finally(() => {
        if (mounted) setLoadingOptions(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const selectedCountries = useMemo(() => form.preferred_countries, [form.preferred_countries])

  const toggleCountry = (country) => {
    setForm((prev) => {
      const exists = prev.preferred_countries.includes(country)
      return {
        ...prev,
        preferred_countries: exists
          ? prev.preferred_countries.filter((item) => item !== country)
          : [...prev.preferred_countries, country],
      }
    })
  }

  const submit = async () => {
    setError('')
    setSaving(true)
    try {
      const payload = {
        ...form,
        gpa: Number(form.gpa),
        gre_score: form.gre_score === '' ? null : Number(form.gre_score),
        toefl_score: form.toefl_score === '' ? null : Number(form.toefl_score),
        ielts_score: form.ielts_score === '' ? null : Number(form.ielts_score),
      }
      const response = await studentAPI.createProfile(payload)
      const profileId = response.data?.id
      if (profileId) {
        localStorage.setItem('student_profile_id', String(profileId))
        window.dispatchEvent(new Event('storage'))
      }
      localStorage.setItem('study_mode', 'true')
      window.dispatchEvent(new Event('storage'))
      navigate('/student/dashboard')
    } catch (err) {
      setError(err.userMessage || 'Failed to create student profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="study-page">
      <section className="study-hero">
        <div>
          <p className="section-label">Study Mode</p>
          <h1>Create your student profile</h1>
          <p className="muted">Tell us your academic background, budget, and preferences so the matcher can rank the best programs.</p>
        </div>
        <div className="study-hero-actions">
          <span className="study-badge">Step {step} of 3</span>
          <Button variant="secondary" onClick={() => navigate('/student/dashboard')}>Skip to Dashboard</Button>
        </div>
      </section>

      <section className="profile-progress" aria-hidden="true">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`} />
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`} />
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`} />
      </section>

      {error && <div className="study-panel"><p className="muted" style={{ color: 'var(--danger)' }}>{error}</p></div>}

      {step === 1 && (
        <section className="profile-step">
          <div className="panel-head">
            <div>
              <p className="section-label">Academic info</p>
              <h2>Core credentials</h2>
            </div>
          </div>
          <div className="form-grid">
            <label>
              <span>GPA</span>
              <input type="number" min="0" max="4.0" step="0.01" value={form.gpa} onChange={(e) => setForm({ ...form, gpa: e.target.value })} />
            </label>
            <label>
              <span>GRE Score</span>
              <input type="number" min="0" max="340" value={form.gre_score} onChange={(e) => setForm({ ...form, gre_score: e.target.value })} placeholder="Optional" />
            </label>
            <label>
              <span>TOEFL Score</span>
              <input type="number" min="0" max="120" value={form.toefl_score} onChange={(e) => setForm({ ...form, toefl_score: e.target.value })} placeholder="Optional" />
            </label>
            <label>
              <span>IELTS Score</span>
              <input type="number" min="0" max="9" step="0.5" value={form.ielts_score} onChange={(e) => setForm({ ...form, ielts_score: e.target.value })} placeholder="Optional" />
            </label>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="profile-step">
          <div className="panel-head">
            <div>
              <p className="section-label">Financial profile</p>
              <h2>Budget and background</h2>
            </div>
          </div>
          <div className="form-grid">
            <label>
              <span>Budget per year: ${Number(form.budget_per_year).toLocaleString()}</span>
              <input type="range" min="0" max="100000" step="500" value={form.budget_per_year} onChange={(e) => setForm({ ...form, budget_per_year: Number(e.target.value) })} />
            </label>
            <label className="span-2">
              <span>Academic background</span>
              <textarea rows="5" value={form.academic_background} onChange={(e) => setForm({ ...form, academic_background: e.target.value })} placeholder="BSc in Software Engineering" />
            </label>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="profile-step">
          <div className="panel-head">
            <div>
              <p className="section-label">Preferences</p>
              <h2>Where and what to study</h2>
            </div>
          </div>
          <div className="form-grid">
            <label>
              <span>Intended Major</span>
              <input list="major-options" value={form.intended_major} onChange={(e) => setForm({ ...form, intended_major: e.target.value })} placeholder="Computer Science" />
              <datalist id="major-options">
                {majors.map((major) => <option key={major} value={major} />)}
              </datalist>
            </label>
            <label>
              <span>Degree Level</span>
              <select value={form.degree_level} onChange={(e) => setForm({ ...form, degree_level: e.target.value })}>
                {DEGREE_OPTIONS.map((degree) => <option key={degree} value={degree}>{degree}</option>)}
              </select>
            </label>
          </div>

          <div>
            <p className="section-label" style={{ marginBottom: 10 }}>Preferred countries</p>
            {loadingOptions ? (
              <div className="loading-block">Loading countries...</div>
            ) : (
              <div className="checkbox-grid">
                {countries.map((country) => (
                  <label className="checkbox-item" key={country}>
                    <input
                      type="checkbox"
                      checked={selectedCountries.includes(country)}
                      onChange={() => toggleCountry(country)}
                    />
                    <span>{country}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      <div className="profile-actions sticky-actions">
        <Button variant="secondary" disabled={step === 1} onClick={() => setStep((prev) => Math.max(1, prev - 1))}>Back</Button>
        {step < 3 ? (
          <Button onClick={() => setStep((prev) => Math.min(3, prev + 1))}>Next</Button>
        ) : (
          <Button loading={saving} onClick={submit}>Create Profile</Button>
        )}
      </div>
    </div>
  )
}

export default StudentProfileForm