import { getApiBaseUrl, getPdfBaseUrl, getAdminPassword } from './config';

async function request(path, options = {}) {
  try {
    const [baseUrl, password] = await Promise.all([getApiBaseUrl(), getAdminPassword()]);
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Password': password,
        ...(options.headers || {}),
      },
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

  createProceso: async (ticketId, data, uri = null) => {
    const [baseUrl, password] = await Promise.all([getApiBaseUrl(), getAdminPassword()]);
    const formData = new FormData();
    formData.append('nombre', data.nombre);
    if (data.descripcion) formData.append('descripcion', data.descripcion);
    if (data.mecanico) formData.append('mecanico', data.mecanico);
    if (uri) {
      const filename = uri.split('/').pop();
      const ext = filename.split('.').pop().toLowerCase();
      const type = ext === 'png' ? 'image/png' : 'image/jpeg';
      formData.append('file', { uri, name: filename, type });
    }
    const response = await fetch(`${baseUrl}/tickets/${ticketId}/procesos`, {
      method: 'POST',
      body: formData,
      headers: { 'X-Admin-Password': password },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }
    return await response.json();
  },

  createRepuesto: (id, data) =>
    request(`/tickets/${id}/repuestos`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  subirFoto: async (ticketId, uri, descripcion = null, tipo = 'OTRA') => {
    const [baseUrl, password] = await Promise.all([getApiBaseUrl(), getAdminPassword()]);
    const filename = uri.split('/').pop();
    const ext = filename.split('.').pop().toLowerCase();
    const type = ext === 'png' ? 'image/png' : 'image/jpeg';

    const formData = new FormData();
    formData.append('file', { uri, name: filename, type });
    formData.append('tipo', tipo);
    if (descripcion) formData.append('descripcion', descripcion);

    const response = await fetch(
      `${baseUrl}/tickets/${ticketId}/fotos`,
      { method: 'POST', body: formData, headers: { 'X-Admin-Password': password } }
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

  getPdfUrl: async (ticketId) => {
    const [base, password] = await Promise.all([getPdfBaseUrl(), getAdminPassword()]);
    return `${base}/tickets/${ticketId}/pdf?token=${encodeURIComponent(password)}`;
  },

  descargarPdf: async (ticketId) => {
    const [base, password] = await Promise.all([getPdfBaseUrl(), getAdminPassword()]);
    const response = await fetch(`${base}/tickets/${ticketId}/pdf?token=${encodeURIComponent(password)}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }
    return response;
  },

  getMecanicos: () => request('/mecanicos'),

  getProcesosRapidos: () => request('/procesos-rapidos'),

  getCobrosRapidos: () => request('/cobros-rapidos'),

  createCompra: async (ticketId, data, uri = null) => {
    const [baseUrl, password] = await Promise.all([getApiBaseUrl(), getAdminPassword()]);
    const formData = new FormData();
    formData.append('descripcion', data.descripcion);
    formData.append('valor', String(data.valor));
    if (data.responsable) formData.append('responsable', data.responsable);
    if (data.nota) formData.append('nota', data.nota);
    if (uri) {
      const filename = uri.split('/').pop();
      const ext = filename.split('.').pop().toLowerCase();
      const type = ext === 'png' ? 'image/png' : 'image/jpeg';
      formData.append('file', { uri, name: filename, type });
    }
    const response = await fetch(`${baseUrl}/tickets/${ticketId}/compras`, {
      method: 'POST',
      body: formData,
      headers: { 'X-Admin-Password': password },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }
    return await response.json();
  },
};
