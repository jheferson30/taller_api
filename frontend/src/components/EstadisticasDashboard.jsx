import { useEffect, useState } from "react";
import { api } from "../api";

const formatMoney = (v) =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", minimumFractionDigits: 0 }).format(v || 0);

// Gráfico de columnas SVG
function GraficoColumnas({ datos, alto = 200 }) {
  if (!datos || datos.length === 0) return <p className="empty-state">Sin datos</p>;

  const maxVal = Math.max(...datos.map((d) => d.total), 1);
  const ancho = 700;
  const padX = 10;
  const padY = 24;
  const padBottom = 28; // espacio para etiquetas
  const areaAlto = alto - padY - padBottom;
  const n = datos.length;
  const esMes = n > 10;
  const slot = (ancho - padX * 2) / n;
  const barAncho = Math.max(4, slot - (esMes ? 3 : 5));
  // En modo mes mostrar etiqueta cada 5 días, en semana todas
  const mostrarLabel = (i) => esMes ? i % 5 === 0 || datos[i]?.fecha === new Date().toISOString().slice(0, 10) : true;

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="grafico-svg" preserveAspectRatio="xMidYMid meet">
      {/* Líneas guía horizontales */}
      {[0.25, 0.5, 0.75, 1].map((f) => {
        const y = padY + areaAlto - areaAlto * f;
        const val = maxVal * f;
        const valLabel = val >= 1000000 ? `${(val / 1000000).toFixed(1)}M` : val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val.toFixed(0);
        return (
          <g key={f}>
            <line x1={padX} x2={ancho - padX} y1={y} y2={y}
              stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4 3" />
            <text x={padX + 2} y={y - 3} fontSize="8" fill="#94a3b8">{valLabel}</text>
          </g>
        );
      })}

      {datos.map((d, i) => {
        const barH = Math.max(2, (d.total / maxVal) * areaAlto);
        const x = padX + i * slot + (slot - barAncho) / 2;
        const y = padY + areaAlto - barH;
        const dia = d.fecha ? d.fecha.slice(8) : ""; // solo DD
        const mes = d.fecha ? d.fecha.slice(5, 7) : "";
        const esHoy = d.fecha === new Date().toISOString().slice(0, 10);
        const labelY = padY + areaAlto + 12;

        return (
          <g key={i}>
            <rect
              x={x} y={y} width={barAncho} height={barH}
              rx={esMes ? 3 : 5}
              fill={esHoy ? "#1e40af" : "#3b82f6"}
              opacity={esHoy ? 1 : 0.7}
            >
              <title>{d.fecha}: {formatMoney(d.total)}</title>
            </rect>
            {/* Valor encima solo si la barra es suficientemente alta y no es modo mes */}
            {!esMes && barH > 22 && (
              <text x={x + barAncho / 2} y={y + 13} textAnchor="middle"
                fontSize="9" fill="white" fontWeight="600">
                {d.total >= 1000000 ? `${(d.total / 1000000).toFixed(1)}M` : d.total >= 1000 ? `${(d.total / 1000).toFixed(0)}k` : d.total}
              </text>
            )}
            {/* Etiqueta fecha — solo las que corresponde mostrar */}
            {mostrarLabel(i) && (
              <text x={x + barAncho / 2} y={labelY} textAnchor="middle"
                fontSize={esMes ? 8 : 9}
                fill={esHoy ? "#1e40af" : "#64748b"}
                fontWeight={esHoy ? "700" : "400"}>
                {esMes ? `${dia}/${mes}` : dia}
              </text>
            )}
            {/* Punto indicador para hoy en modo mes */}
            {esMes && esHoy && (
              <circle cx={x + barAncho / 2} cy={y - 5} r="3" fill="#1e40af" />
            )}
          </g>
        );
      })}
    </svg>
  );
}

// Barra horizontal con porcentaje
function BarraHorizontal({ label, valor, max, color = "#3b82f6", suffix = "" }) {
  const pct = max > 0 ? Math.min(100, (valor / max) * 100) : 0;
  return (
    <div className="barra-h-row">
      <div className="barra-h-label">{label}</div>
      <div className="barra-h-track">
        <div className="barra-h-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="barra-h-valor">{valor}{suffix}</div>
    </div>
  );
}

