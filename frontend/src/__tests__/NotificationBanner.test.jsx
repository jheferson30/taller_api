/**
 * Tests para NotificationBanner
 *
 * Propiedad 14: Banner de renovación visible solo para ADMIN
 * Valida: Requisitos 8.1, 8.3, 8.4
 *
 * Con notificaciones RENOVACION_PLAN no leídas:
 *   - el banner se renderiza para ADMIN
 *   - el banner NO se renderiza para MECANICO
 *   - al hacer clic en cerrar, llama a PATCH /notificaciones/{id}/leer
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, test, expect, beforeEach, afterEach } from "vitest";
import axios from "axios";
import NotificationBanner from "../components/NotificationBanner";
import authService from "../services/authService";

// Mock axios
vi.mock("axios");

// Mock authService
vi.mock("../services/authService", () => ({
  default: {
    getAccessToken: vi.fn(),
    getUser: vi.fn(),
  },
}));

const NOTIFICACION_RENOVACION = {
  id: 42,
  tipo: "RENOVACION_PLAN",
  titulo: "Plan próximo a vencer",
  mensaje: "Tu plan vence en 2 días. Renueva para continuar.",
  leida: false,
  fecha_creacion: "2024-01-01T00:00:00Z",
  referencia_id: null,
};

describe("NotificationBanner — Propiedad 14: banner visible solo para ADMIN", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Restaurar usuario ADMIN por defecto antes de cada test
    authService.getUser.mockReturnValue({ username: "admin", roles: ["ADMIN"] });
    authService.getAccessToken.mockReturnValue("fake-token");
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ── Tests con notificaciones pasadas como prop ──────────────────────────────

  describe("con notificaciones pasadas como prop", () => {
    test("renderiza el banner para usuario ADMIN con notificación RENOVACION_PLAN no leída", () => {
      render(
        <NotificationBanner notificaciones={[NOTIFICACION_RENOVACION]} />
      );

      expect(screen.getByTestId("notification-banner")).toBeInTheDocument();
      expect(screen.getByText(/Tu plan vence en 2 días/i)).toBeInTheDocument();
    });

    test("NO renderiza el banner para usuario MECANICO aunque haya notificaciones RENOVACION_PLAN", () => {
      authService.getUser.mockReturnValue({ username: "mecanico1", roles: ["MECANICO"] });

      render(
        <NotificationBanner notificaciones={[NOTIFICACION_RENOVACION]} />
      );

      expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    });

    test("NO renderiza el banner cuando no hay notificaciones RENOVACION_PLAN", () => {
      const otraNotificacion = {
        id: 10,
        tipo: "TICKET_ASIGNADO",
        titulo: "Ticket asignado",
        mensaje: "Se te asignó el ticket #10",
        leida: false,
        fecha_creacion: "2024-01-01T00:00:00Z",
        referencia_id: 10,
      };

      render(<NotificationBanner notificaciones={[otraNotificacion]} />);

      expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    });

    test("NO renderiza el banner cuando la notificación RENOVACION_PLAN ya está leída", () => {
      const notifLeida = { ...NOTIFICACION_RENOVACION, leida: true };

      render(<NotificationBanner notificaciones={[notifLeida]} />);

      expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    });

    test("NO renderiza el banner cuando la lista de notificaciones está vacía", () => {
      render(<NotificationBanner notificaciones={[]} />);

      expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    });

    test("al hacer clic en cerrar, llama a PATCH /notificaciones/{id}/leer", async () => {
      axios.patch.mockResolvedValue({ data: { id: 42, leida: true } });

      render(
        <NotificationBanner notificaciones={[NOTIFICACION_RENOVACION]} />
      );

      expect(screen.getByTestId("notification-banner")).toBeInTheDocument();

      const botonCerrar = screen.getByLabelText(/cerrar banner/i);
      fireEvent.click(botonCerrar);

      await waitFor(() => {
        expect(axios.patch).toHaveBeenCalledWith(
          expect.stringContaining("/notificaciones/42/leer"),
          {},
          expect.objectContaining({
            headers: expect.objectContaining({ Authorization: "Bearer fake-token" }),
          })
        );
      });
    });

    test("al hacer clic en cerrar, oculta el banner sin recargar la página", async () => {
      axios.patch.mockResolvedValue({ data: { id: 42, leida: true } });

      render(
        <NotificationBanner notificaciones={[NOTIFICACION_RENOVACION]} />
      );

      expect(screen.getByTestId("notification-banner")).toBeInTheDocument();

      const botonCerrar = screen.getByLabelText(/cerrar banner/i);
      fireEvent.click(botonCerrar);

      await waitFor(() => {
        expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
      });
    });

    test("oculta el banner aunque falle el PATCH (no bloquea al usuario)", async () => {
      axios.patch.mockRejectedValue(new Error("Network error"));

      render(
        <NotificationBanner notificaciones={[NOTIFICACION_RENOVACION]} />
      );

      const botonCerrar = screen.getByLabelText(/cerrar banner/i);
      fireEvent.click(botonCerrar);

      await waitFor(() => {
        expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
      });
    });
  });

  // ── Tests con consulta interna (sin prop) ───────────────────────────────────

  describe("con consulta interna a la API", () => {
    test("renderiza el banner para ADMIN cuando la API retorna notificación RENOVACION_PLAN", async () => {
      axios.get.mockResolvedValue({
        data: {
          total: 1,
          notificaciones: [NOTIFICACION_RENOVACION],
        },
      });

      render(<NotificationBanner />);

      await waitFor(() => {
        expect(screen.getByTestId("notification-banner")).toBeInTheDocument();
      });
    });

    test("NO renderiza el banner para MECANICO aunque la API retorne notificaciones", () => {
      authService.getUser.mockReturnValue({ username: "mecanico1", roles: ["MECANICO"] });

      render(<NotificationBanner />);

      // Para MECANICO, el componente no llama a la API
      expect(axios.get).not.toHaveBeenCalled();
      expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    });

    test("NO renderiza el banner cuando la API no retorna notificaciones RENOVACION_PLAN", async () => {
      axios.get.mockResolvedValue({
        data: {
          total: 0,
          notificaciones: [],
        },
      });

      render(<NotificationBanner />);

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalled();
      });

      expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    });
  });

  // ── Propiedad 14 parametrizada: ADMIN vs MECANICO ──────────────────────────

  describe("Propiedad 14 — parametrizada por rol", () => {
    const casos = [
      { rol: "ADMIN", debeVer: true },
      { rol: "MECANICO", debeVer: false },
    ];

    casos.forEach(({ rol, debeVer }) => {
      test(`usuario con rol ${rol} ${debeVer ? "VE" : "NO VE"} el banner`, () => {
        authService.getUser.mockReturnValue({ username: "usuario1", roles: [rol] });

        render(
          <NotificationBanner notificaciones={[NOTIFICACION_RENOVACION]} />
        );

        if (debeVer) {
          expect(screen.getByTestId("notification-banner")).toBeInTheDocument();
        } else {
          expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
        }
      });
    });
  });
});
