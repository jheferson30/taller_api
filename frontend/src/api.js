const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || "";
const TIMEOUT_MS = 15000; // 15 segundos

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (ADMIN_PASSWORD) headers["X-Admin-Password"] = ADMIN_PASSWORD;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
    const contentType = res.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await res.json() : await res.text();
    if (!res.ok) {
      const detail = isJson ? payload.detail || JSON.stringify(payload) : payload;
      throw new Error(detail || "Error de servidor");
    }
    return payload;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("El servidor no respondió. Verifica la conexión.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  buscarVehiculo: (placa) => request(`/vehiculos/buscar?placa=${encodeURIComponent(placa)}`),
  crearVehiculo: (body) =>
    request("/vehiculos/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  actualizarVehiculo: (placa, body) =>
    request(`/vehiculos/${encodeURIComponent(placa)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  fichaVehiculo: (placa) => request(`/vehiculos/${encodeURIComponent(placa)}/ficha`),
  crearTicketIngreso: (placa, body) =>
    request(`/vehiculos/${encodeURIComponent(placa)}/ticket-ingreso`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  agregarFoto: (ticketId, body) =>
    request(`/tickets/${ticketId}/fotos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  eliminarFoto: (ticketId, fotoId) =>
    request(`/tickets/${ticketId}/fotos/${fotoId}`, {
      method: "DELETE",
    }),
  subirFoto: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/upload/foto`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Error al subir foto");
    return res.json();
  },
  subirSoporteCompra: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/upload/compra`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Error al subir soporte");
    return res.json();
  },
  agregarCompra: (ticketId, body) =>
    request(`/tickets/${ticketId}/compras`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  agregarCobro: (ticketId, body) =>
    request(`/tickets/${ticketId}/cobros`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  eliminarCobro: (ticketId, cobroId) =>
    request(`/tickets/${ticketId}/cobros/${cobroId}`, {
      method: "DELETE",
    }),
  actualizarFinanzas: (ticketId, body) =>
    request(`/tickets/${ticketId}/finanzas`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  finalizarTicket: (ticketId) =>
    request(`/tickets/${ticketId}/finalizar`, {
      method: "POST",
    }),
  entregarTicket: (ticketId, body) =>
    request(`/tickets/${ticketId}/entregar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
    const res = await fetch(`${API_BASE}/tickets/${ticketId}/pdf`, {
      headers: { "X-Admin-Password": ADMIN_PASSWORD },
    });
    if (!res.ok) throw new Error("No se pudo descargar el PDF");
    return res.blob();
  },
  descargarPdfEconomia: async (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    const res = await fetch(`${API_BASE}/economia-dia/pdf${params}`, {
      headers: { "X-Admin-Password": ADMIN_PASSWORD },
    });
    if (!res.ok) {
      throw new Error("No se pudo descargar el PDF");
    }
    return res.blob();
  },
  // Seguridad Economía
  verificarTienePassword: () => request("/seguridad/economia/tiene-password"),
  crearPasswordEconomia: (body) =>
    request("/seguridad/economia/crear-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  validarPasswordEconomia: (body) =>
    request("/seguridad/economia/validar-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  recuperarPasswordEconomia: (body) =>
    request("/seguridad/economia/recuperar-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  // Citas
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  actualizarCita: (citaId, body) =>
    request(`/citas/${citaId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  toggleMecanico: (id) =>
    request(`/configuracion/mecanicos/${id}`, { method: "PUT" }),
  eliminarMecanico: (id) =>
    request(`/configuracion/mecanicos/${id}`, { method: "DELETE" }),
  obtenerConfigTaller: () => request("/configuracion/taller"),
  actualizarConfigTaller: (body) =>
    request("/configuracion/taller", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  obtenerProcesosRapidos: () => request("/configuracion/procesos-rapidos"),
  actualizarProcesosRapidos: (procesos) =>
    request("/configuracion/procesos-rapidos", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ procesos }),
    }),
  obtenerCobrosRapidos: () => request("/configuracion/cobros-rapidos"),
  actualizarCobrosRapidos: (cobros) =>
    request("/configuracion/cobros-rapidos", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cobros }),
    }),
  cobroRapido: (body) =>
    request("/movimientos-caja/cobro-rapido", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  listarCobrosRapidos: (params = {}) => {
    const q = new URLSearchParams();
    if (params.placa) q.append("placa", params.placa);
    if (params.fecha_desde) q.append("fecha_desde", params.fecha_desde);
    if (params.fecha_hasta) q.append("fecha_hasta", params.fecha_hasta);
    return request(`/movimientos-caja/cobros-rapidos?${q.toString()}`);
  },
};
