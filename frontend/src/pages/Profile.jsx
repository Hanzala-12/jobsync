import { useState } from 'react'
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
    } catch (err) {
      setMessage('Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="profile-page">
      <div className="page-header">
        <h1>My Profile</h1>
        <p className="subtitle">Tell us about your background so we can match jobs better.</p>
      </div>

      <form onSubmit={submit} className="profile-form">
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
