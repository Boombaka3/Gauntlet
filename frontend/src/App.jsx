// frontend/src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout         from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Login     from './pages/Login.jsx'
import Jobs      from './pages/Jobs.jsx'
import Papers    from './pages/Papers.jsx'
import NewJob    from './pages/NewJob.jsx'
import JobStatus from './pages/JobStatus.jsx'
import Conflicts from './pages/Conflicts.jsx'
import JobList   from './pages/JobList.jsx'
import Chat      from './pages/Chat.jsx'

function Protected({ children }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/"      element={<Navigate to="/jobs" replace />} />
      <Route path="/jobs"               element={<Protected><Jobs /></Protected>} />
      <Route path="/jobs/new"           element={<Protected><NewJob /></Protected>} />
      <Route path="/jobs/list"          element={<Protected><JobList /></Protected>} />
      <Route path="/jobs/:id"           element={<Protected><Papers /></Protected>} />
      <Route path="/jobs/:id/status"    element={<Protected><JobStatus /></Protected>} />
      <Route path="/jobs/:id/conflicts" element={<Protected><Conflicts /></Protected>} />
      <Route path="/jobs/:id/chat"      element={<Protected><Chat /></Protected>} />
    </Routes>
  )
}
