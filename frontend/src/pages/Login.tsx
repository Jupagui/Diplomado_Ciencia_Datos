import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { Marca } from '../layout/AppShell';
import { mensajeError } from '../services/api';
import { Button } from '../ui/Button';
import { Icon, IconSprite } from '../ui/Icon';
import { Field, ThemeSwitch } from '../ui/Inputs';
import { Alert } from '../ui/Surfaces';
import { OrbitBackdrop } from '../ui/backgrounds/OrbitBackdrop';

export default function Login() {
  const { autenticado, entrar } = useAuth();
  const navigate = useNavigate();
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);

  if (autenticado) return <Navigate to="/" replace />;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setCargando(true);
    try {
      await entrar(usuario.trim(), clave);
      navigate('/', { replace: true });
    } catch (err) {
      setError(mensajeError(err, 'No se pudo iniciar sesión'));
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="login-page">
      <IconSprite />
      <div className="backdrop is-home"><div className="aura a1" /><div className="aura a2" /><OrbitBackdrop /><div className="scrim" /></div>
      <section className="login-card rise" aria-labelledby="login-t">
        <div className="brand-line"><Marca /><ThemeSwitch /></div>
        <div>
          <p className="eyebrow">Acceso</p>
          <h1 id="login-t" className="title">Bienvenido a tu <em>negocio</em></h1>
          <p className="muted small" style={{ marginTop: 'var(--sp-1)' }}>Gestión operativa y analítica predictiva para micronegocios.</p>
        </div>
        <form onSubmit={enviar}>
          <Field label="Usuario" icon="usuarios" value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" autoFocus required />
          <Field label="Contraseña" icon="sello" type="password" value={clave} onChange={(e) => setClave(e.target.value)} autoComplete="current-password" required />
          {error && <Alert tone="danger" title="No se pudo ingresar" role="alert">{error}</Alert>}
          <Button type="submit" loading={cargando} disabled={!usuario || !clave} icon="next">Ingresar</Button>
        </form>
        <p className="muted small"><Icon name="info" /> Demo: usuario <code>admin</code>, contraseña <code>admin123</code>.</p>
      </section>
    </div>
  );
}
