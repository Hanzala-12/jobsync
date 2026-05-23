import { useState, useEffect } from 'react'
import { profileAPI } from '../api/client'
import Button from '../components/Button'
import { FileUp, UserCircle, Edit2, Trash2, CheckCircle2 } from 'lucide-react'
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
  const [pageSize] = useState(4)
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
        setMessage(res.data?.message || 'Profile updated successfully')
      } else {
        res = await profileAPI.create(fd)
        setMessage(res.data?.message || 'Profile created successfully')
        const newId = res.data?.id
        if (newId) {
          try { await profileAPI.select(newId); setSelectedId(newId) } catch (e) { /* ignore */ }
        }
      }
      await loadProfiles()
      
      // Keep form loaded if edited, or clear if created
      if (!editingProfileId) {
        setSkills('')
        setDegree('')
        setYears(0)
        setInterests('')
        setResumeFile(null)
      }
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

  useEffect(() => { loadProfiles() }, [pageIndex])

  const handleSelect = async (id) => {
    try {
      await profileAPI.select(id)
      setSelectedId(id)
      setMessage('Active profile updated')
    } catch (e) {
      setMessage('Failed to set active profile')
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this profile permanently?')) return
    try {
      await profileAPI.delete(id)
      setMessage('Profile deleted')
      await loadProfiles()
      if (selectedId === id) setSelectedId(null)
      if (editingProfileId === id) {
        setEditingProfileId(null)
        setSkills('')
        setDegree('')
        setYears(0)
        setInterests('')
      }
    } catch (e) {
      setMessage('Failed to delete profile')
    }
  }

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
          setEditingProfileId(p.id)
          setMessage('Loaded profile for editing')
        }
      } catch (e) {
        setMessage('Failed to load profile details')
      }
    })()
  }

  const clearForm = () => {
    setEditingProfileId(null)
    setSkills('')
    setDegree('')
    setYears(0)
    setInterests('')
    setResumeFile(null)
    setMessage('')
  }

  return (
    <div className="profile-page fade-up">
      <div className="page-header">
        <h1>My Profile</h1>
        <p className="subtitle">Manage your background information to get better job matches.</p>
      </div>

      <div className="profile-layout">
        <form className="profile-card fade-up" onSubmit={submit}>
          <h3>{editingProfileId ? 'Edit Profile' : 'Create New Profile'}</h3>
          
          <div className="form-group">
            <label className="field-label">Domain Skills</label>
            <textarea 
              className="field-input" 
              rows={3}
              value={skills} 
              onChange={(e) => setSkills(e.target.value)} 
              placeholder="e.g. React, Node.js, System Design..."
            />
          </div>

          <div className="form-group row">
            <div>
              <label className="field-label">Degree / Education</label>
              <input className="field-input" value={degree} onChange={(e) => setDegree(e.target.value)} placeholder="e.g. BS Computer Science" />
            </div>
            <div>
              <label className="field-label">Years Exp.</label>
              <input className="field-input" type="number" value={years} onChange={(e) => setYears(e.target.value)} min={0} />
            </div>
          </div>

          <div className="form-group">
            <label className="field-label">Career Interests</label>
            <textarea 
              className="field-input" 
              rows={2}
              value={interests} 
              onChange={(e) => setInterests(e.target.value)} 
              placeholder="e.g. Fintech, Open Source..."
            />
          </div>

          <div className="form-group">
            <span className="field-label">Base Resume (Optional)</span>
            <label className="file-upload-lbl">
              <FileUp size={20} color="var(--j-text-3)" />
              <p>{resumeFile ? resumeFile.name : 'Upload PDF or DOCX'}</p>
              <input type="file" accept=".pdf,.docx" onChange={(e) => setResumeFile(e.target.files[0])} />
            </label>
          </div>

          <div className="form-actions">
            <Button type="submit" loading={loading}>{editingProfileId ? 'Update Profile' : 'Save Profile'}</Button>
            {editingProfileId && (
              <Button type="button" variant="secondary" onClick={clearForm}>Cancel Edit</Button>
            )}
          </div>

          {message && <div className="status-msg">{message}</div>}
        </form>

        <div className="profile-card fade-up">
          <h3>Saved Profiles</h3>
          
          <div className="saved-profiles-list">
            {profiles.length === 0 ? (
              <p className="status-msg">No profiles saved yet. Create one to get started.</p>
            ) : (
              profiles.map(p => (
                <div key={p.id} className={`saved-profile-card ${selectedId === p.id ? 'active' : ''}`}>
                  <div className="sp-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <UserCircle size={16} color="var(--j-text-2)" />
                      <span className="sp-title">Profile #{p.id}</span>
                    </div>
                    {selectedId === p.id && <span className="sp-badge">Active</span>}
                  </div>
                  
                  <div className="sp-body">
                    {p.skills && <p><strong>Skills:</strong> {p.skills}</p>}
                    {(p.degree || p.years_experience) && <p>{p.degree || 'No degree'} • {p.years_experience || 0} yrs exp</p>}
                  </div>
                  
                  <div className="sp-actions">
                    {selectedId !== p.id && (
                      <button className="sel" type="button" onClick={() => handleSelect(p.id)}>
                        <CheckCircle2 size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'text-bottom' }}/> Set Active
                      </button>
                    )}
                    <button type="button" onClick={() => handleEdit(p)}>
                      <Edit2 size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'text-bottom' }}/> Edit
                    </button>
                    <button className="del" type="button" onClick={() => handleDelete(p.id)}>
                      <Trash2 size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'text-bottom' }}/> Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {totalProfiles > pageSize && (
            <div className="pager-ctrl">
              <span className="pager-muted">Page {pageIndex} of {Math.ceil(totalProfiles / pageSize)}</span>
              <div className="pager-btns">
                <button disabled={pageIndex === 1} onClick={() => setPageIndex(p => Math.max(1, p - 1))}>Prev</button>
                <button disabled={pageIndex * pageSize >= totalProfiles} onClick={() => setPageIndex(p => p + 1)}>Next</button>
              </div>
            </div>
          )}

          {previewText && (
            <div className="preview-box fade-up">
              <span className="field-label">ACTIVE PROfILE RESUME TEXT</span>
              <div className="preview-content">{previewText}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
