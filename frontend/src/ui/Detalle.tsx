import type { ReactNode } from 'react';

/** Bloque plegable (divulgación progresiva): esconde detalles técnicos o listas largas
 *  hasta que la persona decide abrirlos. Usa <details>, así funciona con teclado y lector de pantalla. */
export function Detalle({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <details className="ux-mas">
      <summary>{titulo}</summary>
      <div className="ux-mas-cuerpo">{children}</div>
    </details>
  );
}
