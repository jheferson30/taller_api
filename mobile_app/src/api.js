// Cambia esta IP por la IP local de tu servidor
// Para encontrarla: en Windows ejecuta "ipconfig" en la terminal
// 10.0.2.2 es la IP del host (tu PC) desde el emulador de Android
const API_BASE_URL = 'http://10.0.2.2:8000/api/mobile';
const ADMIN_PASSWORD = 'la_pulga_fi';

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', 'X-Admin-Password': ADMIN_PASSWORD, ...(options.headers || {}) },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const detail = err.detail;
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : typeof detail === 'string'
          ? detail
          : `Error ${response.status}`;
      throw new Error(msg);
    }
    return await response.json();
  } catch (e) {
    throw new Error(e.message || 'Error de conexión con el servidor');
  }
}

export const api = {
  getEstadisticas: () => request('/estadisticas'),

  getTickets: (estado = null) =>
    request(`/tickets${estado ? `?estado=${estado}` : ''}`),

  getTicket: (id) => request(`/tickets/${id}`),

  getResumen: (id) => request(`/tickets/${id}/resumen`),

  getProcesos: (id) => request(`/tickets/${id}/procesos`),

  getRepuestos: (id) => request(`/tickets/${id}/repuestos`),

  getFotos: (id) => request(`/tickets/${id}/fotos`),

  updateEstado: (id, estado) =>
    request(`/tickets/${id}/estado`, {
      method: 'PATCH',
      body: JSON.stringify({ estado }),
    }),

  createProceso: (id, data) =>
    request(`/tickets/${id}/procesos`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createRepuesto: (id, data) =>
    request(`/tickets/${id}/repuestos`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  subirFoto: async (ticketId, uri, descripcion = null, tipo = 'OTRA') => {
    const filename = uri.split('/').pop();
    const ext = filename.split('.').pop().toLowerCase();
    const type = ext === 'png' ? 'image/png' : 'image/jpeg';

    const formData = new FormData();
    formData.append('file', { uri, name: filename, type });
    formData.append('tipo', tipo);
    if (descripcion) formData.append('descripcion', descripcion);

    const response = await fetch(
      `${API_BASE_URL}/tickets/${ticketId}/fotos`,
      { method: 'POST', body: formData, headers: { 'X-Admin-Password': ADMIN_PASSWORD } }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }
    return await response.json();
  },

  entregarTicket: (id, data) =>
    request(`/tickets/${id}/entregar`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  eliminarFoto: (ticketId, fotoId) =>
    request(`/tickets/${ticketId}/fotos/${fotoId}`, { method: 'DELETE' }),

  getCompras: (id) => request(`/tickets/${id}/compras`),

  eliminarCompra: (ticketId, compraId) =>
    request(`/tickets/${ticketId}/compras/${compraId}`, { method: 'DELETE' }),

  getCobros: (id) => request(`/tickets/${id}/cobros`),

  createCobro: (id, data) =>
    request(`/tickets/${id}/cobros`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  eliminarCobro: (ticketId, cobroId) =>
    request(`/tickets/${ticketId}/cobros/${cobroId}`, { method: 'DELETE' }),

  actualizarFinanzas: (id, data) =>
    request(`/tickets/${id}/finanzas`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getPdfUrl: (ticketId) => `http://10.0.2.2:8000/tickets/${ticketId}/pdf?token=${encodeURIComponent(ADMIN_PASSWORD)}`,

  descargarPdf: async (ticketId) => {
    const response = await fetch(`http://10.0.2.2:8000/tickets/${ticketId}/pdf?token=${encodeURIComponent(ADMIN_PASSWORD)}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }
    return response;
  },
};
