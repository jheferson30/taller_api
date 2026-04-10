import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Import authService after mocking axios
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

global.localStorage = mockLocalStorage;

describe('authService', () => {
  let authService;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
    
    // Re-import authService for each test to get fresh instance
    vi.resetModules();
    const module = await import('../services/authService');
    authService = module.default;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    test('almacena tokens en localStorage después de login exitoso', async () => {
      const mockResponse = {
        data: {
          access_token: 'access123',
          refresh_token: 'refresh123',
          user: { username: 'admin', roles: ['ADMIN'] },
        },
      };

      axios.post.mockResolvedValue(mockResponse);

      await authService.login('admin', 'Admin123');

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/auth/login'),
        { username: 'admin', password: 'Admin123' }
      );
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('access_token', 'access123');
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('refresh_token', 'refresh123');
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'user',
        JSON.stringify({ username: 'admin', roles: ['ADMIN'] })
      );
    });

    test('lanza error cuando las credenciales son inválidas', async () => {
      axios.post.mockRejectedValue({
        response: { data: { detail: 'Credenciales inválidas' } },
      });

      await expect(authService.login('admin', 'wrong')).rejects.toThrow(
        'Credenciales inválidas'
      );
    });

    test('lanza error genérico cuando no hay detalle en la respuesta', async () => {
      axios.post.mockRejectedValue(new Error('Network error'));

      await expect(authService.login('admin', 'wrong')).rejects.toThrow(
        'Error al iniciar sesión'
      );
    });
  });

  describe('logout', () => {
    test('limpia tokens del localStorage', async () => {
      mockLocalStorage.getItem.mockReturnValue('refresh123');
      axios.post.mockResolvedValue({ data: {} });

      await authService.logout();

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('user');
    });

    test('limpia tokens incluso si la petición al servidor falla', async () => {
      mockLocalStorage.getItem.mockReturnValue('refresh123');
      axios.post.mockRejectedValue(new Error('Server error'));

      await authService.logout();

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });

  describe('getAccessToken', () => {
    test('retorna el access token del localStorage', () => {
      mockLocalStorage.getItem.mockReturnValue('access123');

      const token = authService.getAccessToken();

      expect(token).toBe('access123');
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('access_token');
    });

    test('retorna null cuando no hay token', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const token = authService.getAccessToken();

      expect(token).toBeNull();
    });
  });

  describe('getUser', () => {
    test('retorna el usuario parseado del localStorage', () => {
      const user = { username: 'admin', roles: ['ADMIN'] };
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify(user));

      const result = authService.getUser();

      expect(result).toEqual(user);
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('user');
    });

    test('retorna null cuando no hay usuario', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const result = authService.getUser();

      expect(result).toBeNull();
    });
  });

  describe('isAuthenticated', () => {
    test('retorna false cuando no hay token', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const result = authService.isAuthenticated();

      expect(result).toBe(false);
    });

    test('retorna true cuando hay un token válido', () => {
      // Create a valid JWT token (not expired)
      const futureTimestamp = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now
      const payload = { exp: futureTimestamp };
      const encodedPayload = btoa(JSON.stringify(payload));
      const token = `header.${encodedPayload}.signature`;

      mockLocalStorage.getItem.mockReturnValue(token);

      const result = authService.isAuthenticated();

      expect(result).toBe(true);
    });

    test('retorna false y limpia tokens cuando el token está expirado', () => {
      // Create an expired JWT token
      const pastTimestamp = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
      const payload = { exp: pastTimestamp };
      const encodedPayload = btoa(JSON.stringify(payload));
      const token = `header.${encodedPayload}.signature`;

      mockLocalStorage.getItem.mockReturnValue(token);

      const result = authService.isAuthenticated();

      expect(result).toBe(false);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });

  describe('refreshAccessToken', () => {
    test('actualiza el access token en localStorage', async () => {
      mockLocalStorage.getItem.mockReturnValue('refresh123');
      axios.post.mockResolvedValue({
        data: { access_token: 'new_access123' },
      });

      const newToken = await authService.refreshAccessToken();

      expect(newToken).toBe('new_access123');
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('access_token', 'new_access123');
    });

    test('lanza error cuando no hay refresh token', async () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      await expect(authService.refreshAccessToken()).rejects.toThrow(
        'No hay refresh token disponible'
      );
    });

    test('limpia tokens cuando el refresh falla', async () => {
      mockLocalStorage.getItem.mockReturnValue('refresh123');
      axios.post.mockRejectedValue(new Error('Invalid refresh token'));

      await expect(authService.refreshAccessToken()).rejects.toThrow(
        'Sesión expirada'
      );
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });
});
