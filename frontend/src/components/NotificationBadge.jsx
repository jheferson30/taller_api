import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { FiBell, FiCheck, FiCheckCircle } from "react-icons/fi";
import { api } from "../api";

const POLL_INTERVAL_MS = 30_000; // 30 segundos

export default function NotificationBadge({ onRefreshRef }) {
  const [total, setTotal] = useState(0);
  const [notificaciones, setNotificaciones] = useState([]);
  const [open, setOpen] = useState(false);
  const [marcando, setMarcando] = useState(null);
  const dropdownRef = useRef(null);

  const fetchNoLeidas = useCallback(async () => {
    try {
      const data = await api.obtenerNotificacionesNoLeidas();
      setTotal(data?.total ?? 0);
      setNotificaciones(data?.notificaciones ?? []);
    } catch (error) {
      // Silencioso — no romper la UI si falla
    }
  }, []);

  // Exponer refresh() al padre para que pueda forzar actualización
  useEffect(() => {
    if (onRefreshRef) onRefreshRef.current = fetchNoLeidas;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Polling — ejecutar inmediatamente al montar y cada 30 segundos
  useEffect(() => {
    fetchNoLeidas();
    const id = setInterval(fetchNoLeidas, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cerrar al hacer click fuera
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        // Verificar que no sea un clic dentro del modal
        const modalCard = document.querySelector('[data-notification-modal]');
        if (modalCard && modalCard.contains(e.target)) {
          return; // No cerrar si el clic es dentro del modal
        }
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  async function marcarLeida(id) {
    setMarcando(id);
    try {
      await api.marcarNotificacionLeida(id);
      setNotificaciones(prev =>
        prev.map(n => n.id === id ? { ...n, leida: true } : n)
      );
      setTotal(prev => Math.max(0, prev - 1));
    } catch (error) {
      // silencioso
    } finally {
      setMarcando(null);
    }
  }

  async function marcarTodasLeidas() {
    setMarcando("all");
    try {
      await api.marcarTodasNotificacionesLeidas();
      setNotificaciones(prev => prev.map(n => ({ ...n, leida: true })));
      setTotal(0);
      setOpen(false);
    } catch (error) {
      // silencioso
    } finally {
      setMarcando(null);
    }
  }

  // Solo mostrar en el dropdown las que NO son RENOVACION_PLAN (esas tienen su banner)
  const notifDropdown = notificaciones.filter((n) => n.tipo !== "RENOVACION_PLAN");
  const totalDropdown = notifDropdown.length;

  function formatFecha(fechaStr) {
    const d = new Date(fechaStr);
    const ahora = new Date();
    const diffMs = ahora - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "ahora";
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `hace ${diffH}h`;
    return d.toLocaleDateString("es-CO", { day: "numeric", month: "short" });
  }

  return (
    <span ref={dropdownRef} style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
      {/* Botón campana */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={total > 0 ? `${total} notificaciones no leídas` : "Sin notificaciones"}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          color: "inherit",
        }}
      >
        <FiBell size={20} />
        {total > 0 && (
          <span
            data-testid="notification-badge"
            style={{
              position: "absolute",
              top: -6,
              right: -8,
              background: "#ef4444",
              color: "#fff",
              borderRadius: "50%",
              minWidth: 16,
              height: 16,
              fontSize: "0.65rem",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 3px",
              lineHeight: 1,
            }}
          >
            {total}
          </span>
        )}
      </button>

      {/* Overlay + Modal — montado en document.body via portal para escapar del sidebar */}
      {open && createPortal(
        <>
          {/* Overlay oscuro */}
          <div
            onClick={(e) => {
              // Solo cerrar si el clic es en el overlay, no en el card
              if (e.target === e.currentTarget) {
                setOpen(false);
              }
            }}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.4)",
              zIndex: 9998,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Card centrado en el área de contenido (a la derecha del sidebar) */}
            <div
              data-notification-modal
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "min(380px, 90vw)",
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 12,
                boxShadow: "0 16px 48px rgba(0,0,0,0.6)",
                zIndex: 9999,
                overflow: "hidden",
              }}
            >
          {/* Header */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0.75rem 1rem",
            borderBottom: "1px solid #334155",
          }}>
            <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f1f5f9" }}>
              Notificaciones {totalDropdown > 0 && <span style={{ color: "#94a3b8", fontWeight: 400 }}>({totalDropdown})</span>}
            </span>
            {total > 0 && (
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Evitar que se cierre el modal
                  marcarTodasLeidas();
                }}
                disabled={marcando === "all"}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#f59e0b",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "2px 6px",
                  borderRadius: 4,
                }}
              >
                <FiCheckCircle size={13} />
                Leer todas
              </button>
            )}
          </div>

          {/* Lista — máx 4 visibles, scroll si hay más */}
          <div style={{ maxHeight: "calc(4 * 82px)", overflowY: "auto" }}>
            {notifDropdown.length === 0 ? (
              <div style={{ padding: "1.5rem 1rem", textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>
                Sin notificaciones pendientes
              </div>
            ) : (
              notifDropdown.map((n) => (
                <div
                  key={n.id}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "0.75rem",
                    padding: "0.75rem 1rem",
                    borderBottom: "1px solid #1e293b",
                    // Estilo diferente según si está leída o no (estilo Facebook)
                    background: n.leida ? "#0f172a" : "#1e3a5f",
                    transition: "background 0.15s",
                  }}
                >
                  {/* Punto azul para notificaciones NO leídas */}
                  {!n.leida && (
                    <span style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "#3b82f6",
                      marginTop: 6,
                      flexShrink: 0,
                    }} />
                  )}

                  {/* Ícono tipo */}
                  <span style={{
                    marginTop: 2,
                    fontSize: "1.1rem",
                    flexShrink: 0,
                  }}>
                    🔧
                  </span>

                  {/* Contenido */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ 
                      fontWeight: n.leida ? 400 : 600, 
                      fontSize: "0.82rem", 
                      color: "#f1f5f9", 
                      marginBottom: 2 
                    }}>
                      {n.titulo}
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "#94a3b8", lineHeight: 1.4, marginBottom: 4 }}>
                      {n.mensaje}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#475569" }}>
                      {formatFecha(n.fecha_creacion)}
                    </div>
                  </div>

                  {/* Botón marcar leída - solo mostrar si NO está leída */}
                  {!n.leida && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation(); // Evitar que se cierre el modal
                        marcarLeida(n.id);
                      }}
                      disabled={marcando === n.id}
                      title="Marcar como leída"
                      style={{
                        background: "none",
                        border: "1px solid #334155",
                        borderRadius: 6,
                        cursor: "pointer",
                        color: "#f59e0b",
                        padding: "4px 6px",
                        display: "flex",
                        alignItems: "center",
                        flexShrink: 0,
                        opacity: marcando === n.id ? 0.5 : 1,
                      }}
                    >
                      <FiCheck size={14} />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
          </div>
          </div>
        </>,
        document.body
      )}
    </span>
  );
}
