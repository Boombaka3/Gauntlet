// frontend/src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Jobs      from './pages/Jobs.jsx'
import Papers    from './pages/Papers.jsx'
import NewJob    from './pages/NewJob.jsx'
import JobStatus from './pages/JobStatus.jsx'
import Conflicts from './pages/Conflicts.jsx'
import JobList   from './pages/JobList.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"                       element={<Navigate to="/jobs" replace />} />
        <Route path="/jobs"                   element={<Jobs />} />
        <Route path="/jobs/new"               element={<NewJob />} />
        <Route path="/jobs/list"              element={<JobList />} />
        <Route path="/jobs/:id"               element={<Papers />} />
        <Route path="/jobs/:id/status"        element={<JobStatus />} />
        <Route path="/jobs/:id/conflicts"     element={<Conflicts />} />
      </Routes>
    </Layout>
  )
}
