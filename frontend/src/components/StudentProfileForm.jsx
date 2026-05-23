import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Pencil, Plus, Trash2, Users } from 'lucide-react'
import Button from './Button'
import { studentAPI, getStoredAuthToken } from '../api/client'
import './UniversityModule.css'

const DEGREE_OPTIONS = ['Associate', 'Bachelors', 'Masters', 'MPhil', 'MS', 'MSc', 'MBA', 'PhD', 'Diploma', 'Certificate', 'Short Course']
const FALLBACK_COUNTRIES = ['Malaysia', 'Singapore', 'Germany', 'Japan', 'South Korea', 'China', 'India', 'United Kingdom', 'United States']

function StudentProfileForm({ onCreated }) {
  const navigate = useNavigate()
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [loadingProfiles, setLoadingProfiles] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [countries, setCountries] = useState(FALLBACK_COUNTRIES)
  const [majors, setMajors] = useState([])
  const [step, setStep] = useState(1)
  const [profiles, setProfiles] = useState([])
  const [selectedProfileId, setSelectedProfileId] = useState(0)
  const [editingProfileId, setEditingProfileId] = useState(null)
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

  const resetForm = () => {
    setForm({
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
    setEditingProfileId(null)
    setStep(1)
  }

  const loadProfiles = async () => {
    setLoadingProfiles(true)
    try {
      const response = await studentAPI.listProfiles()
      const payload = response.data || {}
      setProfiles(payload.profiles || [])
      setSelectedProfileId(Number(payload.selected_profile_id || 0))
      if (!editingProfileId && payload.profiles?.length === 0) {
        setStatus('Create your first student profile to start matching.')
      }
    } catch (err) {
      setError(err.userMessage || 'Failed to load student profiles')
      setProfiles([])
    } finally {
      setLoadingProfiles(false)
    }
  }

  const beginEdit = (profile) => {
    setEditingProfileId(profile.id)
    setStep(1)
    setForm({
      gpa: profile.gpa ?? 3.0,
      gre_score: profile.gre_score ?? '',
      toefl_score: profile.toefl_score ?? '',
      ielts_score: profile.ielts_score ?? '',
      budget_per_year: profile.budget_per_year ?? 25000,
      preferred_countries: Array.isArray(profile.preferred_countries) ? profile.preferred_countries : [],
      intended_major: profile.intended_major || '',
      degree_level: profile.degree_level || 'Masters',
      academic_background: profile.academic_background || '',
    })
    setStatus(`Editing profile #${profile.id}`)
  }

  const startNewProfile = () => {
    resetForm()
    setStatus('Ready to create a new student profile.')
  }

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

    loadProfiles()

    return () => {
      mounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    setStatus('')
    setSaving(true)
    // Ensure user is authenticated before attempting to create profile
    if (!getStoredAuthToken()) {
      setError('You must be signed in to create a student profile. Please log in or sign up.')
      setSaving(false)
      return
    }
    try {
      const payload = {
        ...form,
        gpa: Number(form.gpa),
        gre_score: form.gre_score === '' ? null : Number(form.gre_score),
        toefl_score: form.toefl_score === '' ? null : Number(form.toefl_score),
        ielts_score: form.ielts_score === '' ? null : Number(form.ielts_score),
      }
      const response = editingProfileId
        ? await studentAPI.updateProfile(editingProfileId, payload)
        : await studentAPI.createProfile(payload)
      const profileId = Number(response.data?.id || editingProfileId || 0)
      if (!editingProfileId && profileId) {
        onCreated?.(profileId)
        setEditingProfileId(profileId)
      } else if (profileId) {
        onCreated?.(profileId)
      }
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('storage'))
      }
      setStatus(editingProfileId ? 'Profile updated.' : 'Profile created.')
      await loadProfiles()
      if (!editingProfileId && profileId) {
        setSelectedProfileId(profileId)
      }
    } catch (err) {
      setError(err.userMessage || 'Failed to save student profile')
    } finally {
      setSaving(false)
    }
  }

  const selectProfile = async (profileId) => {
    setError('')
    setStatus('')
    try {
      await studentAPI.selectProfile(profileId)
      setSelectedProfileId(profileId)
      onCreated?.(profileId)
      setStatus(`Using profile #${profileId} now.`)
    } catch (err) {
      setError(err.userMessage || 'Failed to switch profile')
    }
  }

  const deleteProfile = async (profileId) => {
    if (!window.confirm('Delete this student profile? Saved programs and applications for it will also be removed.')) {
      return
    }
    setError('')
    setStatus('')
    try {
      const response = await studentAPI.deleteProfile(profileId)
      const nextSelected = Number(response.data?.selected_profile_id || 0)
      if (editingProfileId === profileId) {
        resetForm()
      }
      if (selectedProfileId === profileId) {
        setSelectedProfileId(nextSelected)
        onCreated?.(nextSelected)
      }
      await loadProfiles()
      setStatus(`Profile #${profileId} deleted.`)
    } catch (err) {
      setError(err.userMessage || 'Failed to delete profile')
    }
  }

  const profileCount = profiles.length

  return (
    <div className="study-page">
      <section className="study-hero">
        <div>
          <p className="section-label">Study Mode</p>
          <h1>Student profiles</h1>
          <p className="muted">Create multiple profiles, switch the active one, or edit and delete older versions whenever you need.</p>
        </div>
        <div className="study-hero-actions">
          <span className="study-badge">{profileCount} saved profile{profileCount === 1 ? '' : 's'}</span>
          <Button variant="secondary" onClick={() => navigate('/student/dashboard')}>Open Dashboard</Button>
        </div>
      </section>

      {(error || status) && (
        <div className="study-panel">
          {error && <p className="muted" style={{ color: 'var(--danger)' }}>{error}</p>}
          {!error && status && <p className="muted" style={{ color: 'var(--j-green)' }}>{status}</p>}
        </div>
      )}

      <section className="study-panel">
        <div className="panel-head">
          <div>
            <p className="section-label"><Users size={14} style={{ display: 'inline', marginRight: 6 }} /> SAVED PROFILES</p>
            <h2>Choose one to work with</h2>
          </div>
          <Button variant="secondary" onClick={startNewProfile}><Plus size={14} style={{ display: 'inline', marginRight: 6 }} /> New Profile</Button>
        </div>

        {loadingProfiles ? (
          <div className="loading-block">Loading profiles...</div>
        ) : profiles.length > 0 ? (
          <div className="grid-cols-2">
            {profiles.map((profile) => {
              const isSelected = profile.id === selectedProfileId
              const isEditing = profile.id === editingProfileId
              return (
                <article key={profile.id} className={`study-panel ${isSelected ? 'active' : ''}`}>
                  <div className="panel-head">
                    <div>
                      <p className="section-label">Profile #{profile.id}</p>
                      <h2>{profile.intended_major || 'Untitled profile'}</h2>
                    </div>
                    {isSelected && <span className="study-badge"><CheckCircle2 size={12} style={{ display: 'inline', marginRight: 4 }} /> Active</span>}
                  </div>
                  <p className="muted-small">{profile.degree_level || 'Degree'} · GPA {profile.gpa ?? 'N/A'} · Budget ${Number(profile.budget_per_year || 0).toLocaleString()}</p>
                  <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
                    <Button size="small" variant={isSelected ? 'secondary' : 'primary'} onClick={() => selectProfile(profile.id)} disabled={isSelected}>
                      {isSelected ? 'Selected' : 'Switch to this'}
                    </Button>
                    <Button size="small" variant="secondary" onClick={() => beginEdit(profile)}>
                      <Pencil size={14} style={{ display: 'inline', marginRight: 6 }} /> {isEditing ? 'Editing' : 'Edit'}
                    </Button>
                    <Button size="small" variant="secondary" onClick={() => deleteProfile(profile.id)}>
                      <Trash2 size={14} style={{ display: 'inline', marginRight: 6 }} /> Delete
                    </Button>
                  </div>
                </article>
              )
            })}
          </div>
        ) : (
          <div className="empty-block">
            <div>
              <p className="section-label">No profile found</p>
              <h2>Create your first profile</h2>
              <p>Profiles drive dashboard matches, saved programs, and applications.</p>
            </div>
          </div>
        )}
      </section>

      <section className="profile-progress" aria-hidden="true">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`} />
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`} />
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`} />
      </section>

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
              <input list="degree-options" value={form.degree_level} onChange={(e) => setForm({ ...form, degree_level: e.target.value })} placeholder="Masters" />
              <datalist id="degree-options">
                {DEGREE_OPTIONS.map((degree) => <option key={degree} value={degree} />)}
              </datalist>
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
        <Button variant="secondary" onClick={startNewProfile}>Reset Form</Button>
        <Button variant="secondary" disabled={step === 1} onClick={() => setStep((prev) => Math.max(1, prev - 1))}>Back</Button>
        {step < 3 ? (
          <Button onClick={() => setStep((prev) => Math.min(3, prev + 1))}>Next</Button>
        ) : (
          <Button loading={saving} onClick={submit}>{editingProfileId ? 'Save Changes' : 'Create Profile'}</Button>
        )}
      </div>
    </div>
  )
}

export default StudentProfileForm