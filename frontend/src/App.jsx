// frontend/src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Suites from './pages/Suites.jsx'
import Cases from './pages/Cases.jsx'
import NewRun from './pages/NewRun.jsx'
import Runs from './pages/Runs.jsx'
import RunStatus from './pages/RunStatus.jsx'
import Results from './pages/Results.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/suites" replace />} />
        <Route path="/suites" element={<Suites />} />
        <Route path="/suites/:id" element={<Cases />} />
        <Route path="/runs/new" element={<NewRun />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/runs/:id" element={<RunStatus />} />
        <Route path="/runs/:id/results" element={<Results />} />
        <Route path="/models" element={
          <div className="px-8 py-8">
            <h1 className="text-2xl font-semibold text-gauntlet-text mb-2">Models</h1>
            <p className="text-gauntlet-muted text-sm">Available models are configured via the API. Use New Run to select models.</p>
          </div>
        } />
      </Routes>
    </Layout>
  )
}
