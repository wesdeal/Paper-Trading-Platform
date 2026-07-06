import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../store/auth'

export default function RequireAuth({ children }) {
  const token = useAuth((s) => s.token)
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}
