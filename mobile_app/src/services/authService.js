import AsyncStorage from '@react-native-async-storage/async-storage';
import { getApiBaseUrl } from '../config';

const TOKEN_KEY = '@auth_access_token';
const REFRESH_TOKEN_KEY = '@auth_refresh_token';
const USER_KEY = '@auth_user';

class AuthService {
  constructor() {
    this.accessToken = null;
    this.refreshToken = null;
    this.user = null;
    this.refreshPromise = null;
  }

  /**
   * Login con username y password
   * Almacena tokens en AsyncStorage
   */
  async login(username, password) {
    const baseUrl = await getApiBaseUrl();
    const response = await fetch(`${baseUrl.replace('/mobile', '')}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Error ${response.status}`);
    }

    const data = await response.json();
    
    // Almacenar tokens y usuario
    await Promise.all([
      AsyncStorage.setItem(TOKEN_KEY, data.access_token),
      AsyncStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token),
      AsyncStorage.setItem(USER_KEY, JSON.stringify(data.user)),
    ]);

    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    this.user = data.user;

    return data;
  }

  /**
   * Logout - limpia tokens y llama al endpoint
   */
  async logout() {
    try {
      if (this.accessToken) {
        const baseUrl = await getApiBaseUrl();
        await fetch(`${baseUrl.replace('/mobile', '')}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch (error) {
      console.warn('Error al hacer logout en servidor:', error);
    } finally {
      // Limpiar tokens localmente siempre
      await Promise.all([
        AsyncStorage.removeItem(TOKEN_KEY),
        AsyncStorage.removeItem(REFRESH_TOKEN_KEY),
        AsyncStorage.removeItem(USER_KEY),
      ]);
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      this.refreshPromise = null;
    }
  }

  /**
   * Refresca el access token usando el refresh token
   */
  async refreshAccessToken() {
    // Si ya hay un refresh en progreso, esperar a que termine
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const refreshToken = this.refreshToken || await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
        
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const baseUrl = await getApiBaseUrl();
        const response = await fetch(`${baseUrl.replace('/mobile', '')}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!response.ok) {
          throw new Error('Failed to refresh token');
        }

        const data = await response.json();
        
        // Actualizar tokens
        await Promise.all([
          AsyncStorage.setItem(TOKEN_KEY, data.access_token),
          AsyncStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token),
        ]);

        this.accessToken = data.access_token;
        this.refreshToken = data.refresh_token;

        return data.access_token;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Hace un request autenticado con retry automático en 401
   */
  async authenticatedRequest(url, options = {}) {
    // Obtener token
    let token = this.accessToken || await AsyncStorage.getItem(TOKEN_KEY);
    
    if (!token) {
      throw new Error('No access token available');
    }

    // Primer intento
    let response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
      },
    });

    // Si es 401, intentar refrescar token y reintentar
    if (response.status === 401) {
      try {
        token = await this.refreshAccessToken();
        
        // Reintentar con nuevo token
        response = await fetch(url, {
          ...options,
          headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch (error) {
        // Si falla el refresh, hacer logout
        await this.logout();
        throw new Error('Session expired. Please login again.');
      }
    }

    return response;
  }

  /**
   * Obtiene el usuario actual
   */
  async getUser() {
    if (this.user) {
      return this.user;
    }

    const userStr = await AsyncStorage.getItem(USER_KEY);
    if (userStr) {
      this.user = JSON.parse(userStr);
      return this.user;
    }

    return null;
  }

  /**
   * Verifica si el usuario está autenticado
   */
  async isAuthenticated() {
    const token = this.accessToken || await AsyncStorage.getItem(TOKEN_KEY);
    return !!token;
  }

  /**
   * Carga tokens desde AsyncStorage al iniciar la app
   */
  async loadTokens() {
    const [accessToken, refreshToken, userStr] = await Promise.all([
      AsyncStorage.getItem(TOKEN_KEY),
      AsyncStorage.getItem(REFRESH_TOKEN_KEY),
      AsyncStorage.getItem(USER_KEY),
    ]);

    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.user = userStr ? JSON.parse(userStr) : null;

    return {
      accessToken,
      refreshToken,
      user: this.user,
    };
  }
}

// Exportar instancia singleton
export default new AuthService();
