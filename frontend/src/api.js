const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = isJson ? payload.detail || JSON.stringify(payload) : payload;
    throw new Error(detail || "Error de servidor");
  }
  return payload;
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
  ticketResumen: (ticketId) => request(`/tickets/${ticketId}/resumen`),
  agregarProceso: (ticketId, body) =>
    request(`/tickets/${ticketId}/procesos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
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
  descargarPdfEconomia: async (password, fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    const res = await fetch(`${API_BASE}/economia-dia/pdf${params}`, {
      headers: { "X-PDF-Password": password },
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
};
