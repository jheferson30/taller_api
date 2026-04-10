import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import ProtectedRoute from '../components/ProtectedRoute';
import authService from '../services/authService';

// Mock authService
vi.mock('../services/authService', () => ({
  default: {
    isAuthenticated: vi.fn(),
  },
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renderiza children cuando el usuario está autenticado', () => {
    authService.isAuthenticated.mockReturnValue(true);

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <div>Contenido Protegido</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Contenido Protegido')).toBeInTheDocument();
  });

  test('redirige a /login cuando el usuario no está autenticado', () => {
    authService.isAuthenticated.mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <div>Contenido Protegido</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Contenido Protegido')).not.toBeInTheDocument();
  });

  test('no renderiza children cuando no está autenticado', () => {
    authService.isAuthenticated.mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <div>Contenido Protegido</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText('Contenido Protegido')).not.toBeInTheDocument();
  });
});
