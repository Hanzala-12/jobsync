import { useState, useEffect } from 'react'
import { profileAPI } from '../api/client'
import './Profile.css'

export default function Profile() {
  const [skills, setSkills] = useState('')
  const [degree, setDegree] = useState('')
  const [years, setYears] = useState(0)
  const [interests, setInterests] = useState('')
  const [resumeFile, setResumeFile] = useState(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [profiles, setProfiles] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [editingProfileId, setEditingProfileId] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    try {
      const fd = new FormData()
      fd.append('skills', skills)
      fd.append('degree', degree)
      fd.append('years_experience', String(years))
      fd.append('interests', interests)
      if (resumeFile) fd.append('resume', resumeFile)
      const res = await profileAPI.create(fd)
      setMessage(res.data?.message || 'Profile saved')
      // if backend returned created id, select it
      const newId = res.data?.id
      if (newId) {
        try { await profileAPI.select(newId); setSelectedId(newId) } catch (e) { /* ignore */ }
      }
      // refresh profiles list
      await loadProfiles()
      // if created, clear form
      setSkills('')
      setDegree('')
      setYears(0)
      setInterests('')
      setResumeFile(null)
      setEditingProfileId(null)
    } catch (err) {
      setMessage('Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  const loadProfiles = async () => {
    try {
      const res = await profileAPI.exists()
      const data = res.data || {}
      setProfiles(data.profiles || [])
      setSelectedId(data.selected_profile_id || null)
    } catch (e) {
      setProfiles([])
    }
  }

  useEffect(() => {
    loadProfiles()
  }, [])

  const handleSelect = async (id) => {
    try {
      await profileAPI.select(id)
      setSelectedId(id)
      setMessage('Selected profile ' + id)
    } catch (e) {
      setMessage('Failed to select profile')
    }
  }

  const handleEdit = (p) => {
    // Pre-fill fields for editing (best-effort)
    setSkills(p.skills || '')
    setEditingProfileId(p.id)
    setMessage('Editing profile ' + p.id + '. Saving will create a new profile version.')
  }

  return (
    <div className="profile-page">
      <div className="page-header">
        <h1>My Profile</h1>
        <p className="subtitle">Tell us about your background so we can match jobs better.</p>
      </div>

      <form onSubmit={submit} className="profile-form">
          <div className="profiles-list">
            {profiles.length === 0 ? (
              <div className="profiles-empty">No saved profiles</div>
            ) : (
              profiles.map((p) => (
                <div key={p.id} className={"profile-item" + (selectedId === p.id ? ' active' : '')}>
                  <div className="profile-meta">
                    <strong>Profile {p.id}</strong>
                    <div className="profile-skills">{p.skills}</div>
                  </div>
                  <div className="profile-actions">
                    <button type="button" className="btn" onClick={() => handleSelect(p.id)}>{selectedId === p.id ? 'Selected' : 'Select'}</button>
                    <button type="button" className="btn" onClick={() => handleEdit(p)}>Edit</button>
                  </div>
                </div>
              ))
            )}
          </div>
        <div className="form-row">
          <label className="field-label">Skills (comma separated)</label>
          <textarea className="field-input" value={skills} onChange={(e) => setSkills(e.target.value)} />
        </div>

        <div className="form-row two-col">
          <div className="col">
            <label className="field-label">Degree</label>
            <input className="field-input" value={degree} onChange={(e) => setDegree(e.target.value)} />
          </div>
          <div className="col">
            <label className="field-label">Years of experience</label>
            <input className="field-input" type="number" value={years} onChange={(e) => setYears(e.target.value)} />
          </div>
        </div>

        <div className="form-row">
          <label className="field-label">Interests</label>
          <textarea className="field-input" value={interests} onChange={(e) => setInterests(e.target.value)} />
        </div>

        <div className="form-row">
          <label className="field-label">Upload resume (PDF or DOCX)</label>
          <input className="field-input file-input" type="file" accept=".pdf,.docx" onChange={(e) => setResumeFile(e.target.files[0])} />
        </div>

        <div className="form-row actions">
          <button className="btn primary" type="submit" disabled={loading}>{loading ? 'Saving...' : 'Save Profile'}</button>
        </div>
      </form>

      {message && <p className="muted-text message">{message}</p>}
    </div>
  )
}
