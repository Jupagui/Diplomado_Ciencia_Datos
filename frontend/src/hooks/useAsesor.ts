import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { mensajeError, preguntarAsesor, type PlanAccion } from '../services/api';

export type Mensaje = { rol: 'usuario'; texto: string } | { rol: 'asistente'; plan: PlanAccion } | { rol: 'error'; texto: string };

export const SUGERENCIAS = [
  '¿Qué debo reponer esta semana?',
  '¿Qué combos puedo armar para subir el ticket?',
  '¿Cómo fidelizo a mis mejores clientes?',
  'Prepárame para el próximo festivo',
  '¿Dónde puedo proteger mi margen?',
];

/** Estado y acciones del chat con el asesor. Lo comparten la página Asesor y el agente flotante. */
export function useAsesor() {
  const [chat, setChat] = useState<Mensaje[]>([]);
  const [texto, setTexto] = useState('');
  const fin = useRef<HTMLDivElement>(null);

  const preguntar = useMutation({
    mutationFn: preguntarAsesor,
    onSuccess: (plan) => setChat((c) => [...c, { rol: 'asistente', plan }]),
    onError: (e) => setChat((c) => [...c, { rol: 'error', texto: mensajeError(e) }]),
  });

  useEffect(() => { fin.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [chat, preguntar.isPending]);

  const enviar = (pregunta: string) => {
    const p = pregunta.trim();
    if (!p || preguntar.isPending) return;
    setChat((c) => [...c, { rol: 'usuario', texto: p }]);
    setTexto('');
    preguntar.mutate(p);
  };
  const alEnviar = (e: FormEvent) => { e.preventDefault(); enviar(texto); };

  return { chat, texto, setTexto, enviar, alEnviar, pendiente: preguntar.isPending, fin };
}

export type EstadoAsesor = ReturnType<typeof useAsesor>;
