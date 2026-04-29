import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Card from '../components/Card';
import './Kanban.css';

function Kanban() {
  const [board, setBoard] = useState({
    Saved: [],
    Applied: [],
    Interviewing: [],
    Rejected: [],
    Offered: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBoard();
  }, []);

  const fetchBoard = async () => {
    try {
      const response = await fetch('http://localhost:8000/kanban/board');
      const data = await response.json();
      setBoard(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching board:', error);
      setLoading(false);
    }
  };

  const moveApplication = async (appId, newStatus) => {
    try {
      await fetch('http://localhost:8000/kanban/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: appId, new_status: newStatus })
      });
      fetchBoard();
    } catch (error) {
      console.error('Error moving application:', error);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="kanban-container">
          <h1>Loading Kanban Board...</h1>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="kanban-container">
        <h1>Application Tracker</h1>
        <p className="subtitle">Drag and drop to update application status</p>
        
        <div className="kanban-board">
          {Object.entries(board).map(([status, apps]) => (
            <div key={status} className="kanban-column">
              <div className="column-header">
                <h3>{status}</h3>
                <span className="count">{apps.length}</span>
              </div>
              
              <div className="column-content">
                {apps.map(app => (
                  <Card key={app.id} className="kanban-card">
                    <h4>{app.role}</h4>
                    <p className="company">{app.company}</p>
                    
                    {app.applied_date && (
                      <p className="date">Applied: {new Date(app.applied_date).toLocaleDateString()}</p>
                    )}
                    
                    {app.interview_date && (
                      <p className="date interview">Interview: {new Date(app.interview_date).toLocaleDateString()}</p>
                    )}
                    
                    {app.next_action && (
                      <p className="next-action">{app.next_action}</p>
                    )}
                    
                    <div className="move-buttons">
                      {status !== 'Saved' && (
                        <button onClick={() => moveApplication(app.id, 'Saved')}>← Saved</button>
                      )}
                      {status !== 'Applied' && (
                        <button onClick={() => moveApplication(app.id, 'Applied')}>Applied</button>
                      )}
                      {status !== 'Interviewing' && (
                        <button onClick={() => moveApplication(app.id, 'Interviewing')}>Interview</button>
                      )}
                      {status !== 'Offered' && status !== 'Rejected' && (
                        <>
                          <button onClick={() => moveApplication(app.id, 'Offered')} className="success">Offered</button>
                          <button onClick={() => moveApplication(app.id, 'Rejected')} className="danger">Rejected</button>
                        </>
                      )}
                    </div>
                  </Card>
                ))}
                
                {apps.length === 0 && (
                  <p className="empty-column">No applications</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}

export default Kanban;
