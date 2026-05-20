import { useState } from 'react'
import { profileAPI } from '../api/client'

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
      <h1>My Profile</h1>
      <form onSubmit={submit} className="profile-form">
        <label>Skills (comma separated)</label>
        <textarea value={skills} onChange={(e) => setSkills(e.target.value)} />

        <label>Degree</label>
        <input value={degree} onChange={(e) => setDegree(e.target.value)} />

        <label>Years of experience</label>
        <input type="number" value={years} onChange={(e) => setYears(e.target.value)} />

        <label>Interests</label>
        <textarea value={interests} onChange={(e) => setInterests(e.target.value)} />

        <label>Upload resume (PDF or DOCX)</label>
        <input type="file" accept=".pdf,.docx" onChange={(e) => setResumeFile(e.target.files[0])} />

        <button type="submit" disabled={loading}>{loading ? 'Saving...' : 'Save Profile'}</button>
      </form>
      {message && <p className="muted-text">{message}</p>}
    </div>
  )
}
