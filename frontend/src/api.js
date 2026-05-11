import axios from 'axios';
import authService from './services/authService';

// En producción, usar URL relativa (mismo dominio). En desarrollo, localhost:8000
const API_BASE = import.meta.env.VITE_API_URL !== undefined 
  ? import.meta.env.VITE_API_URL 
  : (import.meta.env.MODE === 'production' ? '' : 'http://127.0.0.1:8000');
const TIMEOUT_MS = 15000; // 15 segundos para requests normales
const TIMEOUT_PDF_MS = 120000; // 2 minutos para generación de PDFs

/**
 * Lee el valor de una cookie por nombre.
 * Retorna null si la cookie no existe.
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return null;
}

// Configurar axios con base URL y timeout
axios.defaults.baseURL = API_BASE;
axios.defaults.timeout = TIMEOUT_MS;
axios.defaults.withCredentials = true; // Importante para que envíe y reciba cookies

// IMPORTANTE: Los interceptores de axios ya están configurados en authService
// No necesitamos configurarlos aquí de nuevo

// Métodos HTTP que requieren protección CSRF
const WRITE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

// Interceptor de request: agrega X-CSRF-Token en métodos de escritura
axios.interceptors.request.use((config) => {
  const method = (config.method || '').toLowerCase();
  if (WRITE_METHODS.has(method)) {
    // Leer CSRF token desde authService (guardado en login)
    const csrfToken = authService.getCsrfToken() || getCookie('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return config;
});

// Interceptor de response: retry automático en error CSRF (403)
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Solo reintentar si es 403 por CSRF y no es ya un reintento
    if (
      error.response?.status === 403 &&
      error.response?.data?.error === 'csrf_error' &&
      !originalRequest._csrfRetry
    ) {
      originalRequest._csrfRetry = true;

      // Refrescar el token leyendo la cookie actualizada
      const newCsrfToken = getCookie('csrftoken');
      if (newCsrfToken) {
        originalRequest.headers['X-CSRF-Token'] = newCsrfToken;
        return axios(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

async function request(path, options = {}) {
  try {
    const response = await axios({
      url: path,
      ...options,
    });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('El servidor no respondió. Verifica la conexión.');
    }
    const detail = error.response?.data?.detail || error.message || 'Error de servidor';
    throw new Error(detail);
  }
}

export const api = {
  buscarVehiculo: (placa) => request(`/vehiculos/buscar?placa=${encodeURIComponent(placa)}`),
  crearVehiculo: (body) =>
    request("/vehiculos/", {
      method: "POST",
      data: body,
    }),
  actualizarVehiculo: (placa, body) =>
    request(`/vehiculos/${encodeURIComponent(placa)}`, {
      method: "PUT",
      data: body,
    }),
  fichaVehiculo: (placa) => request(`/vehiculos/${encodeURIComponent(placa)}/ficha`),
  crearTicketIngreso: (placa, body) =>
    request(`/vehiculos/${encodeURIComponent(placa)}/ticket-ingreso`, {
      method: "POST",
      data: body,
    }),
  ticketsAbiertos: () => request("/tickets/abiertos"),
  buscarTickets: (params = {}) => {
    const q = new URLSearchParams();
    if (params.placa) q.append('placa', params.placa);
    if (params.estado) q.append('estado', params.estado);
    if (params.fecha_desde) q.append('fecha_desde', params.fecha_desde);
    if (params.fecha_hasta) q.append('fecha_hasta', params.fecha_hasta);
    return request(`/tickets/buscar?${q.toString()}`);
  },
  ticketResumen: (ticketId) => request(`/tickets/${ticketId}/resumen`),
  agregarProceso: (ticketId, body) =>
    request(`/tickets/${ticketId}/procesos`, {
      method: "POST",
      data: body,
    }),
  eliminarProceso: (ticketId, procesoId) =>
    request(`/tickets/${ticketId}/procesos/${procesoId}`, { method: "DELETE" }),
  eliminarRepuesto: (ticketId, repuestoId) =>
    request(`/tickets/${ticketId}/repuestos/${repuestoId}`, { method: "DELETE" }),
  eliminarCompra: (ticketId, compraId) =>
    request(`/tickets/${ticketId}/compras/${compraId}`, { method: "DELETE" }),
  agregarRepuesto: (ticketId, body) =>
    request(`/tickets/${ticketId}/repuestos`, {
      method: "POST",
      data: body,
    }),
  agregarFoto: (ticketId, body) =>
    request(`/tickets/${ticketId}/fotos`, {
      method: "POST",
      data: body,
    }),
  eliminarFoto: (ticketId, fotoId) =>
    request(`/tickets/${ticketId}/fotos/${fotoId}`, {
      method: "DELETE",
    }),
  subirFoto: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await axios.post("/upload/foto", formData);
      return response.data;
    } catch (error) {
      const status = error.response?.status;
      if (status === 413) throw new Error('El archivo es demasiado grande. Máximo permitido: 10 MB.');
      if (status === 415) throw new Error('Tipo de archivo no permitido. Usa JPG, PNG o PDF.');
      throw new Error(error.response?.data?.detail || 'Error al subir la foto. Intenta de nuevo.');
    }
  },
  subirSoporteCompra: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await axios.post("/upload/compra", formData);
      return response.data;
    } catch (error) {
      const status = error.response?.status;
      if (status === 413) throw new Error('El archivo es demasiado grande. Máximo permitido: 10 MB.');
      if (status === 415) throw new Error('Tipo de archivo no permitido. Usa JPG, PNG o PDF.');
      throw new Error(error.response?.data?.detail || 'Error al subir el soporte. Intenta de nuevo.');
    }
  },
  agregarCompra: (ticketId, body) =>
    request(`/tickets/${ticketId}/compras`, {
      method: "POST",
      data: body,
    }),
  agregarCobro: (ticketId, body) =>
    request(`/tickets/${ticketId}/cobros`, {
      method: "POST",
      data: body,
    }),
  eliminarCobro: (ticketId, cobroId) =>
    request(`/tickets/${ticketId}/cobros/${cobroId}`, {
      method: "DELETE",
    }),
  actualizarFinanzas: (ticketId, body) =>
    request(`/tickets/${ticketId}/finanzas`, {
      method: "PUT",
      data: body,
    }),
  finalizarTicket: (ticketId) =>
    request(`/tickets/${ticketId}/finalizar`, {
      method: "POST",
    }),
  entregarTicket: (ticketId, body) =>
    request(`/tickets/${ticketId}/entregar`, {
      method: "POST",
      data: body,
    }),
  economiaResumen: (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    return request(`/economia-dia${params}`);
  },
  economiaIngresos: (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    return request(`/economia-dia/ingresos${params}`);
  },
  economiaEgresos: (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    return request(`/economia-dia/egresos${params}`);
  },
  descargarPdfTicket: async (ticketId) => {
    const response = await axios.get(`/tickets/${ticketId}/pdf`, {
      responseType: 'blob',
      timeout: TIMEOUT_PDF_MS,
    });
    return response.data;
  },
  descargarPdfEconomia: async (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    const response = await axios.get(`/economia-dia/pdf${params}`, {
      responseType: 'blob',
      timeout: TIMEOUT_PDF_MS,
    });
    return response.data;
  },
  listarCitas: (fechaDesde, fechaHasta, estado) => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    if (estado) params.append('estado', estado);
    return request(`/citas?${params.toString()}`);
  },
  listarCitasProximas: (dias = 7) => request(`/citas/proximas?dias=${dias}`),
  obtenerCita: (citaId) => request(`/citas/${citaId}`),
  crearCita: (body) =>
    request("/citas", {
      method: "POST",
      data: body,
    }),
  actualizarCita: (citaId, body) =>
    request(`/citas/${citaId}`, {
      method: "PUT",
      data: body,
    }),
  cancelarCita: (citaId) =>
    request(`/citas/${citaId}`, {
      method: "DELETE",
    }),
  generarTicketDesdeCita: (citaId) =>
    request(`/citas/${citaId}/generar-ticket`, {
      method: "POST",
    }),
  infoSistema: () => request("/info"),
  infoConexionQr: () => request("/info/conexion-qr"),
  // Configuración
  listarMecanicos: () => request("/configuracion/mecanicos"),
  crearMecanico: (body) =>
    request("/configuracion/mecanicos", {
      method: "POST",
      data: body,
    }),
  toggleMecanico: (id) =>
    request(`/configuracion/mecanicos/${id}`, { method: "PUT" }),
  eliminarMecanico: (id) =>
    request(`/configuracion/mecanicos/${id}`, { method: "DELETE" }),
  obtenerConfigTaller: () => request("/configuracion/taller"),
  actualizarConfigTaller: (body) =>
    request("/configuracion/taller", {
      method: "PUT",
      data: body,
    }),
  obtenerProcesosRapidos: () => request("/configuracion/procesos-rapidos"),
  actualizarProcesosRapidos: (procesos) =>
    request("/configuracion/procesos-rapidos", {
      method: "PUT",
      data: { procesos },
    }),
  obtenerCobrosRapidos: () => request("/configuracion/cobros-rapidos"),
  actualizarCobrosRapidos: (cobros) =>
    request("/configuracion/cobros-rapidos", {
      method: "PUT",
      data: { cobros },
    }),
  cobroRapido: (body) =>
    request("/movimientos-caja/cobro-rapido", {
      method: "POST",
      data: body,
    }),
  economiaEstadisticas: (periodo = "semana") =>
    request(`/economia-dia/estadisticas?periodo=${periodo}`),
  listarCobrosRapidos: (params = {}) => {
    const q = new URLSearchParams();
    if (params.placa) q.append("placa", params.placa);
    if (params.fecha_desde) q.append("fecha_desde", params.fecha_desde);
    if (params.fecha_hasta) q.append("fecha_hasta", params.fecha_hasta);
    return request(`/movimientos-caja/cobros-rapidos?${q.toString()}`);
  },
  // Usuarios
  listarUsuarios: () => request("/users"),
  listarUsuariosParaAsignacion: () => request("/users/para-asignacion"),
  crearUsuario: (body) => request("/users", { method: "POST", data: body }),
  eliminarUsuario: (id) => request(`/users/${id}`, { method: "DELETE" }),
  cambiarPasswordPropio: (body) => request("/users/me/change-password", { method: "POST", data: body }),
  obtenerPerfil: (userId) => request(`/users/${userId}`),
  obtenerConfigEmail: () => request("/configuracion/email"),
  actualizarConfigEmail: (body) => request("/configuracion/email", { method: "PUT", data: body }),
  obtenerLogo: () => request("/configuracion/logo"),
  subirLogo: (formData) => request("/configuracion/logo", { method: "POST", data: formData, headers: { "Content-Type": "multipart/form-data" } }),
  cambiarPasswordAdmin: (body) => request("/seguridad/admin/cambiar-password", { method: "POST", data: body }),
};

// ── API Super Admin ──────────────────────────────────────────────────────────
export const apiSuperAdmin = {
  // Métricas
  metricasGlobales: () => request("/super-admin/metricas/global"),
  metricasTaller: (tallerId) => request(`/super-admin/talleres/${tallerId}/metricas`),
  recursosTaller: (tallerId) => request(`/super-admin/talleres/${tallerId}/recursos`),
  
  // Gestión de talleres
  listarTalleres: () => request("/super-admin/talleres"),
  crearTaller: (body) => request("/super-admin/talleres", { method: "POST", data: body }),
  actualizarTaller: (tallerId, body) => request(`/super-admin/talleres/${tallerId}`, { method: "PATCH", data: body }),
  cambiarEstado: (tallerId, estado) => request(`/super-admin/talleres/${tallerId}/estado`, { method: "PATCH", data: { estado } }),
  
  // Bloqueo de emergencia
  bloquearEmergencia: (tallerId, motivo) => request(`/super-admin/talleres/${tallerId}/bloqueo-emergencia`, { method: "POST", data: { motivo } }),
  desbloquearEmergencia: (tallerId) => request(`/super-admin/talleres/${tallerId}/bloqueo-emergencia`, { method: "DELETE" }),
  
  // Usuarios del taller
  listarUsuariosTaller: (tallerId) => request(`/super-admin/talleres/${tallerId}/usuarios`),
  crearAdminTaller: (tallerId, body) => request(`/super-admin/talleres/${tallerId}/usuarios`, { method: "POST", data: body }),
  resetPasswordMasivo: (tallerId) => request(`/super-admin/talleres/${tallerId}/reset-passwords`, { method: "POST" }),
  
  // Notificaciones
  enviarNotificacionMasiva: (body) => request("/super-admin/notificaciones/masivas", { method: "POST", data: body }),
  obtenerNotificacionesNoLeidas: () => request("/notificaciones/no-leidas"),
  marcarNotificacionLeida: (id) => request(`/notificaciones/${id}/leer`, { method: "PATCH" }),
  marcarTodasNotificacionesLeidas: () => request("/notificaciones/leer-todas", { method: "PATCH" }),
  
  // Auditoría
  obtenerAuditoria: (params = {}) => {
    const q = new URLSearchParams();
    if (params.taller_id) q.append("taller_id", params.taller_id);
    if (params.usuario_id) q.append("usuario_id", params.usuario_id);
    if (params.accion) q.append("accion", params.accion);
    if (params.fecha_desde) q.append("fecha_desde", params.fecha_desde);
    if (params.fecha_hasta) q.append("fecha_hasta", params.fecha_hasta);
    if (params.page) q.append("page", params.page);
    if (params.per_page) q.append("per_page", params.per_page);
    return request(`/super-admin/auditoria?${q.toString()}`);
  },
};
