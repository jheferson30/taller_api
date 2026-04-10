import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
import HomeScreen from '../screens/HomeScreen';
import { api } from '../api';
import authService from '../services/authService';

// Mock api
jest.mock('../api', () => ({
  api: {
    getEstadisticas: jest.fn(),
  },
}));

// Mock authService
jest.mock('../services/authService', () => ({
  __esModule: true,
  default: {
    getUser: jest.fn(),
  },
}));

// Mock navigation
const mockNavigate = jest.fn();
const mockNavigation = {
  navigate: mockNavigate,
  addListener: jest.fn(() => jest.fn()),
};

// Mock useFocusEffect
jest.mock('@react-navigation/native', () => ({
  useFocusEffect: jest.fn((callback) => {
    // Don't call the callback automatically - let tests control it
  }),
}));

describe('HomeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('muestra loading mientras carga datos', () => {
    api.getEstadisticas.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    authService.getUser.mockResolvedValue({ username: 'admin', roles: ['ADMIN'] });

    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);

    expect(getByText('Conectando al servidor...')).toBeTruthy();
  });

  test('muestra estadísticas cuando los datos se cargan correctamente', async () => {
    const mockStats = {
      por_estado: {
        abiertos: 5,
        en_proceso: 3,
        finalizados: 10,
        entregados: 8,
      },
    };

    api.getEstadisticas.mockResolvedValue(mockStats);
    authService.getUser.mockResolvedValue({ username: 'admin', roles: ['ADMIN'] });

    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText('5')).toBeTruthy(); // Abiertos
      expect(getByText('3')).toBeTruthy(); // En Proceso
      expect(getByText('10')).toBeTruthy(); // Finalizados
      expect(getByText('8')).toBeTruthy(); // Entregados
    });
  });

  test('muestra error cuando falla la carga de datos', async () => {
    api.getEstadisticas.mockRejectedValue(new Error('Error de conexión'));
    authService.getUser.mockResolvedValue({ username: 'admin', roles: ['ADMIN'] });

    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText('Sin conexión')).toBeTruthy();
      expect(getByText('Error de conexión')).toBeTruthy();
    });
  });

  test('navega a TicketList cuando se presiona una tarjeta KPI', async () => {
    const mockStats = {
      por_estado: {
        abiertos: 5,
        en_proceso: 3,
        finalizados: 10,
        entregados: 8,
      },
    };

    api.getEstadisticas.mockResolvedValue(mockStats);
    authService.getUser.mockResolvedValue({ username: 'admin', roles: ['ADMIN'] });

    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText('Abiertos')).toBeTruthy();
    });

    fireEvent.press(getByText('Abiertos'));

    expect(mockNavigate).toHaveBeenCalledWith('TicketList', {
      estado: 'ABIERTO',
      titulo: 'Tickets Abiertos',
    });
  });

  test('navega a CobroRapido cuando se presiona el botón de acceso rápido', async () => {
    const mockStats = {
      por_estado: {
        abiertos: 5,
        en_proceso: 3,
        finalizados: 10,
        entregados: 8,
      },
    };

    api.getEstadisticas.mockResolvedValue(mockStats);
    authService.getUser.mockResolvedValue({ username: 'admin', roles: ['ADMIN'] });

    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText(/Cobro Rápido/)).toBeTruthy();
    });

    fireEvent.press(getByText(/Cobro Rápido/));

    expect(mockNavigate).toHaveBeenCalledWith('CobroRapido', {});
  });

  test('muestra el rol correcto del usuario', async () => {
    const mockStats = {
      por_estado: {
        abiertos: 5,
        en_proceso: 3,
        finalizados: 10,
        entregados: 8,
      },
    };

    api.getEstadisticas.mockResolvedValue(mockStats);
    authService.getUser.mockResolvedValue({ username: 'mecanico', roles: ['MECANICO'] });

    const { getAllByText } = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      const mecanicoTexts = getAllByText('Mecánico');
      expect(mecanicoTexts.length).toBeGreaterThan(0);
    });
  });

  test('reintenta cargar datos cuando se presiona el botón Reintentar', async () => {
    api.getEstadisticas.mockRejectedValueOnce(new Error('Error de conexión'));
    authService.getUser.mockResolvedValue({ username: 'admin', roles: ['ADMIN'] });

    const { getByText } = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText('Reintentar')).toBeTruthy();
    });

    // Ahora hacer que la segunda llamada tenga éxito
    const mockStats = {
      por_estado: {
        abiertos: 5,
        en_proceso: 3,
        finalizados: 10,
        entregados: 8,
      },
    };
    api.getEstadisticas.mockResolvedValue(mockStats);

    fireEvent.press(getByText('Reintentar'));

    await waitFor(() => {
      expect(getByText('5')).toBeTruthy(); // Abiertos
    });
  });
});