// Medallas para el podio
const MEDALLAS = ["🥇", "🥈", "🥉"];
const COLORES_MECANICO = ["#f59e0b", "#94a3b8", "#cd7c2f", "#3b82f6", "#8b5cf6"];

export default function EstadisticasDashboard() {
  const [periodo, setPeriodo] = useState("semana");
  const [datos, setDatos] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function cargar(p) {
    setLoading(true);
    setError("");
    try {
      const res = await api.economiaEstadisticas(p);
      setDatos(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargar(periodo); }, [periodo]);

  const totalPeriodo = datos?.ingresos_por_dia?.reduce((s, d) => s + d.total, 0) || 0;
  const maxServicios = datos?.servicios_frecuentes?.[0]?.cantidad || 1;
  const maxMecanicos = datos?.mecanicos_ranking?.[0]?.procesos || 1;

  return (
    <div className="estadisticas-dashboard">
      <div className="estadisticas-header">
        <div>
          <h3 className="estadisticas-titulo">Dashboard de Estadísticas</h3>
          <p className="estadisticas-sub">Análisis del período seleccionado</p>
        </div>        <div className="periodo-tabs">
          <button
            className={`periodo-btn ${periodo === "semana" ? "activo" : ""}`}
            onClick={() => setPeriodo("semana")}
          >
            Última semana
          </button>
          <button
            className={`periodo-btn ${periodo === "mes" ? "activo" : ""}`}
            onClick={() => setPeriodo("mes")}
          >
            Último mes
          </button>
        </div>
      </div>

      {loading && <div className="stats-loading"><span className="stats-spinner" />Cargando estadísticas...</div>}
      {error && <p className="stats-error">{error}</p>}

      {datos && !loading && (
        <>
          {/* Total período */}
          <div className="stats-total-badge">
            <span className="stats-total-label">Total ingresos ({periodo === "semana" ? "7 días" : "30 días"})</span>
            <strong className="stats-total-valor">{formatMoney(totalPeriodo)}</strong>
            <span className="stats-total-rango">{datos.fecha_desde} → {datos.fecha_hasta}</span>
          </div>

          <div className="stats-grid">
            {/* Gráfico de ingresos */}
            <div className="stats-card stats-card-wide">
              <h4 className="stats-card-title">Ingresos por día</h4>
              <GraficoColumnas datos={datos.ingresos_por_dia} />
              <p className="stats-chart-hint">Las barras azul oscuro indican el día de hoy</p>
            </div>

            {/* Top servicios */}
            <div className="stats-card">
              <h4 className="stats-card-title">Servicios más frecuentes</h4>
              {datos.servicios_frecuentes.length === 0 ? (
                <p className="empty-state">Sin datos en este período</p>
              ) : (
                <div className="barras-h-list">
                  {datos.servicios_frecuentes.map((s, i) => (
                    <BarraHorizontal
                      key={i}
                      label={s.servicio?.length > 28 ? s.servicio.slice(0, 28) + "…" : s.servicio}
                      valor={s.cantidad}
                      max={maxServicios}
                      color={`hsl(${210 + i * 25}, 70%, ${55 - i * 5}%)`}
                      suffix=" tickets"
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Ranking mecánicos */}
            <div className="stats-card">
              <h4 className="stats-card-title">Mecánicos más activos</h4>
              {datos.mecanicos_ranking.length === 0 ? (
                <p className="empty-state">Sin datos en este período</p>
              ) : (
                <div className="mecanicos-ranking">
                  {datos.mecanicos_ranking.map((m, i) => (
                    <div key={i} className={`mecanico-row ${i === 0 ? "mecanico-top" : ""}`}>
                      <span className="mecanico-medalla">{MEDALLAS[i] || `#${i + 1}`}</span>
                      <div className="mecanico-info">
                        <span className="mecanico-nombre">{m.mecanico}</span>
                        <div className="mecanico-barra-track">
                          <div
                            className="mecanico-barra-fill"
                            style={{
                              width: `${(m.procesos / maxMecanicos) * 100}%`,
                              background: COLORES_MECANICO[i] || "#64748b",
                            }}
                          />
                        </div>
                      </div>
                      <span className="mecanico-procesos">{m.procesos} proc.</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
