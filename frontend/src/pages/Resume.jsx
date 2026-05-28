import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Button from '../components/Button'
import { profileAPI, resumeAPI } from '../api/client'
import { UploadCloud, FileText, Download, Copy, Trash2, CheckCircle2, AlertCircle } from 'lucide-react'
import ResumeModal from '../components/ResumeModal'
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
  const [rewriteError, setRewriteError] = useState('')

  const [versions, setVersions] = useState([])
  const [versionName, setVersionName] = useState('')
  const [savingVersion, setSavingVersion] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewJob, setPreviewJob] = useState(null)

  useEffect(() => {
    if (location.state?.tab && TABS.includes(location.state.tab)) {
      setTab(location.state.tab)
    }
    if (location.state?.jobDescription) {
      setRewriteJobDescription(location.state.jobDescription)
    }
  }, [location.state])

  useEffect(() => {
    if (resumeText.trim()) return
    const cached = (localStorage.getItem('jobsync_resume_text') || '').trim()
    if (cached) {
      setResumeText(cached)
      return
    }

    ;(async () => {
      try {
        const res = await profileAPI.selected()
        const text = String(res?.data?.profile?.resume_text || '')
        if (!text.trim()) return

        const marker = text.toLowerCase().indexOf('resume text:')
        const extracted = marker >= 0 ? text.slice(marker + 'resume text:'.length).trim() : text.trim()
        if (extracted) {
          setResumeText(extracted)
          localStorage.setItem('jobsync_resume_text', extracted)
        }
      } catch {
        // best-effort prefill only
      }
    })()
  }, [resumeText])

  const loadVersions = async () => {
    try {
      const response = await resumeAPI.listVersions()
      const d = response.data
      setVersions(Array.isArray(d) ? d : (d?.versions || d?.data || []))
    } catch {
      setVersions([])
    }
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
    setRewriteError('')
    try {
      const response = await resumeAPI.rewrite({
        resume_text: resumeText,
        job_description: rewriteJobDescription,
        job_type: jobType,
      })
      setRewriteResult(response.data)
      localStorage.setItem('jobsync_resume_text', response.data?.rewritten || resumeText)
    } catch (error) {
      setRewriteResult(null)
      setRewriteError(error?.userMessage || error?.message || 'Resume rewrite failed. Please try again.')
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

  const openPreview = () => {
    if (!rewriteResult?.rewritten) return
    setPreviewJob({
      title: `${jobType} Resume Preview`,
      company: 'Standalone Resume Builder',
      location: 'Local Preview',
      previewResult: {
        candidate_name: 'Tailored Resume',
        tagline: `${jobType} optimization from the standalone resume page`,
        original_resume: resumeText,
        fixed_resume_text: rewriteResult.rewritten,
        simple_text_version: rewriteResult.rewritten,
        ats_score: score || 0,
        changes_made: rewriteResult.changes_made || [],
        validation_passed: true,
        validation_message: 'Preview generated from the standalone rewrite flow.',
        cached: false,
      },
    })
    setPreviewOpen(true)
  }

  const scoreClass = score < 50 ? 'bad' : score < 76 ? 'ok' : 'good'

  return (
    <div className="resume-page fade-up">
      <div className="page-header">
        <h1>Resume Builder</h1>
        <p className="subtitle">Analyze, rewrite, and manage tailored resume versions.</p>
      </div>

      <div className="resume-tabs">
        <button className={`resume-tab ${tab === 'analyze' ? 'active' : ''}`} onClick={() => setTab('analyze')}>Analyze Fit</button>
        <button className={`resume-tab ${tab === 'rewrite' ? 'active' : ''}`} onClick={() => setTab('rewrite')}>AI Rewrite</button>
        <button className={`resume-tab ${tab === 'versions' ? 'active' : ''}`} onClick={() => setTab('versions')}>My Versions</button>
      </div>

      {tab === 'analyze' && (
        <div className="analyze-grid fade-up">
          <section className="panel-card">
            <span className="field-label">RESUME PDF</span>
            <label className="upload-zone">
              <UploadCloud size={24} color="var(--j-text-3)" />
              <p>{file ? file.name : 'Drop resume PDF here or click to browse'}</p>
              <input type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            </label>
            
            <span className="field-label">TARGET JOB DESCRIPTION</span>
            <textarea
              className="text-area"
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the job description you want to evaluate against..."
              rows={8}
            />
            <Button className="w-full" onClick={analyzeResume} loading={analyzing} disabled={!file}>Generate Analysis</Button>
          </section>

          <section className="panel-card">
            {!analysis ? (
              <div className="empty-results">
                <AlertCircle size={32} />
                <p>Upload a resume and job description to see your ATS match score and skill gaps.</p>
              </div>
            ) : (
              <div className="fade-up">
                <div className="score-display">
                  <div className={`score-circle ${scoreClass}`}>{score}</div>
                  <div className="score-text">
                    <span className="field-label">ATS MATCH SCORE</span>
                    <p>Your resume scores <strong>{score}%</strong> against this job description.</p>
                  </div>
                </div>

                <div className="skills-split">
                  <div>
                    <span className="field-label">MATCHED SKILLS</span>
                    <div className="chip-container">
                      {(analysis.matched_skills || []).map((item) => (
                        <span key={item} className="skill-chip match">{item}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="field-label">MISSING SKILLS</span>
                    <div className="chip-container">
                      {(analysis.missing_keywords || []).map((item) => (
                        <span key={item} className="skill-chip missing">{item}</span>
                      ))}
                    </div>
                  </div>
                </div>

                <span className="field-label">ACTIONABLE FEEDBACK</span>
                <ul className="tips-list">
                  {(analysis.tips || []).map((tip, index) => <li key={`${tip}-${index}`}>{tip}</li>)}
                </ul>
              </div>
            )}
          </section>
        </div>
      )}

      {tab === 'rewrite' && (
        <div className="rewrite-grid fade-up">
          <section className="panel-card">
            <span className="field-label">YOUR RESUME TEXT</span>
            <textarea
              className="text-area"
              rows={10}
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste your current resume content..."
            />
            
            <span className="field-label">TARGET JOB DESCRIPTION</span>
            <textarea
              className="text-area"
              rows={8}
              value={rewriteJobDescription}
              onChange={(event) => setRewriteJobDescription(event.target.value)}
              placeholder="Paste the target job description to optimize for..."
            />
            
            <span className="field-label">OPTIMIZE FOR ROLE TYPE</span>
            <div className="job-types-row">
              {JOB_TYPES.map((type) => (
                <button key={type} className={`type-btn ${jobType === type ? 'active' : ''}`} onClick={() => setJobType(type)}>
                  {type}
                </button>
              ))}
            </div>
            
            <Button className="w-full" onClick={rewriteResume} loading={rewriting}>Rewrite Resume</Button>
          </section>

          <section className="panel-card">
            {!rewriteResult ? (
              <div className="empty-results">
                <FileText size={32} />
                <p>{rewriteError || 'Tailored resume output will appear here after optimization.'}</p>
              </div>
            ) : (
              <div className="fade-up">
                <div className="stats-row">
                  <span className="stat-add">+{rewriteResult.keywords_added?.length || 0} keywords</span>
                  <span className="stat-del">-{rewriteResult.keywords_removed?.length || 0} removed</span>
                  <span className="stat-mod">~{rewriteResult.changes_made?.length || 0} modifications</span>
                </div>
                
                <div className="diff-panels">
                  <div className="diff-col">
                    <h4>ORIGINAL</h4>
                    <div className="diff-content">{resumeText}</div>
                  </div>
                  <div className="diff-col">
                    <h4>REWRITTEN (OPTIMIZED)</h4>
                    <div className="diff-content new">{rewriteResult.rewritten}</div>
                  </div>
                </div>

                <span className="field-label">KEY EXPERT ADJUSTMENTS</span>
                <ul className="changes-list">
                  {(rewriteResult.changes_made || []).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                </ul>

                <div className="action-row">
                  <Button variant="secondary" onClick={() => copyText(rewriteResult.rewritten)}><Copy size={14} style={{ marginRight: 6 }}/> Copy text</Button>
                  <Button variant="secondary" onClick={() => downloadText(rewriteResult.rewritten, 'optimized-resume.txt')}><Download size={14} style={{ marginRight: 6 }}/> Download .txt</Button>
                  <Button variant="secondary" onClick={openPreview}>Open ATS Preview</Button>
                  <Button onClick={() => setShowSaveModal(true)}>Save Version</Button>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {tab === 'versions' && (
        <section className="panel-card fade-up">
          <div className="vc-header">
            <h3>SAVED VERSIONS</h3>
          </div>

          {versions.length === 0 && (
             <div className="empty-results" style={{ minHeight: 200 }}>
               <p>No tailored versions saved yet.</p>
             </div>
          )}

          <div className="versions-grid">
            {versions.map((version) => (
              <article className="version-card" key={version.id}>
                <div className="vc-header">
                  <div>
                    <div className="vc-title">{version.name}</div>
                    <div className="vc-date">{new Date(version.created_at).toLocaleDateString()}</div>
                  </div>
                  <span className="vc-type">{version.job_type}</span>
                </div>
                
                <input
                  className="vc-input"
                  defaultValue={version.used_for || ''}
                  placeholder="Used for: e.g. Acme Corp Application"
                  onBlur={(event) => resumeAPI.updateVersionUsedFor(version.id, event.target.value).then(loadVersions)}
                />
                
                <div className="vc-actions">
                  <span className="vc-ats">ATS Score: {version.ats_score ?? 'N/A'}</span>
                  <div className="vc-btn-group">
                    <button className="icon-action-btn" onClick={() => { setResumeText(version.content); setTab('rewrite'); }} title="Load into editor"><FileText size={14} /></button>
                    <button className="icon-action-btn" onClick={() => copyText(version.content)} title="Copy text"><Copy size={14} /></button>
                    <button
                      className="icon-action-btn del"
                      onClick={async () => {
                        await resumeAPI.deleteVersion(version.id)
                        loadVersions()
                      }}
                      title="Delete version"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {showSaveModal && (
        <div className="save-modal-overlay" onClick={() => setShowSaveModal(false)}>
          <div className="save-modal fade-up" onClick={(event) => event.stopPropagation()}>
            <h3>Save Tailored Version</h3>
            <input
              value={versionName}
              onChange={(event) => setVersionName(event.target.value)}
              placeholder={`${jobType} Version`}
              autoFocus
            />
            <div className="save-modal-actions">
              <Button className="w-full" onClick={() => saveVersion(versionName)} loading={savingVersion}>Save</Button>
              <Button className="w-full" variant="secondary" onClick={() => setShowSaveModal(false)}>Cancel</Button>
            </div>
          </div>
        </div>
      )}

      <ResumeModal
        open={previewOpen}
        job={previewJob}
        onClose={() => {
          setPreviewOpen(false)
          setPreviewJob(null)
        }}
      />
    </div>
  )
}

export default Resume
