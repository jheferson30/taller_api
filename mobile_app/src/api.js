import AsyncStorage from '@react-native-async-storage/async-storage';
import { getApiBaseUrl, getPdfBaseUrl, getAdminPassword } from './config';
import authService from './services/authService';

// Mensajes amigables por código de error HTTP
function mensajeError(status, detalle = null) {
  if (detalle && typeof detalle === 'string') return detalle;
  switch (status) {
    case 400: return 'Los datos enviados no son válidos. Revisa la información.';
    case 401: return 'Sesión expirada. Por favor inicia sesión nuevamente.';
    case 403: return 'No tienes permisos para realizar esta acción.';
    case 404: return 'El recurso solicitado no fue encontrado.';
    case 409: return 'Ya existe un registro con esos datos.';
    case 413: return 'El archivo es demasiado grande. Máximo permitido: 10 MB.';
    case 415: return 'Tipo de archivo no permitido. Usa JPG, PNG o PDF.';
    case 422: return 'Los datos enviados tienen errores de validación.';
    case 429: return 'Demasiadas solicitudes. Espera un momento e intenta de nuevo.';
    case 500: return 'Error interno del servidor. Intenta más tarde.';
    case 502: return 'El servidor no está disponible. Intenta más tarde.';
    case 503: return 'Servicio temporalmente no disponible. Intenta más tarde.';
    default:  return 'Ocurrió un error inesperado. Intenta de nuevo.';
  }
}

async function request(path, options = {}) {
  try {
    const baseUrl = await getApiBaseUrl();
    const url = `${baseUrl}${path}`;
    
    const response = await authService.authenticatedRequest(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const detail = err.detail;
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : mensajeError(response.status, typeof detail === 'string' ? detail : null);
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
    const baseUrl = await getApiBaseUrl();
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
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/procesos`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || mensajeError(response.status));
    }
    return await response.json();
  },

  createRepuesto: (id, data) =>
    request(`/tickets/${id}/repuestos`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  subirFoto: async (ticketId, uri, descripcion = null, tipo = 'OTRA') => {
    const baseUrl = await getApiBaseUrl();
    const filename = uri.split('/').pop();
    const ext = filename.split('.').pop().toLowerCase();
    const type = ext === 'png' ? 'image/png' : 'image/jpeg';

    const formData = new FormData();
    formData.append('file', { uri, name: filename, type });
    formData.append('tipo', tipo);
    if (descripcion) formData.append('descripcion', descripcion);

    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/fotos`,
      { method: 'POST', body: formData }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || mensajeError(response.status));
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

  eliminarCompra: async (ticketId, compraId) => {
    const baseUrl = await getPdfBaseUrl();
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/compras/${compraId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error(mensajeError(response.status));
    return response.json();
  },

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
    const base = await getPdfBaseUrl();
    const token = authService.accessToken || await AsyncStorage.getItem('@auth_access_token');
    return `${base}/tickets/${ticketId}/pdf?token=${encodeURIComponent(token)}`;
  },

  descargarPdf: async (ticketId) => {
    const base = await getPdfBaseUrl();
    const response = await authService.authenticatedRequest(
      `${base}/tickets/${ticketId}/pdf`,
      {}
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || mensajeError(response.status));
    }
    return response;
  },

  getMecanicos: () => request('/mecanicos'),

  getProcesosRapidos: () => request('/procesos-rapidos'),

  getCobrosRapidos: () => request('/cobros-rapidos'),

  cobroRapido: async (data) => {
    const baseUrl = await getPdfBaseUrl();
    const response = await authService.authenticatedRequest(
      `${baseUrl}/movimientos-caja/cobro-rapido`,
      {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json' },
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const detail = err.detail;
      const msg = Array.isArray(detail) ? detail.map(d => d.msg || JSON.stringify(d)).join(', ') : typeof detail === 'string' ? detail : mensajeError(response.status);
      throw new Error(msg);
    }
    return response.json();
  },

  eliminarProceso: async (ticketId, procesoId) => {
    const baseUrl = await getPdfBaseUrl();
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/procesos/${procesoId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error(mensajeError(response.status));
    return response.json();
  },

  eliminarRepuesto: async (ticketId, repuestoId) => {
    const baseUrl = await getPdfBaseUrl();
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/repuestos/${repuestoId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error(mensajeError(response.status));
    return response.json();
  },

  subirArchivoFoto: async (uri) => {
    const baseUrl = await getPdfBaseUrl();
    const filename = uri.split('/').pop() || `foto_${Date.now()}.jpg`;
    const ext = filename.includes('.') ? filename.split('.').pop().toLowerCase() : 'jpg';
    const type = ext === 'png' ? 'image/png' : 'image/jpeg';
    const safeName = filename.includes('.') ? filename : `${filename}.jpg`;
    const formData = new FormData();
    formData.append('file', { uri, name: safeName, type });
    const response = await authService.authenticatedRequest(
      `${baseUrl}/upload/foto`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || mensajeError(response.status, 'Error al subir foto'));
    }
    return response.json();
  },

  createProcesoJson: async (ticketId, data) => {
    const baseUrl = await getPdfBaseUrl();
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/procesos`,
      {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json' },
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const detail = err.detail;
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : typeof detail === 'string' ? detail : mensajeError(response.status);
      throw new Error(msg);
    }
    return response.json();
  },

  createCompra: async (ticketId, data, uri = null) => {
    const baseUrl = await getApiBaseUrl();
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
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/compras`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || mensajeError(response.status));
    }
    return await response.json();
  },

  getEconomia: (fecha) => request(`/economia-hoy${fecha ? '?fecha=' + fecha : ''}`),
};
