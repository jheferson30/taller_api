import { useState, useEffect } from "react";
import axios from "axios";
import authService from "../services/authService";

const API_BASE =
  import.meta.env.VITE_API_URL !== undefined
    ? import.meta.env.VITE_API_URL
    : import.meta.env.MODE === "production"
    ? ""
    : "http://127.0.0.1:8000";

/**
 * Banner de renovación de plan.
 * Solo visible para usuarios con rol ADMIN cuando tienen notificaciones
 * de tipo RENOVACION_PLAN no leídas.
 *
 * Props:
 *   notificaciones (optional): lista de notificaciones ya cargadas.
 *     Si no se pasa, el componente las consulta internamente.
 */
export default function NotificationBanner({ notificaciones: notificacionesProp }) {
  const [notificacion, setNotificacion] = useState(null);
  const [visible, setVisible] = useState(false);

  const user = authService.getUser();
  const isAdmin = user?.roles?.includes("ADMIN") ?? false;

  useEffect(() => {
    if (!isAdmin) return;

    if (notificacionesProp) {
      // Usar las notificaciones pasadas como prop
      const renovacion = notificacionesProp.find(
        (n) => n.tipo === "RENOVACION_PLAN" && !n.leida
      );
      if (renovacion) {
        setNotificacion(renovacion);
        setVisible(true);
      }
      return;
    }

    // Consultar internamente si no se pasan como prop
    const token = authService.getAccessToken();
    if (!token) return;

    axios
      .get(`${API_BASE}/notificaciones/no-leidas`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((response) => {
        const lista = response.data?.notificaciones ?? [];
        const renovacion = lista.find(
          (n) => n.tipo === "RENOVACION_PLAN" && !n.leida
        );
        if (renovacion) {
          setNotificacion(renovacion);
          setVisible(true);
        }
      })
      .catch(() => {
        // Silenciar errores de red
      });
  }, [isAdmin, notificacionesProp]);

  async function handleCerrar() {
    if (!notificacion) return;

    const token = authService.getAccessToken();
    try {
      await axios.patch(
        `${API_BASE}/notificaciones/${notificacion.id}/leer`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch {
      // Ocultar el banner de todas formas para no bloquear al usuario
    } finally {
      setVisible(false);
    }
  }

  // No renderizar si no es ADMIN o no hay notificación visible
  if (!isAdmin || !visible || !notificacion) return null;

  return (
    <div
      data-testid="notification-banner"
      role="alert"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 1000,
        background: "#fef3c7",
        borderBottom: "1px solid #f59e0b",
        color: "#92400e",
        padding: "0.6rem 1rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "1rem",
        fontSize: "0.875rem",
      }}
    >
      <span>⚠️ {notificacion.mensaje}</span>
      <button
        onClick={handleCerrar}
        aria-label="Cerrar banner de renovación"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontWeight: 700,
          fontSize: "1rem",
          color: "#92400e",
          padding: "0 0.25rem",
          lineHeight: 1,
        }}
      >
        ✕
      </button>
    </div>
  );
}
