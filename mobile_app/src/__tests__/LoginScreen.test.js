import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../screens/LoginScreen';
import authService from '../services/authService';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock authService
jest.mock('../services/authService', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
  },
}));

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

// Mock config
jest.mock('../config', () => ({
  getServerIp: jest.fn().mockResolvedValue('http://localhost:8000'),
}));

// Mock navigation
const mockNavigate = jest.fn();
const mockReplace = jest.fn();
const mockAddListener = jest.fn(() => jest.fn());

const mockNavigation = {
  navigate: mockNavigate,
  replace: mockReplace,
  addListener: mockAddListener,
};

const mockRoute = {
  params: {},
};

describe('LoginScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    AsyncStorage.getItem.mockResolvedValue(null);
  });

  test('renderiza el formulario de login correctamente', async () => {
    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />
    );

    await waitFor(() => {
      expect(getByPlaceholderText('Usuario')).toBeTruthy();
      expect(getByPlaceholderText('Contraseña')).toBeTruthy();
      expect(getByText('Iniciar Sesión')).toBeTruthy();
    });
  });

  test('muestra error con credenciales inválidas', async () => {
    authService.login.mockRejectedValue(new Error('Credenciales inválidas'));

    const { getByPlaceholderText, getByText, findByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />
    );

    await waitFor(() => {
      expect(getByPlaceholderText('Usuario')).toBeTruthy();
    });

    fireEvent.changeText(getByPlaceholderText('Usuario'), 'admin');
    fireEvent.changeText(getByPlaceholderText('Contraseña'), 'wrong');
    fireEvent.press(getByText('Iniciar Sesión'));

    expect(await findByText('Credenciales inválidas')).toBeTruthy();
  });

  test('redirige al home con credenciales válidas', async () => {
    authService.login.mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: { username: 'mecanico', roles: ['MECANICO'] },
    });

    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />
    );

    await waitFor(() => {
      expect(getByPlaceholderText('Usuario')).toBeTruthy();
    });

    fireEvent.changeText(getByPlaceholderText('Usuario'), 'mecanico');
    fireEvent.changeText(getByPlaceholderText('Contraseña'), 'Mecanico123');
    fireEvent.press(getByText('Iniciar Sesión'));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('Home');
    });
  });

  test('redirige a HomeAdmin cuando el usuario es ADMIN', async () => {
    authService.login.mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: { username: 'admin', roles: ['ADMIN'] },
    });

    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />
    );

    await waitFor(() => {
      expect(getByPlaceholderText('Usuario')).toBeTruthy();
    });

    fireEvent.changeText(getByPlaceholderText('Usuario'), 'admin');
    fireEvent.changeText(getByPlaceholderText('Contraseña'), 'Admin123');
    fireEvent.press(getByText('Iniciar Sesión'));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('HomeAdmin');
    });
  });

  test('muestra error cuando los campos están vacíos', async () => {
    const { getByText, findByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />
    );

    await waitFor(() => {
      expect(getByText('Iniciar Sesión')).toBeTruthy();
    });

    fireEvent.press(getByText('Iniciar Sesión'));

    expect(await findByText('Por favor ingresa usuario y contraseña')).toBeTruthy();
  });

  test('guarda el usuario cuando se marca "Recordar usuario"', async () => {
    authService.login.mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: { username: 'admin', roles: ['ADMIN'] },
    });

    const { getByPlaceholderText, getByText } = render(
      <LoginScreen navigation={mockNavigation} route={mockRoute} />
    );

    await waitFor(() => {
      expect(getByPlaceholderText('Usuario')).toBeTruthy();
    });

    // Marcar checkbox "Recordar usuario"
    fireEvent.press(getByText('Recordar usuario'));

    fireEvent.changeText(getByPlaceholderText('Usuario'), 'admin');
    fireEvent.changeText(getByPlaceholderText('Contraseña'), 'Admin123');
    fireEvent.press(getByText('Iniciar Sesión'));

    await waitFor(() => {
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('@saved_username', 'admin');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('@remember_user', 'true');
    });
  });
});
