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
    <div className="resume-page fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        className="app-card"
        style={{
          padding: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Resume Workspace</p>
          <h1 style={{ marginTop: 6 }}>Resume Builder</h1>
          <p className="subtitle">Analyze, rewrite, and manage tailored resume versions.</p>
        </div>
        <div style={{ minWidth: 240, padding: 16, borderRadius: 16, background: 'linear-gradient(135deg, rgba(58,87,232,0.10), rgba(16,185,129,0.08))', border: '1px solid rgba(58,87,232,0.12)' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Workspace modes</div>
          <p style={{ margin: '8px 0 0', color: 'var(--j-text-2)', lineHeight: 1.6 }}>Move between analysis, rewriting, and version management without leaving the page.</p>
        </div>
      </section>

      <div
        className="resume-tabs"
        style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: 8, borderRadius: 18, background: 'var(--j-surface)', border: '1px solid var(--j-border)', boxShadow: 'var(--j-shadow-sm)' }}
      >
        <button type="button" className={`resume-tab ${tab === 'analyze' ? 'active' : ''}`} onClick={() => setTab('analyze')} style={{ minHeight: 42, padding: '0 16px', borderRadius: 14, border: tab === 'analyze' ? '1px solid rgba(58,87,232,0.18)' : '1px solid transparent', background: tab === 'analyze' ? 'rgba(58,87,232,0.10)' : 'transparent', color: tab === 'analyze' ? 'var(--j-accent)' : 'var(--j-text-2)', fontWeight: 700 }}>Analyze Fit</button>
        <button type="button" className={`resume-tab ${tab === 'rewrite' ? 'active' : ''}`} onClick={() => setTab('rewrite')} style={{ minHeight: 42, padding: '0 16px', borderRadius: 14, border: tab === 'rewrite' ? '1px solid rgba(58,87,232,0.18)' : '1px solid transparent', background: tab === 'rewrite' ? 'rgba(58,87,232,0.10)' : 'transparent', color: tab === 'rewrite' ? 'var(--j-accent)' : 'var(--j-text-2)', fontWeight: 700 }}>AI Rewrite</button>
        <button type="button" className={`resume-tab ${tab === 'versions' ? 'active' : ''}`} onClick={() => setTab('versions')} style={{ minHeight: 42, padding: '0 16px', borderRadius: 14, border: tab === 'versions' ? '1px solid rgba(58,87,232,0.18)' : '1px solid transparent', background: tab === 'versions' ? 'rgba(58,87,232,0.10)' : 'transparent', color: tab === 'versions' ? 'var(--j-accent)' : 'var(--j-text-2)', fontWeight: 700 }}>My Versions</button>
      </div>

      {tab === 'analyze' && (
        <div className="analyze-grid fade-up" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 0.9fr) minmax(0, 1.1fr)', gap: 20, alignItems: 'start' }}>
          <section className="panel-card" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Resume PDF</span>
            <label className="upload-zone" style={{ borderRadius: 16, border: '1px dashed var(--j-border)', background: 'var(--j-surface-2)', padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, minHeight: 160, cursor: 'pointer' }}>
              <UploadCloud size={24} color="var(--j-text-3)" />
              <p style={{ margin: 0, color: 'var(--j-text-2)' }}>{file ? file.name : 'Drop resume PDF here or click to browse'}</p>
              <input type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            </label>

            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Target Job Description</span>
            <textarea
              className="text-area"
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the job description you want to evaluate against..."
              rows={8}
              style={{ borderRadius: 16 }}
            />
            <Button className="w-full" onClick={analyzeResume} loading={analyzing} disabled={!file}>Generate Analysis</Button>
          </section>

          <section className="panel-card" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', minHeight: 320 }}>
            {!analysis ? (
              <div className="empty-results" style={{ minHeight: 320, borderRadius: 16, background: 'var(--j-surface-2)', border: '1px dashed var(--j-border)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
                <AlertCircle size={32} />
                <p style={{ color: 'var(--j-text-2)' }}>Upload a resume and job description to see your ATS match score and skill gaps.</p>
              </div>
            ) : (
              <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div className="score-display" style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 16, borderRadius: 16, background: 'var(--j-surface-2)', border: '1px solid var(--j-border)' }}>
                  <div className={`score-circle ${scoreClass}`} style={{ width: 88, height: 88, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 24, fontWeight: 800, background: 'linear-gradient(135deg, var(--j-accent), var(--j-accent-2))', color: '#fff' }}>{score}</div>
                  <div className="score-text">
                    <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>ATS Match Score</span>
                    <p style={{ marginTop: 6, color: 'var(--j-text-2)' }}>Your resume scores <strong style={{ color: 'var(--j-text-1)' }}>{score}%</strong> against this job description.</p>
                  </div>
                </div>

                <div className="skills-split" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 16 }}>
                  <div style={{ padding: 16, borderRadius: 16, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)' }}>
                    <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Matched Skills</span>
                    <div className="chip-container" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                      {(analysis.matched_skills || []).map((item) => (
                        <span key={item} className="skill-chip match" style={{ padding: '8px 10px', borderRadius: 999, background: 'rgba(16,185,129,0.10)', color: '#047857', fontWeight: 700 }}>{item}</span>
                      ))}
                    </div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 16, border: '1px solid var(--j-border)', background: 'var(--j-surface-2)' }}>
                    <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Missing Skills</span>
                    <div className="chip-container" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                      {(analysis.missing_keywords || []).map((item) => (
                        <span key={item} className="skill-chip missing" style={{ padding: '8px 10px', borderRadius: 999, background: 'rgba(239,68,68,0.10)', color: '#b91c1c', fontWeight: 700 }}>{item}</span>
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Actionable Feedback</span>
                  <ul className="tips-list" style={{ marginTop: 12, display: 'grid', gap: 10, paddingLeft: 18, color: 'var(--j-text-2)' }}>
                    {(analysis.tips || []).map((tip, index) => <li key={`${tip}-${index}`}>{tip}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {tab === 'rewrite' && (
        <div className="rewrite-grid fade-up" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 0.95fr) minmax(0, 1.05fr)', gap: 20, alignItems: 'start' }}>
          <section className="panel-card" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Your Resume Text</span>
            <textarea
              className="text-area"
              rows={10}
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste your current resume content..."
              style={{ borderRadius: 16 }}
            />

            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Target Job Description</span>
            <textarea
              className="text-area"
              rows={8}
              value={rewriteJobDescription}
              onChange={(event) => setRewriteJobDescription(event.target.value)}
              placeholder="Paste the target job description to optimize for..."
              style={{ borderRadius: 16 }}
            />

            <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Optimize for Role Type</span>
            <div className="job-types-row" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {JOB_TYPES.map((type) => (
                <button key={type} type="button" className={`type-btn ${jobType === type ? 'active' : ''}`} onClick={() => setJobType(type)} style={{ minHeight: 38, padding: '0 14px', borderRadius: 999, border: jobType === type ? '1px solid rgba(58,87,232,0.18)' : '1px solid var(--j-border)', background: jobType === type ? 'rgba(58,87,232,0.10)' : 'var(--j-surface-2)', color: jobType === type ? 'var(--j-accent)' : 'var(--j-text-2)', fontWeight: 700 }}>{type}</button>
              ))}
            </div>

            <Button className="w-full" onClick={rewriteResume} loading={rewriting}>Rewrite Resume</Button>
          </section>

          <section className="panel-card" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)', minHeight: 320 }}>
            {!rewriteResult ? (
              <div className="empty-results" style={{ minHeight: 320, borderRadius: 16, background: 'var(--j-surface-2)', border: '1px dashed var(--j-border)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
                <FileText size={32} />
                <p style={{ color: 'var(--j-text-2)' }}>{rewriteError || 'Tailored resume output will appear here after optimization.'}</p>
              </div>
            ) : (
              <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div className="stats-row" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  <span className="stat-add" style={{ padding: '8px 10px', borderRadius: 999, background: 'rgba(16,185,129,0.10)', color: '#047857', fontWeight: 700 }}>+{rewriteResult.keywords_added?.length || 0} keywords</span>
                  <span className="stat-del" style={{ padding: '8px 10px', borderRadius: 999, background: 'rgba(239,68,68,0.10)', color: '#b91c1c', fontWeight: 700 }}>-{rewriteResult.keywords_removed?.length || 0} removed</span>
                  <span className="stat-mod" style={{ padding: '8px 10px', borderRadius: 999, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700 }}>~{rewriteResult.changes_made?.length || 0} modifications</span>
                </div>

                <div className="diff-panels" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 16 }}>
                  <div className="diff-col" style={{ border: '1px solid var(--j-border)', borderRadius: 16, background: 'var(--j-surface-2)', overflow: 'hidden' }}>
                    <h4 style={{ margin: 0, padding: '14px 16px', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)', borderBottom: '1px solid var(--j-border)' }}>Original</h4>
                    <div className="diff-content" style={{ padding: 16, whiteSpace: 'pre-wrap', lineHeight: 1.7, color: 'var(--j-text-2)' }}>{resumeText}</div>
                  </div>
                  <div className="diff-col" style={{ border: '1px solid rgba(58,87,232,0.18)', borderRadius: 16, background: 'rgba(58,87,232,0.05)', overflow: 'hidden' }}>
                    <h4 style={{ margin: 0, padding: '14px 16px', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-accent)', borderBottom: '1px solid rgba(58,87,232,0.12)' }}>Rewritten (Optimized)</h4>
                    <div className="diff-content new" style={{ padding: 16, whiteSpace: 'pre-wrap', lineHeight: 1.7, color: 'var(--j-text-1)' }}>{rewriteResult.rewritten}</div>
                  </div>
                </div>

                <div>
                  <span className="field-label" style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--j-text-3)' }}>Key Expert Adjustments</span>
                  <ul className="changes-list" style={{ marginTop: 12, display: 'grid', gap: 10, paddingLeft: 18, color: 'var(--j-text-2)' }}>
                    {(rewriteResult.changes_made || []).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                  </ul>
                </div>

                <div className="action-row" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
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
        <section className="panel-card fade-up" style={{ background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-sm)' }}>
          <div className="vc-header" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--j-text-1)' }}>Saved Versions</h3>
          </div>

          {versions.length === 0 && (
             <div className="empty-results" style={{ minHeight: 200, borderRadius: 16, background: 'var(--j-surface-2)', border: '1px dashed var(--j-border)' }}>
               <p style={{ color: 'var(--j-text-2)' }}>No tailored versions saved yet.</p>
             </div>
          )}

          <div className="versions-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginTop: 16 }}>
            {versions.map((version) => (
              <article className="version-card" key={version.id} style={{ border: '1px solid var(--j-border)', borderRadius: 16, padding: 16, background: 'var(--j-surface-2)', display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="vc-header" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                  <div>
                    <div className="vc-title" style={{ fontSize: 16, fontWeight: 800, color: 'var(--j-text-1)' }}>{version.name}</div>
                    <div className="vc-date" style={{ fontSize: 13, color: 'var(--j-text-2)', marginTop: 4 }}>{new Date(version.created_at).toLocaleDateString()}</div>
                  </div>
                  <span className="vc-type" style={{ padding: '6px 10px', borderRadius: 999, background: 'rgba(58,87,232,0.10)', color: 'var(--j-accent)', fontWeight: 700, fontSize: 12 }}>{version.job_type}</span>
                </div>

                <input
                  className="vc-input"
                  defaultValue={version.used_for || ''}
                  placeholder="Used for: e.g. Acme Corp Application"
                  onBlur={(event) => resumeAPI.updateVersionUsedFor(version.id, event.target.value).then(loadVersions)}
                  style={{ minHeight: 42, borderRadius: 12, border: '1px solid var(--j-border)', padding: '0 12px', background: 'var(--j-surface)', color: 'var(--j-text-1)' }}
                />

                <div className="vc-actions" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
                  <span className="vc-ats" style={{ fontSize: 13, color: 'var(--j-text-2)' }}>ATS Score: {version.ats_score ?? 'N/A'}</span>
                  <div className="vc-btn-group" style={{ display: 'flex', gap: 8 }}>
                    <button type="button" className="icon-action-btn" onClick={() => { setResumeText(version.content); setTab('rewrite'); }} title="Load into editor" style={{ width: 36, height: 36, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface)', display: 'grid', placeItems: 'center' }}><FileText size={14} /></button>
                    <button type="button" className="icon-action-btn" onClick={() => copyText(version.content)} title="Copy text" style={{ width: 36, height: 36, borderRadius: 12, border: '1px solid var(--j-border)', background: 'var(--j-surface)', display: 'grid', placeItems: 'center' }}><Copy size={14} /></button>
                    <button
                      type="button"
                      className="icon-action-btn del"
                      onClick={async () => {
                        await resumeAPI.deleteVersion(version.id)
                        loadVersions()
                      }}
                      title="Delete version"
                      style={{ width: 36, height: 36, borderRadius: 12, border: '1px solid rgba(239,68,68,0.18)', background: 'rgba(239,68,68,0.08)', display: 'grid', placeItems: 'center', color: '#b91c1c' }}
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
        <div className="save-modal-overlay" onClick={() => setShowSaveModal(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.45)', backdropFilter: 'blur(10px)', display: 'grid', placeItems: 'center', padding: 16 }}>
          <div className="save-modal fade-up" onClick={(event) => event.stopPropagation()} style={{ width: 'min(100%, 420px)', background: 'var(--j-surface)', border: '1px solid var(--j-border)', borderRadius: 18, padding: 24, boxShadow: 'var(--j-shadow-lg)' }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--j-text-1)' }}>Save Tailored Version</h3>
            <input
              value={versionName}
              onChange={(event) => setVersionName(event.target.value)}
              placeholder={`${jobType} Version`}
              autoFocus
              style={{ width: '100%', minHeight: 44, marginTop: 14, borderRadius: 12, border: '1px solid var(--j-border)', padding: '0 12px', background: 'var(--j-surface-2)', color: 'var(--j-text-1)' }}
            />
            <div className="save-modal-actions" style={{ display: 'flex', gap: 10, marginTop: 16 }}>
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
