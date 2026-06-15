// frontend/src/components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom'
import { isAuthenticated } from '../hooks/useAuth.js'

export default function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return children
}
