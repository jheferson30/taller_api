import axios from 'axios';
import authService from './services/authService';

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TIMEOUT_MS = 15000; // 15 segundos

// Configurar axios con base URL y timeout
axios.defaults.baseURL = API_BASE;
axios.defaults.timeout = TIMEOUT_MS;

// IMPORTANTE: Los interceptores de axios ya están configurados en authService
// No necesitamos configurarlos aquí de nuevo

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
    const response = await axios.post("/upload/foto", formData);
    return response.data;
  },
  subirSoporteCompra: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await axios.post("/upload/compra", formData);
    return response.data;
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
    });
    return response.data;
  },
  descargarPdfEconomia: async (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    const response = await axios.get(`/economia-dia/pdf${params}`, {
      responseType: 'blob',
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
  crearUsuario: (body) => request("/users", { method: "POST", data: body }),
  eliminarUsuario: (id) => request(`/users/${id}`, { method: "DELETE" }),
  cambiarPasswordPropio: (body) => request("/users/me/change-password", { method: "POST", data: body }),
  obtenerPerfil: (userId) => request(`/users/${userId}`),
  obtenerConfigEmail: () => request("/configuracion/email"),
  actualizarConfigEmail: (body) => request("/configuracion/email", { method: "PUT", data: body }),
};
