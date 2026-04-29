import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Resume from './pages/Resume'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import CoverLetter from './pages/CoverLetter'
import Interview from './pages/Interview'
import SkillGap from './pages/SkillGap'
import Kanban from './pages/Kanban'
import MockInterview from './pages/MockInterview'
import DailyScout from './pages/DailyScout'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/resume" element={<Resume />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/kanban" element={<Kanban />} />
          <Route path="/cover-letter" element={<CoverLetter />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/mock-interview" element={<MockInterview />} />
          <Route path="/skill-gap" element={<SkillGap />} />
          <Route path="/daily-scout" element={<DailyScout />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
