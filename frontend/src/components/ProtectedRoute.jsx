import { Navigate } from 'react-router-dom';
import authService from '../services/authService';

/**
 * Componente que protege rutas requiriendo autenticación
 * Redirige a /login si el usuario no está autenticado
 */
export default function ProtectedRoute({ children }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
