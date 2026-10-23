import { createContext, useContext } from 'react';

export interface Sesion {
  usuario: string | null;
  autenticado: boolean;
  entrar: (username: string, password: string) => Promise<void>;
  salir: () => void;
}

export const AuthContext = createContext<Sesion>({
  usuario: null,
  autenticado: false,
  entrar: async () => {},
  salir: () => {},
});

export const useAuth = () => useContext(AuthContext);
