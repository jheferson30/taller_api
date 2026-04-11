import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';

class AuthService {
  constructor() {
    this.isRefreshing = false;
    this.refreshSubscribers = [];
    this.setupAxiosInterceptors();
  }

  /**
   * Configura interceptores de axios para agregar token automáticamente
   * y refrescar cuando expire
   */
  setupAxiosInterceptors() {
    // Request interceptor: agregar token a todas las peticiones
    axios.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: refrescar token automáticamente en 401
    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Si es 401, limpiar tokens y redirigir a login inmediatamente
        if (error.response?.status === 401) {
          // No intentar refresh si ya estamos en login o refresh
          if (
            originalRequest.url?.includes('/auth/login') ||
            originalRequest.url?.includes('/auth/refresh')
          ) {
            return Promise.reject(error);
          }

          // Si ya intentamos refresh, limpiar y redirigir
          if (originalRequest._retry) {
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(error);
          }

          originalRequest._retry = true;

          // Intentar refresh solo si hay refresh token
          const refreshToken = this.getRefreshToken();
          if (!refreshToken) {
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(error);
          }

          try {
            const newAccessToken = await this.refreshAccessToken();
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return axios(originalRequest);
          } catch (refreshError) {
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * Notifica a todos los requests en espera que el token fue refrescado
   */
  onRefreshed(token) {
    this.refreshSubscribers.forEach((callback) => callback(token));
  }

  /**
   * Login del usuario
   * @param {string} username 
   * @param {string} password 
   * @returns {Promise<{access_token: string, refresh_token: string, user: object}>}
   */
  async login(username, password) {
    try {
      const response = await axios.post(`${API_BASE}/auth/login`, {
        username,
        password,
      });

      const { access_token, refresh_token, user } = response.data;

      // Almacenar tokens en localStorage
      localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      return response.data;
    } catch (error) {
      if (error.response?.status === 429) {
        const retryAfter = error.response?.data?.retry_after || 60;
        const err = new Error('Demasiados intentos de inicio de sesión');
        err.status = 429;
        err.retryAfter = retryAfter;
        Object.defineProperty(err, 'retryAfter', { value: retryAfter, writable: true });
        throw err;
      }
      // Extraer mensaje del servidor
      const data = error.response?.data;
      let msg = 'Error al iniciar sesión';
      if (typeof data?.detail === 'string') {
        msg = data.detail;
      } else if (typeof data?.message === 'string') {
        msg = data.message;
      } else if (error.response?.status === 401) {
        msg = 'Usuario o contraseña incorrectos';
      } else if (error.response?.status === 403) {
        msg = 'Tu cuenta no tiene permisos para acceder';
      } else if (!error.response) {
        msg = 'No se pudo conectar al servidor. Verifica tu conexión.';
      }
      throw new Error(msg);
    }
  }

  /**
   * Logout del usuario
   */
  async logout() {
    const refreshToken = this.getRefreshToken();
    
    try {
      // Llamar al endpoint de logout para agregar token a blacklist
      if (refreshToken) {
        await axios.post(`${API_BASE}/auth/logout`, {
          refresh_token: refreshToken,
        });
      }
    } catch (error) {
      console.error('Error al hacer logout en el servidor:', error);
    } finally {
      // Limpiar tokens localmente siempre
      this.clearTokens();
    }
  }

  /**
   * Refresca el access token usando el refresh token
   * @returns {Promise<string>} Nuevo access token
   */
  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No hay refresh token disponible');
    }

    try {
      const response = await axios.post(`${API_BASE}/auth/refresh`, {
        refresh_token: refreshToken,
      });

      const { access_token } = response.data;
      localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
      
      return access_token;
    } catch (error) {
      this.clearTokens();
      throw new Error('Sesión expirada. Por favor inicia sesión nuevamente.');
    }
  }

  /**
   * Obtiene el access token del localStorage
   * @returns {string|null}
   */
  getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  /**
   * Obtiene el refresh token del localStorage
   * @returns {string|null}
   */
  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  /**
   * Obtiene el usuario del localStorage
   * @returns {object|null}
   */
  getUser() {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  /**
   * Verifica si el usuario está autenticado
   * @returns {boolean}
   */
  isAuthenticated() {
    const token = this.getAccessToken();
    if (!token) return false;
    // Verificar que el token no esté expirado localmente
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return false;
      // Agregar padding si es necesario para base64
      const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64 + '=='.slice(0, (4 - base64.length % 4) % 4);
      const payload = JSON.parse(atob(padded));
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp < now) {
        this.clearTokens();
        return false;
      }
      return true;
    } catch {
      // Si no podemos decodificar, asumir que es válido (el backend lo validará)
      return true;
    }
  }

  /**
   * Limpia todos los tokens del localStorage
   */
  clearTokens() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  /**
   * Carga los tokens al iniciar la aplicación
   */
  loadTokens() {
    // Los tokens ya están en localStorage, solo verificar que existan
    return this.isAuthenticated();
  }
}

// Exportar instancia singleton
const authService = new AuthService();
export default authService;
