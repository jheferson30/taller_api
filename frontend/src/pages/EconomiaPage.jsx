import { useEffect, useState } from "react";
import { api } from "../api";
import EstadisticasDashboard from "../components/EstadisticasDashboard";
import PageHero from "../components/PageHero";

export default function EconomiaPage() {
  const [resumen, setResumen] = useState(null);
  const [ingresos, setIngresos] = useState(null);
  const [egresos, setEgresos] = useState(null);
  const [msg, setMsg] = useState("");
  const hoyLocal = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  };
  const [fecha, setFecha] = useState(hoyLocal());
  const [loading, setLoading] = useState(false);

  const formatMoney = (value) =>
    new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", minimumFractionDigits: 0 }).format(value || 0);

  const agruparEgresosPorCategoria = (lista) => {
    const grupos = {};
    (lista || []).forEach((e) => {
      const cat = e.categoria || "OTRO";
      if (!grupos[cat]) grupos[cat] = { total: 0, items: [] };
      grupos[cat].total += e.valor;
      grupos[cat].items.push(e);
    });
    return grupos;
  };

  async function load(fechaSeleccionada = fecha) {
    setLoading(true); setMsg("");
    try {
      const [r, i, e] = await Promise.all([
        api.economiaResumen(fechaSeleccionada),
        api.economiaIngresos(fechaSeleccionada),
        api.economiaEgresos(fechaSeleccionada),
      ]);
      setResumen(r); setIngresos(i); setEgresos(e);
    } catch (err) { setMsg(err.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function onPdf() {
    setMsg("");
    try {
      const blob = await api.descargarPdfEconomia(fecha);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `economia-${fecha}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
      setMsg("correcto");
    } catch (err) { setMsg("error: " + err.message); }
  }

  const handleFechaChange = (e) => { setFecha(e.target.value); load(e.target.value); };
  const egresosPorCategoria = agruparEgresosPorCategoria(egresos?.egresos);

  return (
    <>
      <PageHero
        titulo="Economía del Día"
        subtitulo="Ingresos, egresos y resultado diario"
        action={
          <div className="fecha-selector">
            <label>Fecha:</label>
            <input type="date" value={fecha} onChange={handleFechaChange} max={new Date().toISOString().split("T")[0]} />
          </div>
        }
      />
      <section className="economia-page">
      {loading && <p className="loading">Cargando...</p>}
      <div className="kpis-economia">
        <article className="kpi-card ingreso">
          <div className="kpi-icon">$</div>
          <div className="kpi-content">
            <span className="kpi-label">Ingresos</span>
            <strong className="kpi-value">{formatMoney(resumen?.ingresos)}</strong>
            <small className="kpi-detail">Anticipos: {formatMoney(resumen?.ingreso_anticipo)} | Finales: {formatMoney(resumen?.ingreso_final)} | Rapidos: {formatMoney(resumen?.ingreso_rapido)}</small>
          </div>
        </article>
        <article className="kpi-card egreso">
          <div className="kpi-icon">-$</div>
          <div className="kpi-content">
            <span className="kpi-label">Egresos</span>
            <strong className="kpi-value">{formatMoney(resumen?.egresos)}</strong>
            <small className="kpi-detail">{egresos?.egresos?.length || 0} movimientos</small>
          </div>
        </article>
        <article className={`kpi-card balance ${(resumen?.balance || 0) >= 0 ? 'positivo' : 'negativo'}`}>
          <div className="kpi-content">
            <span className="kpi-label">GANANCIA DEL DIA</span>
            <strong className="kpi-value">{formatMoney(resumen?.balance)}</strong>
            <small className="kpi-detail">{resumen?.tickets_cerrados_hoy || 0} tickets cerrados</small>
          </div>
        </article>
      </div>
      <div className="grafico-simple">
        <h3>Comparacion Visual</h3>
        <div className="barras">
          {(() => {
            const ing = resumen?.ingresos || 0; const egr = resumen?.egresos || 0;
            const gan = Math.max(0, ing - egr); const maxVal = Math.max(ing, egr, gan, 1);
            return (<>
              <div className="barra-container"><div className="barra-label">Ingresos</div><div className="barra-wrapper"><div className="barra ingreso-bar" style={{ width: `${Math.min(100,(ing/maxVal)*100)}%` }}>{formatMoney(ing)}</div></div></div>
              <div className="barra-container"><div className="barra-label">Egresos</div><div className="barra-wrapper"><div className="barra egreso-bar" style={{ width: `${Math.min(100,(egr/maxVal)*100)}%` }}>{formatMoney(egr)}</div></div></div>
              <div className="barra-container"><div className="barra-label">Ganancia</div><div className="barra-wrapper"><div className="barra ganancia-bar" style={{ width: `${Math.min(100,(gan/maxVal)*100)}%` }}>{formatMoney(gan)}</div></div></div>
            </>);
          })()}
        </div>
      </div>
      <div className="grid two top-gap">
        <article className="card detalle-ingresos">
          <h3>Detalle de Ingresos</h3>
          <div className="seccion-movimientos">
            <h4>Anticipos ({ingresos?.anticipos?.length || 0})</h4>
            <div className="list">{(ingresos?.anticipos||[]).length===0?<p className="empty-state">Sin anticipos</p>:(ingresos?.anticipos||[]).map((x)=>(<div key={x.id} className="list-row ingreso-item"><div className="item-main"><strong>{x.ticket_codigo}</strong><span className="placa-badge">{x.placa}</span></div><div className="item-details"><span className="metodo-pago">{x.metodo_pago||'N/A'}</span><span className="responsable">{x.responsable||'N/A'}</span></div><strong className="valor-ingreso">{formatMoney(x.valor_anticipo)}</strong></div>))}</div>
          </div>
          <div className="seccion-movimientos">
            <h4>Cobros Finales ({ingresos?.cobros_finales?.length || 0})</h4>
            <div className="list">{(ingresos?.cobros_finales||[]).length===0?<p className="empty-state">Sin cobros finales</p>:(ingresos?.cobros_finales||[]).map((x)=>(<div key={x.id} className="list-row ingreso-item"><div className="item-main"><strong>{x.ticket_codigo}</strong><span className="placa-badge">{x.placa}</span></div><div className="item-details"><span className="metodo-pago">{x.metodo_pago||'N/A'}</span><span className="responsable">{x.responsable||'N/A'}</span></div><strong className="valor-ingreso">{formatMoney(x.valor_final_cobrado)}</strong></div>))}</div>
          </div>
          <div className="seccion-movimientos">
            <h4>Cobros Rapidos ({ingresos?.cobros_rapidos?.length || 0})</h4>
            <div className="list">{(ingresos?.cobros_rapidos||[]).length===0?<p className="empty-state">Sin cobros rapidos</p>:(ingresos?.cobros_rapidos||[]).map((x)=>(<div key={x.id} className="list-row ingreso-item"><div className="item-main"><span className="placa-badge">{x.placa}</span><span>{x.descripcion}</span></div><div className="item-details"><span className="metodo-pago">{x.metodo_pago||'N/A'}</span></div><strong className="valor-ingreso">{formatMoney(x.valor)}</strong></div>))}</div>
          </div>
        </article>
        <article className="card detalle-egresos">
          <h3>Detalle de Egresos</h3>
          <div className="categorias-resumen">
            <h4>Por Categoria</h4>
            <div className="categorias-grid">{Object.entries(egresosPorCategoria).map(([cat,data])=>(<div key={cat} className="categoria-item"><span className="cat-nombre">{cat}</span><strong className="cat-total">{formatMoney(data.total)}</strong><small className="cat-count">{data.items.length} mov.</small></div>))}</div>
          </div>
          <div className="seccion-movimientos">
            <h4>Todos los Egresos ({egresos?.egresos?.length || 0})</h4>
            <div className="list">{(egresos?.egresos||[]).length===0?<p className="empty-state">Sin egresos</p>:(egresos?.egresos||[]).map((x)=>(<div key={x.id} className="list-row egreso-item"><div className="item-main"><strong className="categoria-badge">{x.categoria||"OTRO"}</strong><span>{x.concepto}</span></div><div className="item-details">{x.ticket_codigo&&<span className="ticket-ref">{x.ticket_codigo}</span>}{x.placa&&<span className="placa-badge">{x.placa}</span>}<span className="responsable">{x.responsable||'N/A'}</span></div><strong className="valor-egreso">{formatMoney(x.valor)}</strong></div>))}</div>
          </div>
        </article>
      </div>
      <EstadisticasDashboard />
      <div className="pdf-section">
        <div className="pdf-card">
          <div className="pdf-info"><h3>Generar Reporte PDF</h3><p>Descarga el informe completo del dia</p></div>
          <div className="pdf-actions"><button onClick={onPdf} className="btn-pdf">Descargar PDF</button></div>
        </div>
      </div>
      {msg && <p className={`status ${msg.startsWith('correcto') ? 'success' : 'error'}`}>{msg}</p>}
    </section>
    </>
  );
}

