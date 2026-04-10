import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import LoginPage from '../pages/LoginPage';
import authService from '../services/authService';

// Mock authService
vi.mock('../services/authService', () => ({
  default: {
    login: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renderiza el formulario de login correctamente', () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument();
  });

  test('muestra error con credenciales inválidas', async () => {
    authService.login.mockRejectedValue(new Error('Credenciales inválidas'));

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    fireEvent.change(screen.getByLabelText(/usuario/i), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'wrong' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByText(/credenciales inválidas/i)).toBeInTheDocument();
    });
  });

  test('redirige al dashboard con credenciales válidas', async () => {
    authService.login.mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: { username: 'admin', roles: ['ADMIN'] },
    });

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    fireEvent.change(screen.getByLabelText(/usuario/i), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'Admin123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  test('deshabilita el botón mientras está cargando', async () => {
    authService.login.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    fireEvent.change(screen.getByLabelText(/usuario/i), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'Admin123' },
    });
    
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/iniciando sesión/i)).toBeInTheDocument();
    });
  });

  test('muestra/oculta contraseña al hacer clic en el icono', () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    const passwordInput = screen.getByLabelText(/contraseña/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Click en el botón de mostrar/ocultar
    const toggleButton = passwordInput.nextElementSibling;
    fireEvent.click(toggleButton);

    expect(passwordInput).toHaveAttribute('type', 'text');
  });
});
