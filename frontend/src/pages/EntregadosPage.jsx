import { useState, useEffect } from "react";
import { api } from "../api";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || "";

const fmt = (v) =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", minimumFractionDigits: 0 }).format(v || 0);

function hoyLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function primerDiaMes() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

export default function EntregadosPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [placa, setPlaca] = useState("");
  const [fechaDesde, setFechaDesde] = useState(primerDiaMes());
  const [fechaHasta, setFechaHasta] = useState(hoyLocal());
  const [estado, setEstado] = useState("TODOS");
  const [selected, setSelected] = useState(null);

  const buscar = async () => {
    setLoading(true);
    setError("");
    setSelected(null);
    try {
      let data;
      if (estado === "TODOS") {
        // Buscar entregados y finalizados por separado y combinar
        const [entregados, finalizados] = await Promise.all([
          api.buscarTickets({ estado: "ENTREGADO", placa: placa.trim() || undefined, fecha_desde: fechaDesde || undefined, fecha_hasta: fechaHasta || undefined }),
          api.buscarTickets({ estado: "FINALIZADO", placa: placa.trim() || undefined, fecha_desde: fechaDesde || undefined, fecha_hasta: fechaHasta || undefined }),
        ]);
        data = [...entregados, ...finalizados].sort((a, b) => new Date(b.fecha_ingreso) - new Date(a.fecha_ingreso));
      } else {
        data = await api.buscarTickets({
          estado,
          placa: placa.trim() || undefined,
          fecha_desde: fechaDesde || undefined,
          fecha_hasta: fechaHasta || undefined,
        });
      }
      setTickets(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { buscar(); }, []);

  return (
    <div className="ent-page">
      {/* Header */}
      <div className="ent-hero">
        <div>
          <h1 className="ent-hero-title">Tickets Entregados</h1>
          <p className="ent-hero-sub">Historial completo de vehículos entregados al cliente</p>
        </div>
        <div className="ent-hero-badge">{tickets.length} registros</div>
      </div>

      {/* Filtros */}
      <div className="ent-filtros-card">
        <div className="ent-filtros-row">
          <div className="ent-field">
            <label className="ent-label">Placa</label>
            <input
              className="ent-input"
              type="text"
              placeholder="Ej: ABC123"
              value={placa}
              onChange={(e) => setPlaca(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && buscar()}
            />
          </div>
          <div className="ent-field">
            <label className="ent-label">Estado</label>
            <select className="ent-input" value={estado} onChange={(e) => setEstado(e.target.value)}>
              <option value="TODOS">Todos (Finalizados + Entregados)</option>
              <option value="FINALIZADO">Solo Finalizados</option>
              <option value="ENTREGADO">Solo Entregados</option>
            </select>
          </div>
          <div className="ent-field">
            <label className="ent-label">Desde</label>
            <input className="ent-input" type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
          </div>
          <div className="ent-field">
            <label className="ent-label">Hasta</label>
            <input className="ent-input" type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
          </div>
          <button className="ent-btn-buscar" onClick={buscar} disabled={loading}>
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </div>
      </div>

      {error && <div className="ent-error">{error}</div>}

      <div className="ent-layout">
        {/* Lista */}
        <div className="ent-lista">
          {loading && <div className="ent-loading">Cargando...</div>}
          {!loading && tickets.length === 0 && (
            <div className="ent-empty">
              <span className="ent-empty-icon">—</span>
              <p>No hay tickets entregados en este rango</p>
            </div>
          )}
          {tickets.map((t) => {
            const fecha = new Date(t.fecha_ingreso).toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric" });
            const isActive = selected?.id === t.id;
            return (
              <div
                key={t.id}
                className={`ent-card ${isActive ? "ent-card--active" : ""}`}
                onClick={() => setSelected(t)}
              >
                <div className="ent-card-top">
                  <span className="ent-placa">{t.placa}</span>
                  <span className={`ent-chip ent-chip--${t.estado.toLowerCase()}`}>{t.estado}</span>
                </div>
                <p className="ent-codigo">{t.ticket_codigo}</p>
                <p className="ent-motivo">{t.motivo_visita}</p>
                <div className="ent-card-footer">
                  <span>{t.nombre_propietario || "Sin propietario"}</span>
                  <span>{fecha}</span>
                </div>
                {t.total_servicio > 0 && (
                  <div className="ent-card-monto">{fmt(t.total_servicio)}</div>
                )}
              </div>
            );
          })}
        </div>

        {/* Detalle */}
        {selected ? (
          <div className="ent-detalle">
            <div className="ent-detalle-header">
              <div>
                <h2 className="ent-detalle-placa">{selected.placa}</h2>
                <p className="ent-detalle-codigo">{selected.ticket_codigo}</p>
              </div>
              <span className={`ent-chip ent-chip--lg ent-chip--${selected.estado.toLowerCase()}`}>{selected.estado}</span>
            </div>

            {/* Info vehículo */}
            <div className="ent-section">
              <h3 className="ent-section-title">Información</h3>
              <div className="ent-info-grid">
                <InfoItem label="Motivo" value={selected.motivo_visita} />
                <InfoItem label="Propietario" value={selected.nombre_propietario} />
                <InfoItem label="Teléfono" value={selected.telefono_propietario} />
                <InfoItem label="Recepcionado por" value={selected.recepcionado_por} />
                <InfoItem label="Confirmado por" value={selected.confirmado_entrega_por} />
                <InfoItem label="Próx. mantenimiento" value={selected.proximo_mantenimiento} />
                <InfoItem label="Fecha ingreso" value={new Date(selected.fecha_ingreso).toLocaleString("es-CO")} />
                {selected.fecha_entrega && (
                  <InfoItem label="Fecha entrega" value={new Date(selected.fecha_entrega).toLocaleString("es-CO")} />
                )}
              </div>
            </div>

            {/* Finanzas */}
            <div className="ent-section">
              <h3 className="ent-section-title">Finanzas</h3>
              <div className="ent-fin-grid">
                <FinCard label="Total Servicio" value={fmt(selected.total_servicio)} color="blue" />
                <FinCard label="Anticipo" value={fmt(selected.anticipo_recibido)} color="green" />
                <FinCard label="Saldo Pendiente" value={fmt(selected.saldo_pendiente)} color={selected.saldo_pendiente > 0 ? "orange" : "gray"} />
                {selected.metodo_pago_final && (
                  <FinCard label="Método de pago" value={selected.metodo_pago_final} color="gray" />
                )}
              </div>
            </div>

            {/* Observaciones */}
            {(selected.observaciones_finales || selected.recomendaciones) && (
              <div className="ent-section">
                <h3 className="ent-section-title">Notas</h3>
                {selected.observaciones_finales && (
                  <div className="ent-nota">
                    <span className="ent-nota-label">Observaciones finales</span>
                    <p>{selected.observaciones_finales}</p>
                  </div>
                )}
                {selected.recomendaciones && (
                  <div className="ent-nota">
                    <span className="ent-nota-label">Recomendaciones</span>
                    <p>{selected.recomendaciones}</p>
                  </div>
                )}
              </div>
            )}

            <button
              className="ent-pdf-btn"
              onClick={async () => {
                try {
                  const blob = await api.descargarPdfTicket(selected.id);
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `ticket-${selected.ticket_codigo || selected.id}.pdf`;
                  a.click();
                  window.URL.revokeObjectURL(url);
                } catch (err) {
                  alert("Error al descargar PDF: " + err.message);
                }
              }}
            >
              Descargar PDF del cliente
            </button>
          </div>
        ) : (
          <div className="ent-detalle-empty">
            <span>←</span>
            <p>Selecciona un ticket para ver el detalle</p>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoItem({ label, value }) {
  if (!value) return null;
  return (
    <div className="ent-info-item">
      <span className="ent-info-label">{label}</span>
      <span className="ent-info-value">{value}</span>
    </div>
  );
}

function FinCard({ label, value, color }) {
  return (
    <div className={`ent-fin-card ent-fin-card--${color}`}>
      <span className="ent-fin-label">{label}</span>
      <span className="ent-fin-value">{value}</span>
    </div>
  );
}
