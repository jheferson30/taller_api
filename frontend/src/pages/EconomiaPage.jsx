import { useEffect, useState } from "react";
import { api } from "../api";
import EconomiaAuth from "../components/EconomiaAuth";

export default function EconomiaPage() {
  const [autenticado, setAutenticado] = useState(false);
  const [tienePassword, setTienePassword] = useState(null);
  const [modoCrear, setModoCrear] = useState(false);
  const [resumen, setResumen] = useState(null);
  const [ingresos, setIngresos] = useState(null);
  const [egresos, setEgresos] = useState(null);
  const [msg, setMsg] = useState("");
  const [fecha, setFecha] = useState(new Date().toISOString().split("T")[0]);
  const [loading, setLoading] = useState(false);

  // Formatear moneda
  const formatMoney = (value) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(value || 0);
  };

  // Agrupar egresos por categoría
  const agruparEgresosPorCategoria = (egresos) => {
    const grupos = {};
    (egresos || []).forEach((e) => {
      const cat = e.categoria || "OTRO";
      if (!grupos[cat]) {
        grupos[cat] = { total: 0, items: [] };
      }
      grupos[cat].total += e.valor;
      grupos[cat].items.push(e);
    });
    return grupos;
  };

  async function load(fechaSeleccionada = fecha) {
    setLoading(true);
    setMsg("");
    try {
      const [r, i, e] = await Promise.all([
        api.economiaResumen(fechaSeleccionada),
        api.economiaIngresos(fechaSeleccionada),
        api.economiaEgresos(fechaSeleccionada),
      ]);
      setResumen(r);
      setIngresos(i);
      setEgresos(e);
    } catch (err) {
      setMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Verificar si ya tiene contraseña configurada
    api.verificarTienePassword()
      .then((res) => {
        setTienePassword(res.tiene_password);
        setModoCrear(!res.tiene_password);
      })
      .catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    if (autenticado) {
      load();
    }
  }, [autenticado]);

  async function onPdf() {
    setMsg("");
    try {
      const blob = await api.descargarPdfEconomia(fecha);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `economia-${fecha}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      setMsg("✓ PDF descargado correctamente");
    } catch (err) {
      setMsg("✗ " + err.message);
    }
  }

  const handleFechaChange = (e) => {
    const nuevaFecha = e.target.value;
    setFecha(nuevaFecha);
    load(nuevaFecha);
  };

  const egresosPorCategoria = agruparEgresosPorCategoria(egresos?.egresos);

  // Si no está autenticado, mostrar pantalla de login/crear
  if (tienePassword === null) {
    return (
      <section className="economia-page">
        <p className="loading">Verificando configuración de seguridad...</p>
      </section>
    );
  }

  if (!autenticado) {
    return (
      <EconomiaAuth
        onAutenticado={() => setAutenticado(true)}
        modoInicial={modoCrear ? "crear" : "login"}
      />
    );
  }

  return (
    <section className="economia-page">
      <div className="economia-header">
        <div>
          <h2>Economía del Día</h2>
          <p className="subtitle">Ingresos, egresos y resultado diario</p>
        </div>
        <div className="fecha-selector">
          <label>Fecha:</label>
          <input
            type="date"
            value={fecha}
            onChange={handleFechaChange}
            max={new Date().toISOString().split("T")[0]}
          />
        </div>
      </div>

      {loading && <p className="loading">Cargando datos...</p>}

      {/* KPIs principales */}
      <div className="kpis-economia">
        <article className="kpi-card ingreso">
          <div className="kpi-icon">💰</div>
          <div className="kpi-content">
            <span className="kpi-label">Ingresos</span>
            <strong className="kpi-value">{formatMoney(resumen?.ingresos)}</strong>
            <small className="kpi-detail">
              Anticipos: {formatMoney(resumen?.ingreso_anticipo)} | 
              Finales: {formatMoney(resumen?.ingreso_final)}
            </small>
          </div>
        </article>

        <article className="kpi-card egreso">
          <div className="kpi-icon">💸</div>
          <div className="kpi-content">
            <span className="kpi-label">Egresos</span>
            <strong className="kpi-value">{formatMoney(resumen?.egresos)}</strong>
            <small className="kpi-detail">
              {egresos?.egresos?.length || 0} movimientos
            </small>
          </div>
        </article>

        <article className={`kpi-card balance ${(resumen?.balance || 0) >= 0 ? 'positivo' : 'negativo'}`}>
          <div className="kpi-icon">{(resumen?.balance || 0) >= 0 ? '📈' : '📉'}</div>
          <div className="kpi-content">
            <span className="kpi-label">Balance</span>
            <strong className="kpi-value">{formatMoney(resumen?.balance)}</strong>
            <small className="kpi-detail">
              Tickets cerrados: {resumen?.tickets_cerrados_hoy || 0}
            </small>
          </div>
        </article>
      </div>

      {/* Gráfico simple de barras */}
      <div className="grafico-simple">
        <h3>Comparación Visual</h3>
        <div className="barras">
          <div className="barra-container">
            <div className="barra-label">Ingresos</div>
            <div className="barra-wrapper">
              <div 
                className="barra ingreso-bar" 
                style={{
                  width: `${Math.min(100, ((resumen?.ingresos || 0) / Math.max(resumen?.ingresos || 1, resumen?.egresos || 1)) * 100)}%`
                }}
              >
                {formatMoney(resumen?.ingresos)}
              </div>
            </div>
          </div>
          <div className="barra-container">
            <div className="barra-label">Egresos</div>
            <div className="barra-wrapper">
              <div 
                className="barra egreso-bar" 
                style={{
                  width: `${Math.min(100, ((resumen?.egresos || 0) / Math.max(resumen?.ingresos || 1, resumen?.egresos || 1)) * 100)}%`
                }}
              >
                {formatMoney(resumen?.egresos)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Detalle de movimientos */}
      <div className="grid two top-gap">
        <article className="card detalle-ingresos">
          <h3>📥 Detalle de Ingresos</h3>
          
          <div className="seccion-movimientos">
            <h4>Anticipos Recibidos ({ingresos?.anticipos?.length || 0})</h4>
            <div className="list">
              {(ingresos?.anticipos || []).length === 0 ? (
                <p className="empty-state">No hay anticipos registrados</p>
              ) : (
                (ingresos?.anticipos || []).map((x) => (
                  <div key={x.id} className="list-row ingreso-item">
                    <div className="item-main">
                      <strong>{x.ticket_codigo}</strong>
                      <span className="placa-badge">{x.placa}</span>
                    </div>
                    <div className="item-details">
                      <span className="metodo-pago">{x.metodo_pago || 'N/A'}</span>
                      <span className="responsable">{x.responsable || 'N/A'}</span>
                    </div>
                    <strong className="valor-ingreso">{formatMoney(x.valor_anticipo)}</strong>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="seccion-movimientos">
            <h4>Cobros Finales ({ingresos?.cobros_finales?.length || 0})</h4>
            <div className="list">
              {(ingresos?.cobros_finales || []).length === 0 ? (
                <p className="empty-state">No hay cobros finales registrados</p>
              ) : (
                (ingresos?.cobros_finales || []).map((x) => (
                  <div key={x.id} className="list-row ingreso-item">
                    <div className="item-main">
                      <strong>{x.ticket_codigo}</strong>
                      <span className="placa-badge">{x.placa}</span>
                    </div>
                    <div className="item-details">
                      <span className="metodo-pago">{x.metodo_pago || 'N/A'}</span>
                      <span className="responsable">{x.responsable || 'N/A'}</span>
                    </div>
                    <strong className="valor-ingreso">{formatMoney(x.valor_final_cobrado)}</strong>
                  </div>
                ))
              )}
            </div>
          </div>
        </article>

        <article className="card detalle-egresos">
          <h3>📤 Detalle de Egresos</h3>
          
          {/* Totales por categoría */}
          <div className="categorias-resumen">
            <h4>Por Categoría</h4>
            <div className="categorias-grid">
              {Object.entries(egresosPorCategoria).map(([cat, data]) => (
                <div key={cat} className="categoria-item">
                  <span className="cat-nombre">{cat}</span>
                  <strong className="cat-total">{formatMoney(data.total)}</strong>
                  <small className="cat-count">{data.items.length} mov.</small>
                </div>
              ))}
            </div>
          </div>

          {/* Lista detallada */}
          <div className="seccion-movimientos">
            <h4>Todos los Egresos ({egresos?.egresos?.length || 0})</h4>
            <div className="list">
              {(egresos?.egresos || []).length === 0 ? (
                <p className="empty-state">No hay egresos registrados</p>
              ) : (
                (egresos?.egresos || []).map((x) => (
                  <div key={x.id} className="list-row egreso-item">
                    <div className="item-main">
                      <strong className="categoria-badge">{x.categoria || "OTRO"}</strong>
                      <span>{x.concepto}</span>
                    </div>
                    <div className="item-details">
                      {x.ticket_codigo && <span className="ticket-ref">{x.ticket_codigo}</span>}
                      {x.placa && <span className="placa-badge">{x.placa}</span>}
                      <span className="responsable">{x.responsable || 'N/A'}</span>
                    </div>
                    <strong className="valor-egreso">{formatMoney(x.valor)}</strong>
                  </div>
                ))
              )}
            </div>
          </div>
        </article>
      </div>

      {/* Sección de descarga de PDF mejorada */}
      <div className="pdf-section">
        <div className="pdf-card">
          <div className="pdf-info">
            <h3>📄 Generar Reporte PDF</h3>
            <p>Descarga el informe completo del día con todos los movimientos</p>
          </div>
          <div className="pdf-actions">
            <button onClick={onPdf} className="btn-pdf">
              📥 Descargar PDF
            </button>
          </div>
        </div>
      </div>

      {msg && <p className={`status ${msg.startsWith('✓') ? 'success' : 'error'}`}>{msg}</p>}
    </section>
  );
}
