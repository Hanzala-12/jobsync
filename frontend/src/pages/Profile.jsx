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
  const [previewText, setPreviewText] = useState('')
  const [pageIndex, setPageIndex] = useState(1)
  const [pageSize] = useState(6)
  const [totalProfiles, setTotalProfiles] = useState(0)

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
      let res
      if (editingProfileId) {
        res = await profileAPI.update(editingProfileId, fd)
        setMessage(res.data?.message || 'Profile updated')
      } else {
        res = await profileAPI.create(fd)
        setMessage(res.data?.message || 'Profile saved')
        // if backend returned created id, select it
        const newId = res.data?.id
        if (newId) {
          try { await profileAPI.select(newId); setSelectedId(newId) } catch (e) { /* ignore */ }
        }
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
      const res = await profileAPI.list(pageIndex, pageSize)
      const data = res.data || {}
      setProfiles(data.profiles || [])
      setSelectedId(data.selected_profile_id || null)
      setTotalProfiles(data.total || 0)
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

  const handleDelete = async (id) => {
    if (!window.confirm('Delete profile?')) return
    try {
      await profileAPI.delete(id)
      setMessage('Deleted profile ' + id)
      // reload current page
      await loadProfiles()
      if (selectedId === id) setSelectedId(null)
    } catch (e) {
      setMessage('Failed to delete')
    }
  }

  useEffect(() => { loadProfiles() }, [pageIndex])

  // parse stored resume_text to prefill fields when editing
  const parseProfileText = (text) => {
    const out = { skills: '', degree: '', years: '', interests: '', resume: '' }
    if (!text) return out
    const lines = text.split(/\r?\n/)
    let captureResume = false
    const resumeParts = []
    for (const line of lines) {
      const l = line.trim()
      if (!l) continue
      if (l.toLowerCase().startsWith('skills:')) out.skills = l.substring(7).trim()
      else if (l.toLowerCase().startsWith('degree:')) out.degree = l.substring(7).trim()
      else if (l.toLowerCase().startsWith('years experience:')) out.years = l.substring(17).trim()
      else if (l.toLowerCase().startsWith('interests:')) out.interests = l.substring(10).trim()
      else if (l.toLowerCase().startsWith('resume text:')) { captureResume = true; resumeParts.push(l.substring(12).trim()) }
      else if (captureResume) resumeParts.push(l)
    }
    out.resume = resumeParts.join('\n')
    return out
  }

  // fetch and show full profile on selection (preview)
  useEffect(() => {
    if (!selectedId) {
      setPreviewText('')
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const res = await profileAPI.get(selectedId)
        if (mounted && res && res.data) setPreviewText(res.data.resume_text || '')
      } catch (e) {
        if (mounted) setPreviewText('')
      }
    })()
    return () => { mounted = false }
  }, [selectedId])

  const handleEdit = (p) => {
    ;(async () => {
      try {
        const res = await profileAPI.get(p.id)
        if (res && res.data) {
          const parsed = parseProfileText(res.data.resume_text || '')
          setSkills(parsed.skills || '')
          setDegree(parsed.degree || '')
          setYears(parsed.years || 0)
          setInterests(parsed.interests || '')
          setPreviewText(parsed.resume || '')
          setEditingProfileId(p.id)
          setMessage('Editing profile ' + p.id)
        }
      } catch (e) {
        setMessage('Failed to load profile for editing')
      }
    })()
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
                    <button type="button" className="btn" onClick={() => handleDelete(p.id)}>Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="profiles-pager" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
            <div>
              <button className="btn" type="button" onClick={() => setPageIndex(Math.max(1, pageIndex - 1))}>Previous</button>
              <button className="btn" type="button" onClick={() => setPageIndex(pageIndex + 1)} style={{ marginLeft: 8 }}>Next</button>
            </div>
            <div className="muted-text">Page {pageIndex} · {totalProfiles} profiles</div>
          </div>
          {previewText && (
            <div className="profile-preview" style={{ marginTop: 12 }}>
              <h4>Resume Preview</h4>
              <div style={{ whiteSpace: 'pre-wrap', background: 'white', padding: 12, borderRadius: 8, border: '1px solid var(--border)' }}>{previewText}</div>
            </div>
          )}
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
