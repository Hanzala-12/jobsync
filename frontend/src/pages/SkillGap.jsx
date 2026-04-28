import { useState } from 'react'
import { TrendingUp } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { intelligenceAPI } from '../api/client'
import './SkillGap.css'

const SkillGap = () => {
  const [jobDescriptions, setJobDescriptions] = useState([''])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const addJobDescription = () => {
    setJobDescriptions([...jobDescriptions, ''])
  }

  const updateJobDescription = (index, value) => {
    const updated = [...jobDescriptions]
    updated[index] = value
    setJobDescriptions(updated)
  }

  const handleAnalyze = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const filtered = jobDescriptions.filter(desc => desc.trim())
      const response = await intelligenceAPI.skillGap(filtered)
      setResult(response.data)
    } catch (error) {
      console.error('Failed to analyze skill gap:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="skill-gap-page">
      <div className="page-header">
        <h1>Skill Gap Analysis</h1>
        <p className="page-description">Identify missing skills from job descriptions</p>
      </div>

      <Card title="Job Descriptions">
        <form onSubmit={handleAnalyze} className="skill-gap-form">
          {jobDescriptions.map((desc, index) => (
            <div key={index} className="form-group">
              <label>Job Description {index + 1}</label>
              <textarea
                value={desc}
                onChange={(e) => updateJobDescription(index, e.target.value)}
                rows="4"
                className="form-input"
                required
              />
            </div>
          ))}
          <div className="form-actions">
            <Button type="button" variant="outline" onClick={addJobDescription}>
              Add Another
            </Button>
            <Button type="submit" loading={loading}>
              <TrendingUp size={20} />
              Analyze Skills
            </Button>
          </div>
        </form>
      </Card>

      {result && (
        <>
          <Card title="Missing Skills">
            <div className="skills-list">
              {result.missing_skills.map((skill, index) => (
                <div key={index} className="skill-item">
                  <span className="skill-name">{skill}</span>
                  {result.frequency[skill] && (
                    <span className="skill-frequency">
                      Appears in {result.frequency[skill]} job(s)
                    </span>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

export default SkillGap
