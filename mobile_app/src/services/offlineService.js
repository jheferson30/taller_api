import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { getApiBaseUrl } from '../config';
import authService from './authService';

const QUEUE_KEY = '@offline_queue';
const CACHE_KEY_PREFIX = '@cache_';

class OfflineService {
  constructor() {
    this.isOnline = true;
    this.isSyncing = false;
    this.pendingOperations = [];
    this.listeners = [];
    this.unsubscribeNetInfo = null;
  }

  /**
   * Inicializa el servicio y comienza a escuchar cambios de conexión
   */
  async initialize() {
    // Cargar operaciones pendientes
    await this.loadPendingOperations();

    // Escuchar cambios de conexión
    this.unsubscribeNetInfo = NetInfo.addEventListener(state => {
      const wasOnline = this.isOnline;
      this.isOnline = state.isConnected && state.isInternetReachable;

      // Si pasamos de offline a online, sincronizar
      if (!wasOnline && this.isOnline) {
        this.syncPendingOperations();
      }

      this.notifyListeners();
    });

    // Obtener estado inicial
    const state = await NetInfo.fetch();
    this.isOnline = state.isConnected && state.isInternetReachable;
  }

  /**
   * Detiene el servicio
   */
  destroy() {
    if (this.unsubscribeNetInfo) {
      this.unsubscribeNetInfo();
    }
  }

  /**
   * Encola una operación para sincronización posterior
   */
  async enqueueOperation(operation) {
    const op = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
      ...operation,
    };

    this.pendingOperations.push(op);
    await this.savePendingOperations();
    this.notifyListeners();

