import { useState } from 'react'
import { FileText } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { coverLetterAPI } from '../api/client'
import './CoverLetter.css'

const CoverLetter = () => {
  const [formData, setFormData] = useState({
    company: '',
    role: '',
    job_description: ''
  })
  const [coverLetter, setCoverLetter] = useState('')
  const [loading, setLoading] = useState(false)

  const handleGenerate = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await coverLetterAPI.generate(formData)
      setCoverLetter(response.data.draft)
    } catch (error) {
      console.error('Failed to generate cover letter:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="cover-letter-page">
      <div className="page-header">
        <h1>Cover Letter Generator</h1>
        <p className="page-description">Generate tailored cover letters with AI</p>
      </div>

      <Card title="Job Details">
        <form onSubmit={handleGenerate} className="cover-letter-form">
          <div className="form-group">
            <label>Company</label>
            <input
              type="text"
              value={formData.company}
              onChange={(e) => setFormData({...formData, company: e.target.value})}
              required
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label>Role</label>
            <input
              type="text"
              value={formData.role}
              onChange={(e) => setFormData({...formData, role: e.target.value})}
              required
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label>Job Description</label>
            <textarea
              value={formData.job_description}
              onChange={(e) => setFormData({...formData, job_description: e.target.value})}
              rows="6"
              required
              className="form-input"
            />
          </div>
          <Button type="submit" loading={loading}>
            <FileText size={20} />
            Generate Cover Letter
          </Button>
        </form>
      </Card>

      {coverLetter && (
        <Card title="Generated Cover Letter">
          <div className="cover-letter-output">
            <pre>{coverLetter}</pre>
            <Button onClick={() => navigator.clipboard.writeText(coverLetter)}>
              Copy to Clipboard
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}

export default CoverLetter
