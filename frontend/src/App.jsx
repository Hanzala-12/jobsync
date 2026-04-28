import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Resume from './pages/Resume'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import CoverLetter from './pages/CoverLetter'
import Interview from './pages/Interview'
import SkillGap from './pages/SkillGap'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/resume" element={<Resume />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/cover-letter" element={<CoverLetter />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/skill-gap" element={<SkillGap />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
