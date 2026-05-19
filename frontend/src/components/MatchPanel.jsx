import Button from './Button'
import './MatchPanel.css'

const MatchPanel = ({ open, job, matchData, onClose, onRewrite }) => {
  if (!open || !job) return null

  return (
    <div className="match-overlay" onClick={onClose}>
      <aside className="match-panel" onClick={(event) => event.stopPropagation()}>
        <div className="match-header">
          <h3>Match Analysis</h3>
          <button type="button" onClick={onClose}>X</button>
        </div>

        <p className="match-job-title">{job.title}</p>
        <p className="match-company">{job.company}</p>

        <div className="score-circle">{Math.round(matchData?.match_score || 0)}</div>

        <div className="paragraph green">
          <p>{matchData?.paragraph1 || 'Strong-fit summary will appear here.'}</p>
        </div>
        <div className="paragraph red">
          <p>{matchData?.paragraph2 || 'Gap analysis will appear here.'}</p>
        </div>
        <div className="paragraph blue">
          <p>{matchData?.paragraph3 || 'Action plan will appear here.'}</p>
        </div>

        <p className="section-label">MATCHED SKILLS</p>
        <div className="chip-list">
          {(matchData?.matched_skills || []).map((skill) => (
            <span className="chip chip-good" key={skill}>{skill}</span>
          ))}
        </div>

        <p className="section-label">MISSING SKILLS</p>
        <div className="chip-list">
          {(matchData?.missing_skills || []).map((skill) => (
            <span className="chip chip-bad" key={skill}>{skill}</span>
          ))}
        </div>

        <div className="quick-win">
          <p className="section-label">Quick Win This Week</p>
          <p>{matchData?.quick_win || 'Tailor two bullets in your resume to this role.'}</p>
        </div>

        <Button className="full-width" onClick={() => onRewrite(job.description)}>
          Rewrite Resume for This Job
        </Button>
      </aside>
    </div>
  )
}

export default MatchPanel
