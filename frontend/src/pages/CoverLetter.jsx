import { useMemo, useState } from 'react'
import Button from '../components/Button'
import { coverLetterAPI } from '../api/client'
import './CoverLetter.css'

const tones = ['Professional', 'Enthusiastic', 'Concise']

function CoverLetter() {
  const [jobTitle, setJobTitle] = useState('')
  const [company, setCompany] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [tone, setTone] = useState('Professional')
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)

  const wordCount = useMemo(() => draft.trim().split(/\s+/).filter(Boolean).length, [draft])
  const readingTime = Math.max(1, Math.ceil(wordCount / 200))

  const generate = async () => {
    setLoading(true)
    try {
      const response = await coverLetterAPI.generate({
        role: jobTitle,
        company,
        job_description: jobDescription,
        tone: tone.toLowerCase(),
      })
      setDraft(response.data?.draft || '')
    } finally {
      setLoading(false)
    }
  }

  const copyDraft = async () => {
    await navigator.clipboard.writeText(draft)
  }

  const downloadDraft = () => {
    const blob = new Blob([draft], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'cover-letter.txt'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="cover-page">
      <div className="page-header">
        <h1>Cover Letter</h1>
        <p className="subtitle">Generate tailored letters with clean formatting.</p>
      </div>

      <div className="cover-grid">
        <section className="panel">
          <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} placeholder="Job Title" />
          <input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Company" />
          <textarea
            rows={13}
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            placeholder="Job Description"
          />
          <div className="tone-row">
            {tones.map((item) => (
              <button key={item} className={tone === item ? 'tone active' : 'tone'} onClick={() => setTone(item)}>
                {item}
              </button>
            ))}
          </div>
          <Button onClick={generate} loading={loading}>Generate</Button>
        </section>

        <section className="panel">
          {!draft ? (
            <p className="empty">Generated letter appears here.</p>
          ) : (
            <>
              <article className="letter-box">
                <p>{draft}</p>
              </article>
              <p className="meta">{wordCount} words · {readingTime} min read</p>
              <div className="actions">
                <Button variant="secondary" onClick={copyDraft}>Copy</Button>
                <Button variant="secondary" onClick={downloadDraft}>Download</Button>
                <button type="button" className="regen" onClick={generate}>Regenerate</button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

export default CoverLetter
