import authService from '../services/authService';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

// Mock config
jest.mock('../config', () => ({
  getAuthBaseUrl: jest.fn().mockResolvedValue('http://localhost:8000'),
}));

// Mock fetch
global.fetch = jest.fn();

describe('authService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    AsyncStorage.getItem.mockResolvedValue(null);
  });

  describe('login', () => {
    test('almacena tokens en AsyncStorage después de login exitoso', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'access123',
          refresh_token: 'refresh123',
          user: { username: 'admin', roles: ['ADMIN'] },
        }),
      };

      global.fetch.mockResolvedValue(mockResponse);

      const result = await authService.login('admin', 'Admin123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/auth/login',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: 'admin', password: 'Admin123' }),
        })
      );

      expect(AsyncStorage.setItem).toHaveBeenCalledWith('@auth_access_token', 'access123');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('@auth_refresh_token', 'refresh123');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@auth_user',
        JSON.stringify({ username: 'admin', roles: ['ADMIN'] })
      );

      expect(result.access_token).toBe('access123');
    });

    test('lanza error cuando las credenciales son inválidas', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({ detail: 'Credenciales inválidas' }),
      };

      global.fetch.mockResolvedValue(mockResponse);

      await expect(authService.login('admin', 'wrong')).rejects.toThrow('Credenciales inválidas');
    });

    test('lanza error genérico cuando no hay detalle en la respuesta', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: jest.fn().mockRejectedValue(new Error('Parse error')),
      };

      global.fetch.mockResolvedValue(mockResponse);

      await expect(authService.login('admin', 'wrong')).rejects.toThrow('Error 500');
    });
  });

  describe('logout', () => {
    test('limpia tokens de AsyncStorage', async () => {
      authService.accessToken = 'access123';
      authService.refreshToken = 'refresh123';

      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({}),
      };

      global.fetch.mockResolvedValue(mockResponse);

      await authService.logout();

      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@auth_access_token');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@auth_refresh_token');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@auth_user');
      expect(authService.accessToken).toBeNull();
      expect(authService.refreshToken).toBeNull();
    });

    test('limpia tokens incluso si la petición al servidor falla', async () => {
      authService.accessToken = 'access123';
      authService.refreshToken = 'refresh123';

      global.fetch.mockRejectedValue(new Error('Server error'));

      await authService.logout();

      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@auth_access_token');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@auth_refresh_token');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@auth_user');
    });
  });

  describe('getUser', () => {
    test('retorna el usuario del cache si está disponible', async () => {
      authService.user = { username: 'admin', roles: ['ADMIN'] };

      const user = await authService.getUser();

      expect(user).toEqual({ username: 'admin', roles: ['ADMIN'] });
      expect(AsyncStorage.getItem).not.toHaveBeenCalled();
    });

    test('retorna el usuario de AsyncStorage si no está en cache', async () => {
      authService.user = null;
      AsyncStorage.getItem.mockResolvedValue(
        JSON.stringify({ username: 'admin', roles: ['ADMIN'] })
      );

      const user = await authService.getUser();

      expect(user).toEqual({ username: 'admin', roles: ['ADMIN'] });
      expect(AsyncStorage.getItem).toHaveBeenCalledWith('@auth_user');
    });

    test('retorna null cuando no hay usuario', async () => {
      authService.user = null;
      AsyncStorage.getItem.mockResolvedValue(null);

      const user = await authService.getUser();

      expect(user).toBeNull();
    });
  });

  describe('isAuthenticated', () => {
    test('retorna true cuando hay un token en cache', async () => {
      authService.accessToken = 'access123';

      const result = await authService.isAuthenticated();

      expect(result).toBe(true);
    });

    test('retorna true cuando hay un token en AsyncStorage', async () => {
      authService.accessToken = null;
      AsyncStorage.getItem.mockResolvedValue('access123');

      const result = await authService.isAuthenticated();

      expect(result).toBe(true);
    });

    test('retorna false cuando no hay token', async () => {
      authService.accessToken = null;
      AsyncStorage.getItem.mockResolvedValue(null);

      const result = await authService.isAuthenticated();

      expect(result).toBe(false);
    });
  });

  describe('refreshAccessToken', () => {
    test('actualiza el access token en AsyncStorage', async () => {
      authService.refreshToken = 'refresh123';

      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'new_access123',
          refresh_token: 'new_refresh123',
        }),
      };

      global.fetch.mockResolvedValue(mockResponse);

      const newToken = await authService.refreshAccessToken();

      expect(newToken).toBe('new_access123');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('@auth_access_token', 'new_access123');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('@auth_refresh_token', 'new_refresh123');
    });

    test('lanza error cuando no hay refresh token', async () => {
      authService.refreshToken = null;
      AsyncStorage.getItem.mockResolvedValue(null);

      await expect(authService.refreshAccessToken()).rejects.toThrow(
        'No refresh token available'
      );
    });

    test('reutiliza la promesa de refresh si ya hay una en progreso', async () => {
      authService.refreshToken = 'refresh123';

      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'new_access123',
          refresh_token: 'new_refresh123',
        }),
      };

      global.fetch.mockResolvedValue(mockResponse);

      // Llamar dos veces simultáneamente
      const promise1 = authService.refreshAccessToken();
      const promise2 = authService.refreshAccessToken();

      const [result1, result2] = await Promise.all([promise1, promise2]);

      expect(result1).toBe('new_access123');
      expect(result2).toBe('new_access123');
      // Debe haber llamado a fetch solo una vez
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('loadTokens', () => {
    test('carga tokens desde AsyncStorage', async () => {
      AsyncStorage.getItem.mockImplementation((key) => {
        if (key === '@auth_access_token') return Promise.resolve('access123');
        if (key === '@auth_refresh_token') return Promise.resolve('refresh123');
        if (key === '@auth_user')
          return Promise.resolve(JSON.stringify({ username: 'admin', roles: ['ADMIN'] }));
        return Promise.resolve(null);
      });

      const result = await authService.loadTokens();

      expect(result.accessToken).toBe('access123');
      expect(result.refreshToken).toBe('refresh123');
      expect(result.user).toEqual({ username: 'admin', roles: ['ADMIN'] });
    });
  });
});
