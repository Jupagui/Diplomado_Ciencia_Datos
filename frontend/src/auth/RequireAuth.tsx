import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './useAuth';

/** Protege las rutas hijas: sin sesión redirige a /login. */
export default function RequireAuth() {
  const { autenticado } = useAuth();
  const ubicacion = useLocation();
  if (!autenticado) return <Navigate to="/login" replace state={{ desde: ubicacion.pathname }} />;
  return <Outlet />;
}
