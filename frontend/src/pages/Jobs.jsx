import { useState } from 'react'
import { Search, MapPin, Building, ExternalLink } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { jobsAPI } from '../api/client'
import './Jobs.css'

const Jobs = () => {
  const [query, setQuery] = useState('software developer')
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await jobsAPI.search(query)
      setJobs(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to search jobs')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="jobs-page">
      <div className="page-header">
        <h1>Job Search</h1>
        <p className="page-description">Search for jobs from multiple sources</p>
      </div>

      <Card>
        <div className="search-section">
          <div className="search-input-group">
            <Search size={20} className="search-icon" />
            <input
              type="text"
              placeholder="Search for jobs..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="search-input"
            />
          </div>
          <Button onClick={handleSearch} loading={loading}>
            Search
          </Button>
        </div>
      </Card>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {jobs.length > 0 && (
        <div className="jobs-grid">
          {jobs.map((job) => (
            <Card key={job.id} className="job-card">
              <div className="job-header">
                <h3 className="job-title">{job.title}</h3>
                <span className="job-source">{job.source}</span>
              </div>
              <div className="job-details">
                <div className="job-detail">
                  <Building size={16} />
                  <span>{job.company}</span>
                </div>
                <div className="job-detail">
                  <MapPin size={16} />
                  <span>{job.location}</span>
                </div>
              </div>
              <p className="job-description">
                {job.description.substring(0, 200)}...
              </p>
              <div className="job-actions">
                <a href={job.url} target="_blank" rel="noopener noreferrer" className="job-link">
                  View Job <ExternalLink size={16} />
                </a>
              </div>
            </Card>
          ))}
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <Card>
          <div className="empty-state">
            <Search size={48} />
            <p>Search for jobs to get started</p>
          </div>
        </Card>
      )}
    </div>
  )
}

export default Jobs
