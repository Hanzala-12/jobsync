import { useState } from 'react';
import Layout from '../components/Layout';
import Card from '../components/Card';
import Button from '../components/Button';
import './DailyScout.css';

function DailyScout() {
  const [query, setQuery] = useState('software engineer');
  const [location, setLocation] = useState('remote');
  const [minScore, setMinScore] = useState(75);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runScout = async () => {
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8000/scout/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          location: location,
          min_score: minScore
        })
      });
      const data = await response.json();
      setResult(data);
      setLoading(false);
    } catch (error) {
      console.error('Error running scout:', error);
      setResult({ error: 'Failed to run scout. Check console for details.' });
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="daily-scout-container">
        <h1>Daily Scout</h1>
        <p className="subtitle">Automated job hunting powered by AI</p>

        <Card>
          <h2>Configure Scout</h2>
          <p className="description">
            Daily Scout searches for jobs, scores them against your resume, and saves the best matches automatically.
          </p>

          <div className="form-group">
            <label>Job Query *</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., software engineer, data scientist"
            />
          </div>

          <div className="form-group">
            <label>Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., remote, New York, London"
            />
          </div>

          <div className="form-group">
            <label>Minimum Match Score: {minScore}%</label>
            <input
              type="range"
              min="50"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              className="slider"
            />
            <div className="slider-labels">
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          <Button onClick={runScout} disabled={loading}>
            {loading ? 'Searching...' : 'Run Scout Now'}
          </Button>
        </Card>

        {result && (
          <Card className={result.error ? 'error-card' : 'success-card'}>
            {result.error ? (
              <>
                <h3>❌ Error</h3>
                <p>{result.error}</p>
              </>
            ) : (
              <>
                <h3>✅ Scout Complete!</h3>
                <div className="result-stats">
                  <div className="stat">
                    <span className="stat-value">{result.found}</span>
                    <span className="stat-label">Jobs Found</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{result.saved}</span>
                    <span className="stat-label">Jobs Saved</span>
                  </div>
                </div>

                {result.top_jobs && result.top_jobs.length > 0 && (
                  <div className="top-jobs">
                    <h4>Top Matches:</h4>
                    <ul>
                      {result.top_jobs.map((job, index) => (
                        <li key={index}>
                          <strong>{job.title}</strong> at {job.company}
                          <span className="score">{job.score}% match</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <p className="next-step">
                  Check the <a href="/jobs">Jobs page</a> to view and apply to saved jobs.
                </p>
              </>
            )}
          </Card>
        )}

        <Card className="info-card">
          <h3>ℹ️ How It Works</h3>
          <ol>
            <li><strong>Search:</strong> Scout searches JSearch API for recent job postings</li>
            <li><strong>Analyze:</strong> Each job is analyzed using AI to extract requirements</li>
            <li><strong>Match:</strong> Jobs are scored against your resume (0-100%)</li>
            <li><strong>Filter:</strong> Only jobs above your minimum score are saved</li>
            <li><strong>Save:</strong> Top matches are saved to your database for review</li>
          </ol>

          <div className="requirements">
            <h4>Requirements:</h4>
            <ul>
              <li>✅ Resume uploaded in system</li>
              <li>✅ RAPIDAPI_KEY configured in .env</li>
              <li>✅ Valid API key for JSearch</li>
            </ul>
          </div>
        </Card>
      </div>
    </Layout>
  );
}

export default DailyScout;
