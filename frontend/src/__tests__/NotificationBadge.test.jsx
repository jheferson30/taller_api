/**
 * Tests para NotificationBadge
 *
 * Propiedad 15: Badge refleja conteo correcto
 * Valida: Requisitos 6.1, 6.2
 *
 * Para cualquier conteo N:
 *   - badge se muestra cuando N > 0
 *   - badge se oculta cuando N = 0
 */
import { render, screen, waitFor, act } from "@testing-library/react";
import { vi, describe, test, expect, beforeEach, afterEach } from "vitest";
import axios from "axios";
import NotificationBadge from "../components/NotificationBadge";

// Mock axios
vi.mock("axios");

// Mock authService
vi.mock("../services/authService", () => ({
  default: {
    getAccessToken: vi.fn(() => "fake-token"),
    getUser: vi.fn(() => ({ username: "admin", roles: ["ADMIN"] })),
  },
}));

describe("NotificationBadge — Propiedad 15: badge refleja conteo correcto", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /**
   * Caso N = 0: badge debe estar oculto
   */
  test("oculta el badge cuando total = 0", async () => {
    axios.get.mockResolvedValue({ data: { total: 0, notificaciones: [] } });

    render(<NotificationBadge />);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalled();
    });

    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument();
  });

  /**
   * Caso N = 1: badge debe mostrarse con valor 1
   */
  test("muestra el badge con valor 1 cuando total = 1", async () => {
    axios.get.mockResolvedValue({ data: { total: 1, notificaciones: [] } });

    render(<NotificationBadge />);

    await waitFor(() => {
      expect(screen.getByTestId("notification-badge")).toBeInTheDocument();
    });
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("1");
  });

  /**
   * Caso N = 5: badge debe mostrarse con valor 5
   */
  test("muestra el badge con valor 5 cuando total = 5", async () => {
    axios.get.mockResolvedValue({ data: { total: 5, notificaciones: [] } });

    render(<NotificationBadge />);

    await waitFor(() => {
      expect(screen.getByTestId("notification-badge")).toBeInTheDocument();
    });
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("5");
  });

  /**
   * Caso N = 99: badge debe mostrarse con valor 99
   */
  test("muestra el badge con valor 99 cuando total = 99", async () => {
    axios.get.mockResolvedValue({ data: { total: 99, notificaciones: [] } });

    render(<NotificationBadge />);

    await waitFor(() => {
      expect(screen.getByTestId("notification-badge")).toBeInTheDocument();
    });
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("99");
  });

  /**
   * Propiedad parametrizada: para todo N > 0 el badge aparece; para N = 0 se oculta.
   * Equivalente a un test de propiedad con valores representativos.
   */
  const casosConBadge = [1, 2, 3, 5, 10, 50, 99, 100];
  casosConBadge.forEach((n) => {
    test(`muestra badge cuando total = ${n} (N > 0)`, async () => {
      axios.get.mockResolvedValue({ data: { total: n, notificaciones: [] } });

      const { unmount } = render(<NotificationBadge />);

      await waitFor(() => {
        expect(screen.getByTestId("notification-badge")).toBeInTheDocument();
      });
      expect(screen.getByTestId("notification-badge")).toHaveTextContent(String(n));

      unmount();
    });
  });

  test("oculta badge cuando total = 0 (caso borde)", async () => {
    axios.get.mockResolvedValue({ data: { total: 0, notificaciones: [] } });

    render(<NotificationBadge />);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalled();
    });

    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument();
  });

  /**
   * Verifica que el polling se inicia: axios.get se llama al montar
   */
  test("llama a la API al montar el componente", async () => {
    axios.get.mockResolvedValue({ data: { total: 3, notificaciones: [] } });

    render(<NotificationBadge />);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining("/notificaciones/no-leidas"),
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: "Bearer fake-token" }),
        })
      );
    });
  });

  /**
   * Verifica que el polling se repite cada 30 segundos usando fake timers.
   * Se usa vi.useFakeTimers con shouldAdvanceTime para que waitFor funcione.
   */
  test("hace polling cada 30 segundos", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    axios.get.mockResolvedValue({ data: { total: 2, notificaciones: [] } });

    render(<NotificationBadge />);

    // Esperar la llamada inicial
    await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(1));

    // Avanzar 30 segundos
    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });
    await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(2));

    // Avanzar otros 30 segundos
    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });
    await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(3));
  });

  /**
   * Verifica que no hace polling si no hay token (usuario no autenticado)
   */
  test("no hace polling si el usuario no está autenticado", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const authService = await import("../services/authService");
    authService.default.getAccessToken.mockReturnValue(null);

    render(<NotificationBadge />);

    // Avanzar tiempo
    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });

    expect(axios.get).not.toHaveBeenCalled();
  });
});
