import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Button from '../components/Button'
import { resumeAPI } from '../api/client'
import './Resume.css'

const TABS = ['analyze', 'rewrite', 'versions']
const JOB_TYPES = ['General', 'ML/AI', 'Web Dev', 'Mobile', 'Cloud', 'Data', 'DevOps']

function Resume() {
  const location = useLocation()
  const [tab, setTab] = useState('analyze')

  const [file, setFile] = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)

  const [resumeText, setResumeText] = useState('')
  const [rewriteJobDescription, setRewriteJobDescription] = useState('')
  const [jobType, setJobType] = useState('General')
  const [rewriteResult, setRewriteResult] = useState(null)
  const [rewriting, setRewriting] = useState(false)

  const [versions, setVersions] = useState([])
  const [versionName, setVersionName] = useState('')
  const [savingVersion, setSavingVersion] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)

  useEffect(() => {
    if (location.state?.tab && TABS.includes(location.state.tab)) {
      setTab(location.state.tab)
    }
    if (location.state?.jobDescription) {
      setRewriteJobDescription(location.state.jobDescription)
    }
  }, [location.state])

  const loadVersions = async () => {
    const response = await resumeAPI.listVersions()
    setVersions(response.data || [])
  }

  useEffect(() => {
    loadVersions()
  }, [])

  const score = useMemo(() => Math.round(analysis?.ats_score || 0), [analysis])

  const analyzeResume = async () => {
    if (!file) return
    setAnalyzing(true)
    try {
      const result = await resumeAPI.analyze(file)
      setAnalysis(result.data)
      if (result.data?.resume_text) {
        setResumeText(result.data.resume_text)
        localStorage.setItem('jobsync_resume_text', result.data.resume_text)
      }
      if (jobDescription.trim()) {
        const reanalysis = await resumeAPI.reanalyze(jobDescription)
        setAnalysis(reanalysis.data)
      }
    } finally {
      setAnalyzing(false)
    }
  }

  const rewriteResume = async () => {
    setRewriting(true)
    try {
      const response = await resumeAPI.rewrite({
        resume_text: resumeText,
        job_description: rewriteJobDescription,
        job_type: jobType,
      })
      setRewriteResult(response.data)
      localStorage.setItem('jobsync_resume_text', response.data?.rewritten || resumeText)
    } finally {
      setRewriting(false)
    }
  }

  const saveVersion = async (nameOverride = '') => {
    if (!rewriteResult?.rewritten) return
    setSavingVersion(true)
    try {
      await resumeAPI.saveVersion({
        name: nameOverride || versionName || `${jobType} Version`,
        job_type: jobType,
        content: rewriteResult.rewritten,
        ats_score: score || null,
      })
      setVersionName('')
      setShowSaveModal(false)
      await loadVersions()
      setTab('versions')
    } finally {
      setSavingVersion(false)
    }
  }

  const copyText = async (text) => {
    await navigator.clipboard.writeText(text || '')
  }

  const downloadText = (text, name = 'resume.txt') => {
    const blob = new Blob([text || ''], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = name
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="resume-page">
      <div className="page-header">
        <h1>Resume</h1>
        <p className="subtitle">Analyze, rewrite, and manage tailored resume versions.</p>
      </div>

      <div className="tab-bar">
        <button className={tab === 'analyze' ? 'active' : ''} onClick={() => setTab('analyze')}>Analyze</button>
        <button className={tab === 'rewrite' ? 'active' : ''} onClick={() => setTab('rewrite')}>Rewrite</button>
        <button className={tab === 'versions' ? 'active' : ''} onClick={() => setTab('versions')}>My Versions</button>
      </div>

      {tab === 'analyze' && (
        <div className="analyze-grid">
          <section className="card-box">
            <label className="upload-box">
              <input type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} />
              <p>Drop resume or click to upload</p>
            </label>
            <textarea
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste job description"
              rows={10}
            />
            <Button className="full" onClick={analyzeResume} loading={analyzing}>Analyze</Button>
          </section>

          <section className="card-box">
            {!analysis ? (
              <div className="empty-state">Upload a resume to see ATS analysis.</div>
            ) : (
              <>
                <p className="section-label">ATS MATCH SCORE</p>
                <p className="ats-score">{score}</p>
                <div className="score-bar"><span className={score < 50 ? 'score-red' : score < 76 ? 'score-amber' : 'score-green'} style={{ width: `${Math.min(score, 100)}%` }} /></div>

                <div className="skills-grid">
                  <div>
                    <p className="section-label">MATCHED SKILLS</p>
                    <div className="chip-grid">
                      {(analysis.matched_skills || []).map((item) => <span key={item} className="chip good">{item}</span>)}
                    </div>
                  </div>
                  <div>
                    <p className="section-label">MISSING SKILLS</p>
                    <div className="chip-grid">
                      {(analysis.missing_keywords || []).map((item) => <span key={item} className="chip bad">{item}</span>)}
                    </div>
                  </div>
                </div>

                <p className="section-label">SUGGESTIONS</p>
                <ol className="tips-list">
                  {(analysis.tips || []).map((tip, index) => <li key={`${tip}-${index}`}>{tip}</li>)}
                </ol>
              </>
            )}
          </section>
        </div>
      )}

      {tab === 'rewrite' && (
        <div className="rewrite-grid">
          <section className="card-box">
            <p className="section-label">YOUR RESUME</p>
            <textarea
              rows={12}
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste your resume text"
            />
            <p className="section-label">JOB DESCRIPTION</p>
            <textarea
              rows={10}
              value={rewriteJobDescription}
              onChange={(event) => setRewriteJobDescription(event.target.value)}
              placeholder="Paste target job description"
            />
            <p className="section-label">JOB TYPE</p>
            <div className="type-row">
              {JOB_TYPES.map((type) => (
                <button key={type} className={jobType === type ? 'type active' : 'type'} onClick={() => setJobType(type)}>
                  {type}
                </button>
              ))}
            </div>
            <Button className="full" onClick={rewriteResume} loading={rewriting}>Rewrite My Resume</Button>
          </section>

          <section className="card-box">
            {!rewriteResult ? (
              <div className="empty-state">AI rewrite output will appear here.</div>
            ) : (
              <>
                <p className="stats-text">
                  <span className="kpi-good">{rewriteResult.keywords_added?.length || 0} keywords added</span>
                  <span>{rewriteResult.keywords_removed?.length || 0} removed</span>
                  <span className="kpi-accent">{rewriteResult.changes_made?.length || 0} changes</span>
                </p>
                <div className="text-panels">
                  <div>
                    <p className="section-label">ORIGINAL</p>
                    <pre>{resumeText}</pre>
                  </div>
                  <div>
                    <p className="section-label">REWRITTEN</p>
                    <pre className="rewritten">{rewriteResult.rewritten}</pre>
                  </div>
                </div>

                <p className="section-label">CHANGES MADE</p>
                <ul className="plain-list">
                  {(rewriteResult.changes_made || []).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                </ul>

                <p className="section-label">KEYWORDS ADDED</p>
                <div className="chip-grid">
                  {(rewriteResult.keywords_added || []).map((item) => <span key={item} className="chip good">{item}</span>)}
                </div>

                <div className="button-row">
                  <Button variant="secondary" onClick={() => copyText(rewriteResult.rewritten)}>Copy</Button>
                  <Button variant="secondary" onClick={() => downloadText(rewriteResult.rewritten, 'rewritten-resume.txt')}>Download .txt</Button>
                  <Button variant="secondary" onClick={() => setShowSaveModal(true)}>Save as Version</Button>
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {tab === 'versions' && (
        <section className="card-box">
          <div className="versions-head">
            <h3>SAVED VERSIONS ({versions.length})</h3>
            <Button variant="secondary" size="small" onClick={() => setShowSaveModal(true)}>Save New Version</Button>
          </div>

          {versions.length === 0 && <p className="empty-state">No saved versions yet.</p>}

          <div className="versions-list">
            {versions.map((version) => (
              <article className="version-card" key={version.id}>
                <div>
                  <p className="name">{version.name}</p>
                  <span className="job-type">{version.job_type}</span>
                </div>
                <div>
                  <p>{new Date(version.created_at).toLocaleDateString()}</p>
                  <input
                    defaultValue={version.used_for || ''}
                    placeholder="Used for: Company"
                    onBlur={(event) => resumeAPI.updateVersionUsedFor(version.id, event.target.value).then(loadVersions)}
                  />
                </div>
                <div className="actions">
                  <span className="ats">ATS {version.ats_score ?? '-'}</span>
                  <Button size="small" variant="secondary" onClick={() => setResumeText(version.content)}>Load</Button>
                  <Button size="small" variant="secondary" onClick={() => copyText(version.content)}>Copy</Button>
                  <Button
                    size="small"
                    variant="secondary"
                    onClick={async () => {
                      await resumeAPI.deleteVersion(version.id)
                      loadVersions()
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {showSaveModal && (
        <div className="modal-overlay" onClick={() => setShowSaveModal(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Save Version</h3>
            <input
              value={versionName}
              onChange={(event) => setVersionName(event.target.value)}
              placeholder={`${jobType} Version`}
            />
            <div className="modal-actions">
              <Button onClick={() => saveVersion(versionName)} loading={savingVersion}>Save</Button>
              <Button variant="secondary" onClick={() => setShowSaveModal(false)}>Cancel</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Resume
