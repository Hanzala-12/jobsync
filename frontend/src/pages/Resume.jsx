import { useEffect, useMemo, useState } from 'react'
import { Upload, CheckCircle, AlertCircle, RotateCcw, Clock3, FileSearch, ShieldAlert } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { resumeAPI } from '../api/client'
import './Resume.css'

const HISTORY_KEY = 'jobsync_resume_analysis_history'

const loadHistory = () => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.slice(0, 3) : []
  } catch {
    return []
  }
}

const Resume = () => {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [showReanalysis, setShowReanalysis] = useState(false)
  const [history, setHistory] = useState(loadHistory)

  const scoreClass = useMemo(() => {
    const score = Number(result?.ats_score ?? 0)
    if (score < 50) return 'score-low'
    if (score <= 75) return 'score-medium'
    return 'score-high'
  }, [result])

  const scoreCircleStyle = useMemo(() => {
    const score = Math.max(0, Math.min(Number(result?.ats_score ?? 0), 100))
    let color = '#10b981'
    if (score < 50) color = '#ef4444'
    else if (score <= 75) color = '#f59e0b'
    return {
      background: `conic-gradient(${color} ${score}%, #e2e8f0 ${score}% 100%)`,
    }
  }, [result])

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 3)))
  }, [history])

  const persistAnalysis = (analysis, source, jobDesc = '') => {
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      source,
      jobDesc,
      timestamp: new Date().toISOString(),
      ...analysis,
    }

    setHistory((current) => [entry, ...current].slice(0, 3))
  }

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
      persistAnalysis(response.data, 'Initial upload')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze resume')
    } finally {
      setLoading(false)
    }
  }

  const handleReanalyze = async () => {
    if (!jobDescription.trim()) {
      setError('Please paste a job description first')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await resumeAPI.reanalyze(jobDescription)
      setResult(response.data)
      persistAnalysis(response.data, 'Re-analyze', jobDescription)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to re-analyze resume')
    } finally {
      setLoading(false)
    }
  }

  const applyHistory = (entry) => {
    setResult(entry)
    setJobDescription(entry.jobDesc || '')
    setShowReanalysis(Boolean(entry.jobDesc))
  }

  const copySuggestions = () => {
    if (!result) return
    const content = [
      `Matched Skills:\n${(result.matched_skills || []).join(', ') || 'None'}`,
      `Missing Skills:\n${(result.missing_keywords || []).join(', ') || 'None'}`,
      `Suggestions:\n${(result.tips || []).map((tip, index) => `${index + 1}. ${tip}`).join('\n') || 'None'}`,
    ].join('\n\n')
    navigator.clipboard.writeText(content)
  }

  return (
    <div className="resume-page">
      <div className="page-header">
        <h1>Resume Analysis</h1>
        <p className="page-description">Upload once, compare against different jobs, and keep the last three analyses on hand.</p>
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
              <div className={`score-circle ${scoreClass}`} style={scoreCircleStyle}>
                <div className="score-circle-inner">
                <span className="score-value">{Math.round(result.ats_score)}</span>
                <span className="score-max">/100</span>
                </div>
              </div>
              <p className="score-description">
                {result.ats_score >= 75 ? 'Excellent! Your resume is well-optimized.' :
                 result.ats_score >= 50 ? 'Good, but there is room for improvement.' :
                 'Your resume needs optimization for ATS systems.'}
              </p>
            </div>
          </Card>

          <Card title="Skill Match Snapshot">
            <div className="analysis-grid">
              <section className="analysis-section">
                <div className="section-heading success">
                  <CheckCircle size={18} />
                  <h3>Matched Skills</h3>
                </div>
                <div className="keyword-list matched">
                  {result.matched_skills && result.matched_skills.length > 0 ? (
                    result.matched_skills.map((skill, index) => (
                      <span key={index} className="keyword-tag matched">{skill}</span>
                    ))
                  ) : (
                    <p className="empty-text">No matched skills detected.</p>
                  )}
                </div>
              </section>

              <section className="analysis-section">
                <div className="section-heading danger">
                  <AlertCircle size={18} />
                  <h3>Missing Skills</h3>
                </div>
                <div className="keyword-list missing">
                  {result.missing_keywords && result.missing_keywords.length > 0 ? (
                    result.missing_keywords.map((skill, index) => (
                      <span key={index} className="keyword-tag missing">{skill}</span>
                    ))
                  ) : (
                    <p className="empty-text">No missing skills detected.</p>
                  )}
                </div>
              </section>

              <section className="analysis-section">
                <div className="section-heading accent">
                  <FileSearch size={18} />
                  <h3>Suggestions</h3>
                </div>
                <ol className="suggestions-list">
                  {result.tips && result.tips.length > 0 ? (
                    result.tips.map((tip, index) => <li key={index}>{tip}</li>)
                  ) : (
                    <li>No suggestions available.</li>
                  )}
                </ol>
                <div className="suggestion-actions">
                  <Button onClick={copySuggestions}>Copy Suggestions</Button>
                </div>
              </section>
            </div>
          </Card>

          <Card title="Original Resume Text">
            <div className="resume-diff">
              <div className="resume-original">
                <pre className="resume-text">{result.resume_text || 'No extracted text available.'}</pre>
              </div>
            </div>
          </Card>

          <Card title="Re-analyze Against Different Job">
            <div className="reanalyze-panel">
              <textarea
                className="reanalyze-textarea"
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                rows="8"
                placeholder="Paste a new job description here to compare your stored resume against it..."
              />
              <div className="reanalyze-actions">
                <Button onClick={handleReanalyze} loading={loading}>
                  Re-analyze against different job
                </Button>
                <Button variant="outline" onClick={() => setShowReanalysis((current) => !current)}>
                  {showReanalysis ? 'Hide Job Input' : 'Show Job Input'}
                </Button>
              </div>
            </div>
          </Card>

          {showReanalysis && (
            <Card title="Job Description Input Preview">
              <div className="job-preview">
                {jobDescription ? jobDescription : 'Paste a job description above and click re-analyze.'}
              </div>
            </Card>
          )}

          <Card title="Last 3 Analyses">
            <div className="analysis-history">
              {history.length > 0 ? history.map((entry) => (
                <button key={entry.id} className="analysis-history-item" onClick={() => applyHistory(entry)}>
                  <div>
                    <strong>{entry.source}</strong>
                    <p>{entry.jobDesc ? entry.jobDesc.slice(0, 90) : 'Initial upload'}</p>
                  </div>
                  <div className="history-meta">
                    <span>{Math.round(entry.ats_score)}</span>
                    <small>{new Date(entry.timestamp).toLocaleDateString()}</small>
                  </div>
                </button>
              )) : (
                <div className="empty-history">
                  <ShieldAlert size={20} />
                  <p>No saved analysis history yet.</p>
                </div>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

export default Resume