    return op.id;
  }

  /**
   * Obtiene las operaciones pendientes
   */
  getPendingOperations() {
    return [...this.pendingOperations];
  }

  /**
   * Sincroniza todas las operaciones pendientes
   */
  async syncPendingOperations() {
    if (this.isSyncing || !this.isOnline || this.pendingOperations.length === 0) {
      return;
    }

    this.isSyncing = true;
    this.notifyListeners();

    try {
      const baseUrl = await getApiBaseUrl();
      const successIds = [];
      const failedOps = [];

      for (const op of [...this.pendingOperations]) {
        try {
          // Operaciones multipart con archivo
          if (op.type === 'CREATE_PROCESO_CON_FOTO') {
            await this._syncProcesoConFoto(op, baseUrl);
          } else if (op.type === 'CREATE_FOTO') {
            await this._syncFoto(op, baseUrl);
          } else if (op.type === 'CREATE_REPUESTO_CON_FOTO') {
            await this._syncRepuestoConFoto(op, baseUrl);
          } else if (op.type === 'CREATE_COMPRA_CON_SOPORTE') {
            await this._syncCompraConSoporte(op, baseUrl);
          } else {
            // Operaciones JSON simples: POST, PATCH, DELETE
            const method = op.method || 'POST';
            const headers = { 'Content-Type': 'application/json' };
            const body = method !== 'DELETE' ? JSON.stringify(op.data || {}) : undefined;
            const response = await authService.authenticatedRequest(
              `${baseUrl}${op.endpoint}`,
              { method, headers, body }
            );
            if (!response.ok) {
              const err = await response.json().catch(() => ({}));
              throw new Error(
                err.detail ||
                (response.status === 401 ? 'Sesión expirada' :
                 response.status === 403 ? 'Sin permisos' : 'Error al sincronizar')
              );
            }
          }
          successIds.push(op.id);
        } catch (err) {
          console.warn(`Operation ${op.id} failed:`, err.message);
          failedOps.push(op);
        }
      }

      // Remover operaciones exitosas
      this.pendingOperations = this.pendingOperations.filter(
        op => !successIds.includes(op.id)
      );

      await this.savePendingOperations();
      this.notifyListeners();

      return { successful: successIds.length, failed: failedOps.length };
    } catch (error) {
      console.error('Sync error:', error);
      await this.scheduleRetry();
      throw error;
    } finally {
      this.isSyncing = false;
      this.notifyListeners();
    }
  }

  /**
   * Sincroniza un proceso con foto usando multipart/form-data
   */
  async _syncProcesoConFoto(op, baseUrl) {
    const { ticketId, nombre, descripcion, mecanico, fotoUri } = op.data;
    const formData = new FormData();
    formData.append('nombre', nombre);
    if (descripcion) formData.append('descripcion', descripcion);
    if (mecanico) formData.append('mecanico', mecanico);
    if (fotoUri) {
      const filename = fotoUri.split('/').pop();
      const ext = filename.split('.').pop().toLowerCase();
      formData.append('file', { uri: fotoUri, name: filename, type: ext === 'png' ? 'image/png' : 'image/jpeg' });
    }
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/procesos/con-foto`,
      { method: 'POST', body: formData }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al sincronizar proceso con foto');
    }
  }

  /**
   * Sincroniza una foto de ticket usando multipart/form-data
   */
  async _syncFoto(op, baseUrl) {
    const { ticketId, fotoUri, descripcion, tipo } = op.data;
    const formData = new FormData();
    const filename = fotoUri.split('/').pop();
    const ext = filename.split('.').pop().toLowerCase();
    formData.append('file', { uri: fotoUri, name: filename, type: ext === 'png' ? 'image/png' : 'image/jpeg' });
    formData.append('tipo', tipo || 'OTRA');
    if (descripcion) formData.append('descripcion', descripcion);
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/fotos`,
      { method: 'POST', body: formData }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al sincronizar foto');
    }
  }

  /**
   * Sincroniza un repuesto con foto opcional
   */
  async _syncRepuestoConFoto(op, baseUrl) {
    const { ticketId, nombre, cantidad, marcaReferencia, fotoUri,
            fueComprado, valor, responsable, nota, soporteUri } = op.data;

    // 1. Subir foto del repuesto si hay
    let foto_url = null;
    if (fotoUri) {
      const filename = fotoUri.split('/').pop();
      const ext = filename.split('.').pop().toLowerCase();
      const fd = new FormData();
      fd.append('file', { uri: fotoUri, name: filename, type: ext === 'png' ? 'image/png' : 'image/jpeg' });
      const res = await authService.authenticatedRequest(`${baseUrl}/upload/foto`, { method: 'POST', body: fd });
      if (res.ok) { const d = await res.json(); foto_url = d.url; }
    }

    // 2. Crear repuesto
    const repRes = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/repuestos`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, cantidad, marca_referencia: marcaReferencia || null, foto_url }),
      }
    );
    if (!repRes.ok) {
      const err = await repRes.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al sincronizar repuesto');
    }

    // 3. Crear compra si fue comprado
    if (fueComprado && valor > 0) {
      const uriSoporte = soporteUri || fotoUri;
      const fd2 = new FormData();
      fd2.append('descripcion', nombre);
      fd2.append('valor', String(valor));
      if (responsable) fd2.append('responsable', responsable);
      if (nota) fd2.append('nota', nota);
      if (uriSoporte) {
        const fn = uriSoporte.split('/').pop();
        const ex = fn.split('.').pop().toLowerCase();
        fd2.append('file', { uri: uriSoporte, name: fn, type: ex === 'png' ? 'image/png' : 'image/jpeg' });
      }
      await authService.authenticatedRequest(`${baseUrl}/tickets/${ticketId}/compras`, { method: 'POST', body: fd2 });
    }
  }

  /**
   * Sincroniza una compra con soporte opcional
   */
  async _syncCompraConSoporte(op, baseUrl) {
    const { ticketId, descripcion, valor, responsable, nota, soporteUri } = op.data;
    const formData = new FormData();
    formData.append('descripcion', descripcion);
    formData.append('valor', String(valor));
    if (responsable) formData.append('responsable', responsable);
    if (nota) formData.append('nota', nota);
    if (soporteUri) {
      const filename = soporteUri.split('/').pop();
      const ext = filename.split('.').pop().toLowerCase();
      formData.append('file', { uri: soporteUri, name: filename, type: ext === 'png' ? 'image/png' : 'image/jpeg' });
    }
    const response = await authService.authenticatedRequest(
      `${baseUrl}/tickets/${ticketId}/compras`,
      { method: 'POST', body: formData }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al sincronizar compra');
    }
  }

  /**
   * Programa un reintento con backoff exponencial
   */
  async scheduleRetry(attempt = 0) {
    const delays = [1000, 2000, 4000, 8000, 30000]; // 1s, 2s, 4s, 8s, 30s
    const delay = delays[Math.min(attempt, delays.length - 1)];

    setTimeout(() => {
      if (this.isOnline && this.pendingOperations.length > 0) {
        this.syncPendingOperations().catch(() => {
          this.scheduleRetry(attempt + 1);
        });
      }
    }, delay);
  }

  /**
   * Inicia sincronización automática
   */
  startAutoSync() {
    // Sincronizar cada 30 segundos si hay operaciones pendientes
    this.syncInterval = setInterval(() => {
      if (this.isOnline && this.pendingOperations.length > 0 && !this.isSyncing) {
        this.syncPendingOperations().catch(console.error);
      }
    }, 30000);
  }

  /**
   * Detiene sincronización automática
   */
  stopAutoSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Guarda datos en caché local
   */
  async cacheData(key, data) {
    const cacheKey = `${CACHE_KEY_PREFIX}${key}`;
    await AsyncStorage.setItem(cacheKey, JSON.stringify({
      data,
      timestamp: new Date().toISOString(),
    }));
  }

  /**
   * Obtiene datos de caché local
   */
  async getCachedData(key, maxAge = 7 * 24 * 60 * 60 * 1000) {
    const cacheKey = `${CACHE_KEY_PREFIX}${key}`;
    const cached = await AsyncStorage.getItem(cacheKey);

    if (!cached) {
      return null;
    }

    const { data, timestamp } = JSON.parse(cached);
    const age = Date.now() - new Date(timestamp).getTime();

    if (age > maxAge) {
      // Caché expirado
      await AsyncStorage.removeItem(cacheKey);
      return null;
    }

    return data;
  }

  /**
   * Limpia caché antiguo
   */
  async cleanOldCache(maxAge = 7 * 24 * 60 * 60 * 1000) {
    const keys = await AsyncStorage.getAllKeys();
    const cacheKeys = keys.filter(k => k.startsWith(CACHE_KEY_PREFIX));

    for (const key of cacheKeys) {
      const cached = await AsyncStorage.getItem(key);
      if (cached) {
        const { timestamp } = JSON.parse(cached);
        const age = Date.now() - new Date(timestamp).getTime();
        
        if (age > maxAge) {
          await AsyncStorage.removeItem(key);
        }
      }
    }
  }

  /**
   * Carga operaciones pendientes desde AsyncStorage
   */
  async loadPendingOperations() {
    const stored = await AsyncStorage.getItem(QUEUE_KEY);
    if (stored) {
      this.pendingOperations = JSON.parse(stored);
    }
  }

  /**
   * Guarda operaciones pendientes en AsyncStorage
   */
  async savePendingOperations() {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(this.pendingOperations));
  }

  /**
   * Agrega un listener para cambios de estado
   */
  addListener(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }

  /**
   * Notifica a todos los listeners
   */
  notifyListeners() {
    const state = {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      pendingCount: this.pendingOperations.length,
    };

    this.listeners.forEach(callback => {
      try {
        callback(state);
      } catch (error) {
        console.error('Listener error:', error);
      }
    });
  }

  /**
   * Obtiene el estado actual
   */
  getState() {
    return {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      pendingCount: this.pendingOperations.length,
    };
  }
}

// Exportar instancia singleton
export default new OfflineService();
