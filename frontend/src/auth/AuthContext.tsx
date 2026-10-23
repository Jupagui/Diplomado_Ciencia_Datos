import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { CLAVE_TOKEN, CLAVE_USUARIO, login } from '../services/api';
import { AuthContext } from './useAuth';

function leer(clave: string): string | null {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
}

/** Sesión JWT guardada en localStorage. El interceptor de api.ts adjunta el token. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => leer(CLAVE_TOKEN));
  const [usuario, setUsuario] = useState<string | null>(() => leer(CLAVE_USUARIO));

  const entrar = useCallback(async (username: string, password: string) => {
    const r = await login(username, password);
    try {
      localStorage.setItem(CLAVE_TOKEN, r.access_token);
      localStorage.setItem(CLAVE_USUARIO, r.username);
    } catch {
      // la sesión durará solo mientras la pestaña siga abierta
    }
    setToken(r.access_token);
    setUsuario(r.username);
  }, []);

  const salir = useCallback(() => {
    try {
      localStorage.removeItem(CLAVE_TOKEN);
      localStorage.removeItem(CLAVE_USUARIO);
    } catch {
      // nada que limpiar
    }
    setToken(null);
    setUsuario(null);
  }, []);

  const valor = useMemo(() => ({ usuario, autenticado: !!token, entrar, salir }), [usuario, token, entrar, salir]);
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
