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
      const operations = [...this.pendingOperations];

      // Preparar batch de operaciones
      const batch = operations.map(op => ({
        id: op.id,
        type: op.type,
        endpoint: op.endpoint,
        method: op.method,
        data: op.data,
        timestamp: op.timestamp,
      }));

      // Enviar batch al servidor
      const response = await authService.authenticatedRequest(
        `${baseUrl}/sync/batch`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ operations: batch }),
        }
      );

      if (!response.ok) {
        throw new Error(`Sync failed: ${response.status}`);
      }

      const result = await response.json();

      // Procesar resultados
      const successIds = result.successful || [];
      const failedOps = result.failed || [];

      // Remover operaciones exitosas
      this.pendingOperations = this.pendingOperations.filter(
        op => !successIds.includes(op.id)
      );

      // Manejar operaciones fallidas
      for (const failed of failedOps) {
        console.warn(`Operation ${failed.id} failed:`, failed.error);
        // Mantener en la cola para reintentar
      }

      await this.savePendingOperations();
      this.notifyListeners();

      return {
        successful: successIds.length,
        failed: failedOps.length,
        conflicts: result.conflicts || [],
      };
    } catch (error) {
      console.error('Sync error:', error);
      // Reintentar con backoff exponencial
      await this.scheduleRetry();
      throw error;
    } finally {
      this.isSyncing = false;
      this.notifyListeners();
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
