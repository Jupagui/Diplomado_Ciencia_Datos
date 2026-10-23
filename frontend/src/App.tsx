import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import RequireAuth from './auth/RequireAuth';
import AppShell from './layout/AppShell';
import Analitica from './pages/Analitica';
import Asesor from './pages/Asesor';
import Clientes from './pages/Clientes';
import Datos from './pages/Datos';
import Inicio from './pages/Inicio';
import Login from './pages/Login';
import Productos from './pages/Productos';
import PuntoVenta from './pages/PuntoVenta';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Inicio />} />
              <Route path="/pos" element={<PuntoVenta />} />
              <Route path="/productos" element={<Productos />} />
              <Route path="/clientes" element={<Clientes />} />
              <Route path="/analitica" element={<Analitica />} />
              <Route path="/asesor" element={<Asesor />} />
              <Route path="/datos" element={<Datos />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
