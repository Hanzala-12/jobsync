import { useState } from 'react'
import { Upload, CheckCircle, AlertCircle } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { resumeAPI } from '../api/client'
import './Resume.css'

const Resume = () => {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setError(null)
    } else {
      setError('Please select a PDF file')
      setFile(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await resumeAPI.analyze(file)
      setResult(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze resume')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="resume-page">
      <div className="page-header">
        <h1>Resume Analysis</h1>
        <p className="page-description">Upload your resume to get ATS score and improvement tips</p>
      </div>

      <Card title="Upload Resume">
        <div className="upload-section">
          <div className="file-input-wrapper">
            <input
              type="file"
              id="resume-file"
              accept=".pdf"
              onChange={handleFileChange}
              className="file-input"
            />
            <label htmlFor="resume-file" className="file-label">
              <Upload size={24} />
              <span>{file ? file.name : 'Choose PDF file'}</span>
            </label>
          </div>

          {error && (
            <div className="alert alert-error">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          <Button 
            onClick={handleUpload} 
            disabled={!file || loading}
            loading={loading}
          >
            Analyze Resume
          </Button>
        </div>
      </Card>

      {result && (
        <>
          <Card title="ATS Score" className="score-card">
            <div className="score-display">
              <div className="score-circle">
                <span className="score-value">{result.ats_score}</span>
                <span className="score-max">/100</span>
              </div>
              <p className="score-description">
                {result.ats_score >= 80 ? 'Excellent! Your resume is well-optimized.' :
                 result.ats_score >= 60 ? 'Good, but there is room for improvement.' :
                 'Your resume needs optimization for ATS systems.'}
              </p>
            </div>
          </Card>

          {result.missing_keywords.length > 0 && (
            <Card title="Missing Keywords">
              <div className="keywords-list">
                {result.missing_keywords.map((keyword, index) => (
                  <span key={index} className="keyword-tag">{keyword}</span>
                ))}
              </div>
            </Card>
          )}

          {result.tips.length > 0 && (
            <Card title="Improvement Tips">
              <ul className="tips-list">
                {result.tips.map((tip, index) => (
                  <li key={index} className="tip-item">
                    <CheckCircle size={20} className="tip-icon" />
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

export default Resume
