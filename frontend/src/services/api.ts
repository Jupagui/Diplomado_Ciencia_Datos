import axios, { isAxiosError } from 'axios';

export const API_URL: string = import.meta.env.VITE_API_URL || 'http://localhost:8010/api/v1';

export const CLAVE_TOKEN = 'mn-token';
export const CLAVE_USUARIO = 'mn-user';

export const apiClient = axios.create({ baseURL: API_URL });

/** Bearer desde localStorage en cada petición. */
apiClient.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem(CLAVE_TOKEN);
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } catch {
    // sin almacenamiento: la petición sale sin token
  }
  return config;
});

/** Ante un 401 (que no sea el propio login) se limpia la sesión y se vuelve al login. */
apiClient.interceptors.response.use(
  (r) => r,
  (error) => {
    if (isAxiosError(error) && error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      try {
        localStorage.removeItem(CLAVE_TOKEN);
        localStorage.removeItem(CLAVE_USUARIO);
      } catch {
        // nada que limpiar
      }
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

/** Texto legible de un error de la API (detail puede ser texto o lista de validación). */
export function mensajeError(e: unknown, defecto = 'Ocurrió un error inesperado'): string {
  if (isAxiosError(e)) {
    const d = e.response?.data?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((x) => x?.msg ?? String(x)).join('; ');
    if (!e.response) return 'No se pudo conectar con el servidor (¿está el backend en el puerto 8010?)';
  }
  return defecto;
}

export const estadoHttp = (e: unknown): number | undefined => (isAxiosError(e) ? e.response?.status : undefined);

// ---------- Tipos ----------
export interface Producto {
  id: number; sku: string; name: string; category: string | null; unit_price: number; unit_cost: number;
  stock: number; is_active: boolean; created_at: string | null;
}
export interface ProductoIn { sku: string; name: string; category?: string | null; unit_price: number; unit_cost: number; stock: number }
export interface ProductoUpdate { name?: string; category?: string | null; unit_price?: number; unit_cost?: number; is_active?: boolean }

export interface Cliente { id: number; first_name: string; last_name: string; email: string | null; phone: string | null; revelado: boolean; created_at: string | null }

export interface ItemVenta { id: number | null; product_id: number; product_name: string | null; quantity: number; unit_price: number; subtotal: number }
export interface Venta { id: number; customer_id: number | null; total_amount: number; payment_method: string; status: string; created_at: string | null; items: ItemVenta[] }

export interface Movimiento { id: number; product_id: number; movement_type: 'IN' | 'OUT' | 'MERMA'; quantity: number; reason: string | null; created_at: string | null }

export interface Kpis {
  dias: number; total_ventas: number; n_ventas: number; unidades_vendidas: number; ticket_promedio: number; costo_vendido: number;
  margen: number; margen_pct: number; valor_inventario: number; rotacion: number; rotacion_anual: number; productos_bajo_stock: number;
  top_productos: { product_id: number; name: string; category: string | null; unidades: number; ingresos: number }[];
  ventas_por_categoria: { category: string; unidades: number; ingresos: number }[];
  serie_diaria: { fecha: string; total: number; n_ventas: number }[];
}

export interface EtlRun {
  id: number; started_at: string; finished_at: string | null; status: string; watermark: string | null; rows_extracted: number;
  duracion_s: number | null; metrics: Record<string, any> | null; error: string | null;
}

export interface DemandaProducto {
  product_id: number; name: string; sku: string; category: string | null; stock: number; horizon: number; total_predicho: number;
  model_version: string; diaria: { fecha: string; cantidad: number }[];
}
export interface Regla { id: number; antecedent: string; consequent: string; support: number; confidence: number; lift: number }
export interface ResumenSegmento { cluster: number; segmento: string; n_clientes: number; recencia_media: number; frecuencia_media: number; monetario_medio: number; monetario_total: number }
export interface ClienteSegmento { customer_id: number; first_name: string; last_name: string; recency: number; frequency: number; monetary: number; cluster: number; segment_label: string }
export interface Segmentos { resumen: ResumenSegmento[]; clientes: ClienteSegmento[] }
export interface Metricas {
  disponible: boolean; mae: number | null; r2: number | null; silhouette: number | null; k: number | null; n_reglas: number | null;
  ultimo_run: string | null; run_id?: number | null; detalle: Record<string, any> | null;
}

export interface AccionPlan {
  accion: string; justificacion: string; impacto_estimado: string; riesgo: 'bajo' | 'medio' | 'alto'; datos_citados: string[]; descuento_pct: number | null;
}
export interface PlanAccion { resumen: string; acciones: AccionPlan[]; advertencias: string[]; modo: 'gemini' | 'simulado' }

// ---------- Llamadas ----------
export const login = async (username: string, password: string) =>
  (await apiClient.post<{ access_token: string; username: string }>('/auth/login', { username, password })).data;

export const getKpis = async (dias: number) => (await apiClient.get<Kpis>('/kpis/resumen', { params: { dias, top: 8 } })).data;

export const getProductos = async (params: { q?: string; solo_activos?: boolean } = {}) =>
  (await apiClient.get<Producto[]>('/products', { params: { ...params, limit: 1000 } })).data;
export const getCategorias = async () => (await apiClient.get<string[]>('/products/categories')).data;
export const crearProducto = async (p: ProductoIn) => (await apiClient.post<Producto>('/products', p)).data;
export const actualizarProducto = async (id: number, p: ProductoUpdate) => (await apiClient.put<Producto>(`/products/${id}`, p)).data;
export const desactivarProducto = async (id: number) => { await apiClient.delete(`/products/${id}`); };
export const getStockBajo = async (umbral = 15) => (await apiClient.get<Producto[]>('/inventory/low-stock', { params: { umbral } })).data;
export const getMovimientos = async (product_id: number) =>
  (await apiClient.get<Movimiento[]>('/inventory/movements', { params: { product_id, limit: 100 } })).data;
export const registrarMovimiento = async (m: { product_id: number; movement_type: string; quantity: number; reason?: string }) =>
  (await apiClient.post<Movimiento>('/inventory/movements', m)).data;

export const getClientes = async (q: string | undefined, revelar: boolean) =>
  (await apiClient.get<Cliente[]>('/customers', { params: { q: q || undefined, revelar, limit: 500 } })).data;

export const registrarVenta = async (v: { items: { product_id: number; quantity: number }[]; payment_method: string; customer_id?: number | null }) =>
  (await apiClient.post<Venta>('/sales', v)).data;

export const getDemanda = async (horizon: 7 | 30, product_id?: number) =>
  (await apiClient.get<DemandaProducto[]>('/analytics/demand', { params: { horizon, product_id } })).data;
export const getReglas = async () => (await apiClient.get<Regla[]>('/analytics/basket', { params: { limit: 100 } })).data;
export const getSegmentos = async () => (await apiClient.get<Segmentos>('/analytics/segments')).data;
export const getMetricas = async () => (await apiClient.get<Metricas>('/analytics/metrics')).data;

export const ejecutarEtl = async (force: boolean) => (await apiClient.post<EtlRun>('/etl/run', null, { params: { force } })).data;
export const getRuns = async () => (await apiClient.get<EtlRun[]>('/etl/runs', { params: { limit: 20 } })).data;

export const preguntarAsesor = async (pregunta: string) => (await apiClient.post<PlanAccion>('/advisor/ask', { pregunta })).data;
