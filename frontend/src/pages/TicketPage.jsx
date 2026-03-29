import { useEffect, useState } from "react";
import { api } from "../api";
import InputDinero from "../components/InputDinero";
import SelectMecanico from "../components/SelectMecanico";

const PROCESOS_RAPIDOS_DEFAULT = [
  "Cambio de aceite",
  "Mantenimiento de frenos",
  "Cambio de cunas de diracion",
  "Mantenimiento de suspensión",
  "Cambio de kit de arrastre",
  "Cambio de refrigerante",
  "Cambio de líquido de frenos",
  "Mantenimiento preventivo",
  "Mantenimiento correctivo",
  "Mantenimiento general",
];

export default function TicketPage() {
  const [tickets, setTickets] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [resumen, setResumen] = useState(null);
  const [activeTab, setActiveTab] = useState("procesos");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [procesosRapidos, setProcesosRapidos] = useState(PROCESOS_RAPIDOS_DEFAULT);
  const [cobrosRapidos, setCobrosRapidos] = useState([]);

  // Forms
  const [proceso, setProceso] = useState({ nombre: "", descripcion: "", mecanico: "" });
  const [repuesto, setRepuesto] = useState({ nombre: "", cantidad: 1, marca_referencia: "" });
  const [fueComprado, setFueComprado] = useState(false);
  const [compraRepuesto, setCompraRepuesto] = useState({ valor: 0, responsable: "", nota: "" });
  const [compraRepuestoFile, setCompraRepuestoFile] = useState(null);
  const [foto, setFoto] = useState({ tipo: "OTRA", archivo_url: "", descripcion: "" });
  const [fotoFile, setFotoFile] = useState(null);
  const [fotoPreview, setFotoPreview] = useState("");
  const [compra, setCompra] = useState({ descripcion: "", valor: 0, soporte_url: "", nota: "", responsable: "" });
  const [compraFile, setCompraFile] = useState(null);
  const [cobro, setCobro] = useState({ concepto: "", valor: 0 });
  const [finanzas, setFinanzas] = useState({ total_servicio: 0, metodo_pago_final: "EFECTIVO" });
  const [observaciones, setObservaciones] = useState({ observaciones_finales: "", recomendaciones: "", proximo_mantenimiento: "" });
  const [entrega, setEntrega] = useState({ confirmado_entrega_por: "", firma_entrega_url: "" });

  async function loadTickets() {
    try {
      const data = await api.ticketsAbiertos();
      setTickets(data);
      if (!selectedId && data.length) {
        setSelectedId(data[0].id);
      }
    } catch (e) {
      setMsg("Error al cargar tickets: " + e.message);
    }
  }

  async function loadResumen(ticketId) {
    if (!ticketId) return;
    try {
      const data = await api.ticketResumen(ticketId);
      setResumen(data);
      // Pre-cargar finanzas si existen
      if (data.ticket.total_servicio) {
        setFinanzas({
          total_servicio: data.ticket.total_servicio,
          metodo_pago_final: data.ticket.metodo_pago_final || "EFECTIVO"
        });
      }
    } catch (e) {
      setMsg("Error al cargar resumen: " + e.message);
    }
  }

  useEffect(() => {
    loadTickets();
    api.obtenerProcesosRapidos().then((r) => { if (r.procesos?.length) setProcesosRapidos(r.procesos); }).catch(() => {});
    api.obtenerCobrosRapidos().then((r) => { if (r.cobros?.length) setCobrosRapidos(r.cobros); }).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedId) {
      loadResumen(selectedId);
    }
  }, [selectedId]);

  async function onAddProceso() {
    if (!proceso.nombre) return;
    setLoading(true);
    try {
      let foto_url = null;
      if (fotoFile) {
        const uploadResult = await api.subirFoto(fotoFile);
        foto_url = uploadResult.url; // ruta relativa como /uploads/...
        setFotoFile(null);
        setFotoPreview("");
      }
      await api.agregarProceso(selectedId, { ...proceso, foto_url });
      setProceso({ nombre: "", descripcion: "", mecanico: "" });
      await loadResumen(selectedId);
      setMsg("✓ Proceso agregado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onAddRepuesto() {
    if (!repuesto.nombre) return;
    setLoading(true);
    try {
      // Subir foto primero si hay archivo
      let foto_url = null;
      if (compraRepuestoFile) {
        const uploadResult = await api.subirFoto(compraRepuestoFile);
        foto_url = uploadResult.url;
      }

      await api.agregarRepuesto(selectedId, { ...repuesto, foto_url });

      if (fueComprado && Number(compraRepuesto.valor) > 0) {
        await api.agregarCompra(selectedId, {
          descripcion: repuesto.nombre,
          valor: Number(compraRepuesto.valor),
          responsable: compraRepuesto.responsable || null,
          nota: compraRepuesto.nota || null,
          soporte_url: foto_url ? `${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}${foto_url}` : null,
        });
      }

      setRepuesto({ nombre: "", cantidad: 1, marca_referencia: "" });
      setFueComprado(false);
      setCompraRepuesto({ valor: 0, responsable: "", nota: "" });
      setCompraRepuestoFile(null);
      await loadResumen(selectedId);
      setMsg("✓ Repuesto agregado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onAddFoto() {
    if (!foto.archivo_url && !fotoFile) return;
    setLoading(true);
    try {
      let fotoUrl = foto.archivo_url;
      
      // Si hay un archivo, subirlo primero
      if (fotoFile) {
        const uploadResult = await api.subirFoto(fotoFile);
        fotoUrl = `http://127.0.0.1:8000${uploadResult.url}`;
      }
      
      await api.agregarFoto(selectedId, { ...foto, archivo_url: fotoUrl });
      setFoto({ tipo: "OTRA", archivo_url: "", descripcion: "" });
      setFotoFile(null);
      setFotoPreview("");
      await loadResumen(selectedId);
      setMsg("✓ Foto agregada");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  function onFotoFileChange(e) {
    const file = e.target.files[0];
    if (file) {
      setFotoFile(file);
      // Crear preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setFotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  }

  async function onAddCompra() {
    if (!compra.descripcion || !compra.valor) return;
    setLoading(true);
    try {
      let soporteUrl = compra.soporte_url;
      
      // Si hay un archivo, subirlo primero
      if (compraFile) {
        const uploadResult = await api.subirSoporteCompra(compraFile);
        soporteUrl = `http://127.0.0.1:8000${uploadResult.url}`;
      }
      
      await api.agregarCompra(selectedId, { ...compra, valor: Number(compra.valor), soporte_url: soporteUrl });
      setCompra({ descripcion: "", valor: 0, soporte_url: "", nota: "", responsable: "" });
      setCompraFile(null);
      await loadResumen(selectedId);
      setMsg("✓ Compra registrada");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  function onCompraFileChange(e) {
    const file = e.target.files[0];
    if (file) {
      setCompraFile(file);
    }
  }

  async function onDeleteFoto(fotoId) {
    if (!confirm("¿Eliminar esta foto?")) return;
    setLoading(true);
    try {
      await api.eliminarFoto(selectedId, fotoId);
      await loadResumen(selectedId);
      setMsg("✓ Foto eliminada");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteProceso(procesoId) {
    if (!confirm("¿Eliminar este proceso?")) return;
    setLoading(true);
    try {
      await api.eliminarProceso(selectedId, procesoId);
      await loadResumen(selectedId);
      setMsg("✓ Proceso eliminado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteCompra(compraId) {
    if (!confirm("¿Eliminar esta compra?")) return;
    setLoading(true);
    try {
      await api.eliminarCompra(selectedId, compraId);
      await loadResumen(selectedId);
      setMsg("✓ Compra eliminada");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteRepuesto(repuestoId) {
    if (!confirm("¿Eliminar este repuesto?")) return;
    setLoading(true);
    try {
      await api.eliminarRepuesto(selectedId, repuestoId);
      await loadResumen(selectedId);
      setMsg("✓ Repuesto eliminado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onAddCobro(conceptoOverride, valorOverride) {
    const concepto = conceptoOverride ?? cobro.concepto;
    const valor = valorOverride ?? cobro.valor;
    if (!concepto || !valor) return;
    setLoading(true);
    try {
      await api.agregarCobro(selectedId, { concepto, valor: Number(valor) });
      if (!conceptoOverride) setCobro({ concepto: "", valor: 0 });
      await loadResumen(selectedId);
      
      // Actualizar el total automáticamente
      const totalCobros = [...resumen.cobros, { valor: Number(valor) }].reduce((sum, c) => sum + c.valor, 0);
      setFinanzas({ ...finanzas, total_servicio: totalCobros });
      
      setMsg("✓ Cobro agregado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteCobro(cobroId) {
    if (!confirm("¿Eliminar este cobro?")) return;
    setLoading(true);
    try {
      await api.eliminarCobro(selectedId, cobroId);
      await loadResumen(selectedId);
      setMsg("✓ Cobro eliminado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onUpdateFinanzas() {
    if (!finanzas.total_servicio) return;
    setLoading(true);
    try {
      await api.actualizarFinanzas(selectedId, { ...finanzas, total_servicio: Number(finanzas.total_servicio) });
      await loadResumen(selectedId);
      setMsg("✓ Finanzas actualizadas");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onFinalizar() {
    if (!resumen?.ticket.total_servicio) {
      setMsg("✗ Por favor define el total del servicio antes de finalizar");
      setTimeout(() => setMsg(""), 4000);
      setActiveTab("finanzas");
      return;
    }
    if (!confirm("¿Finalizar este ticket?")) return;
    setLoading(true);
    try {
      await api.finalizarTicket(selectedId);
      await loadResumen(selectedId);
      await loadTickets();
      setMsg("✓ Ticket finalizado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onEntregar() {
    if (!entrega.confirmado_entrega_por) {
      setMsg("✗ Debes ingresar quién confirma la entrega");
      return;
    }
    setLoading(true);
    try {
      await api.entregarTicket(selectedId, { ...entrega, ...observaciones });
      await loadResumen(selectedId);
      await loadTickets();
      setEntrega({ confirmado_entrega_por: "", firma_entrega_url: "" });
      setMsg("✓ Ticket marcado como entregado");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  const isEditable = resumen?.ticket.estado === "ABIERTO" || resumen?.ticket.estado === "EN_PROCESO";
  const isFinalizado = resumen?.ticket.estado === "FINALIZADO";
  const isEntregado = resumen?.ticket.estado === "ENTREGADO";

  return (
    <section className="ticket-container">
      <div className="ticket-header">
        <h2>Gestión de Tickets</h2>
        <p className="subtitle">Control técnico del mantenimiento</p>
      </div>

      <div className="ticket-layout">
        {/* SIDEBAR - Lista de tickets */}
        <aside className="ticket-sidebar">
          <h3 className="sidebar-title">Tickets Activos ({tickets.length})</h3>
          <div className="ticket-list">
            {tickets.length === 0 && (
              <p className="empty-state">No hay tickets activos</p>
            )}
            {tickets.map((t) => (
              <button
                key={t.id}
                className={`ticket-item ${selectedId === t.id ? "active" : ""}`}
                onClick={() => setSelectedId(t.id)}
              >
                <div className="ticket-item-header">
                  <strong className="ticket-code">{t.ticket_codigo}</strong>
                  <span className={`badge badge-${t.estado.toLowerCase()}`}>{t.estado}</span>
                </div>
                <div className="ticket-item-info">
                  <span className="ticket-placa">{t.placa}</span>
                  <span className="ticket-motivo">{t.motivo_visita}</span>
                </div>
                <div className="ticket-item-fecha">
                  <span className="fecha-hora">
                    {new Date(t.fecha_ingreso).toLocaleDateString('es-CO', { 
                      day: '2-digit', 
                      month: '2-digit', 
                      year: 'numeric' 
                    })}
                    {' '}
                    {new Date(t.fecha_ingreso).toLocaleTimeString('es-CO', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* MAIN CONTENT - Detalle del ticket */}
        <main className="ticket-main">
          {!resumen ? (
            <div className="empty-state-main">
              <p>Selecciona un ticket para ver los detalles</p>
            </div>
          ) : (
            <>
              {/* Header del ticket */}
              <div className="ticket-detail-header">
                <div className="ticket-detail-info">
                  <h3>{resumen.ticket.ticket_codigo}</h3>
                  <div className="ticket-meta">
                    <span className="meta-item">
                      <strong>Placa:</strong> {resumen.ticket.placa}
                    </span>
                    <span className="meta-item">
                      <strong>Estado:</strong> 
                      <span className={`badge badge-${resumen.ticket.estado.toLowerCase()}`}>
                        {resumen.ticket.estado}
                      </span>
                    </span>
                    <span className="meta-item">
                      <strong>Motivo:</strong> {resumen.ticket.motivo_visita}
                    </span>
                  </div>
                  {resumen.ticket.observaciones_recepcion && (
                    <p className="ticket-obs">
                      <strong>Observaciones:</strong> {resumen.ticket.observaciones_recepcion}
                    </p>
                  )}
                </div>
                {isFinalizado && (
                  <div className="ticket-actions-header">
                    <button className="button-primary" onClick={() => setActiveTab("entrega")}>
                      Entregar Ticket
                    </button>
                  </div>
                )}
              </div>

              {/* Tabs */}
              <div className="tabs">
                <button
                  className={`tab ${activeTab === "procesos" ? "active" : ""}`}
                  onClick={() => setActiveTab("procesos")}
                >
                  Procesos ({resumen.procesos.length})
                </button>
                <button
                  className={`tab ${activeTab === "repuestos" ? "active" : ""}`}
                  onClick={() => setActiveTab("repuestos")}
                >
                  Repuestos ({resumen.repuestos.length})
                </button>
                <button
                  className={`tab ${activeTab === "fotos" ? "active" : ""}`}
                  onClick={() => setActiveTab("fotos")}
                >
                  Fotos ({resumen.fotos.filter(f => f.tipo !== "PROCESO").length})
                </button>
                <button
                  className={`tab ${activeTab === "finanzas" ? "active" : ""}`}
                  onClick={() => setActiveTab("finanzas")}
                >
                  Finanzas
                </button>
                {isFinalizado && (
                  <button
                    className={`tab ${activeTab === "entrega" ? "active" : ""}`}
                    onClick={() => setActiveTab("entrega")}
                  >
                    Entrega
                  </button>
                )}
              </div>

              {/* Tab Content */}
              <div className="tab-content">
                {/* TAB: PROCESOS */}
                {activeTab === "procesos" && (
                  <div className="tab-panel">
                    {isEditable && (
                      <div className="form-section">
                        <h4 className="section-title">Agregar Proceso</h4>
                        <div className="quick-actions">
                          {procesosRapidos.map((p) => (
                            <button
                              key={p}
                              className="quick-button"
                              onClick={() => setProceso({ ...proceso, nombre: p })}
                            >
                              {p}
                            </button>
                          ))}
                        </div>
                        <div className="form-grid">
                          <label className="full-width">
                            <span className="label-text">Nombre del Proceso *</span>
                            <input
                              type="text"
                              placeholder="Ej: Cambio de aceite"
                              value={proceso.nombre}
                              onChange={(e) => setProceso({ ...proceso, nombre: e.target.value })}
                            />
                          </label>
                          <label className="full-width">
                            <span className="label-text">Foto (opcional)</span>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={onFotoFileChange}
                              className="file-input"
                            />
                            {fotoPreview && (
                              <div className="image-preview">
                                <img src={fotoPreview} alt="Preview" />
                              </div>
                            )}
                          </label>
                          <label className="full-width">
                            <span className="label-text">Descripción</span>
                            <textarea
                              placeholder="Detalles del proceso..."
                              value={proceso.descripcion}
                              onChange={(e) => setProceso({ ...proceso, descripcion: e.target.value })}
                              rows="2"
                            />
                          </label>
                          <label>
                            <span className="label-text">Mecánico</span>
                            <SelectMecanico
                              value={proceso.mecanico}
                              onChange={(v) => setProceso({ ...proceso, mecanico: v })}
                              placeholder="— Sin asignar —"
                            />
                          </label>
                        </div>
                        <button
                          className="button-primary"
                          onClick={onAddProceso}
                          disabled={loading || !proceso.nombre}
                        >
                          {loading ? "Agregando..." : "Agregar Proceso"}
                        </button>
                      </div>
                    )}

                    <div className="items-list">
                      <h4 className="section-title">Procesos Realizados</h4>
                      {resumen.procesos.length === 0 ? (
                        <p className="empty-state">No hay procesos registrados</p>
                      ) : (
                        resumen.procesos.map((p) => (
                          <div key={p.id} className="item-card" style={{ position: "relative" }}>
                            {isEditable && (
                              <button
                                className="foto-delete"
                                onClick={() => onDeleteProceso(p.id)}
                                disabled={loading}
                                title="Eliminar proceso"
                                style={{ position: "absolute", top: 8, right: 8, zIndex: 1 }}
                              >
                                ✕
                              </button>
                            )}
                            {p.foto_url && (
                              <img
                                src={`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}${p.foto_url}`}
                                alt={p.nombre}
                                style={{ width: "100%", maxHeight: 220, objectFit: "cover", borderRadius: "8px 8px 0 0", marginBottom: 8 }}
                              />
                            )}
                            <div className="item-header">
                              <strong>{p.nombre}</strong>
                              <small>{p.mecanico || "Sin mecánico"}</small>
                            </div>
                            {p.descripcion && <p className="item-desc">{p.descripcion}</p>}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* TAB: REPUESTOS */}
                {activeTab === "repuestos" && (
                  <div className="tab-panel">
                    {isEditable && (
                      <div className="form-section">
                        <h4 className="section-title">Agregar Repuesto</h4>
                        <div className="form-grid">
                          <label className="full-width">
                            <span className="label-text">Nombre del Repuesto *</span>
                            <input
                              type="text"
                              placeholder="Ej: Filtro de aceite"
                              value={repuesto.nombre}
                              onChange={(e) => setRepuesto({ ...repuesto, nombre: e.target.value })}
                            />
                          </label>
                          <label>
                            <span className="label-text">Cantidad *</span>
                            <input
                              type="number"
                              min="1"
                              value={repuesto.cantidad}
                              onChange={(e) => setRepuesto({ ...repuesto, cantidad: Number(e.target.value) })}
                            />
                          </label>
                          <label>
                            <span className="label-text">Marca/Referencia</span>
                            <input
                              type="text"
                              placeholder="Ej: Yamalube"
                              value={repuesto.marca_referencia}
                              onChange={(e) => setRepuesto({ ...repuesto, marca_referencia: e.target.value })}
                            />
                          </label>
                          <label className="full-width">
                            <span className="label-text">Foto del repuesto (opcional)</span>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={(e) => {
                                const file = e.target.files[0] || null;
                                setCompraRepuestoFile(file);
                              }}
                              className="file-input"
                            />
                            {compraRepuestoFile && (
                              <small className="file-selected">✓ {compraRepuestoFile.name}</small>
                            )}
                          </label>
                        </div>

                        {/* Toggle ¿Fue comprado? */}
                        <label style={{ display: "flex", alignItems: "center", gap: 10, margin: "12px 0", cursor: "pointer", padding: "10px 14px", background: fueComprado ? "#dbeafe" : "#f8fafc", borderRadius: 8, border: "1px solid #cbd5e1" }}>
                          <input
                            type="checkbox"
                            checked={fueComprado}
                            onChange={(e) => setFueComprado(e.target.checked)}
                            style={{ width: 18, height: 18, cursor: "pointer" }}
                          />
                          <span style={{ fontWeight: 600, fontSize: 14 }}>¿Fue comprado? (registrar egreso)</span>
                        </label>

                        {fueComprado && (
                          <div className="form-grid" style={{ marginTop: 4 }}>
                            <label>
                              <span className="label-text">Valor *</span>
                              <InputDinero
                                value={compraRepuesto.valor}
                                onChange={(v) => setCompraRepuesto({ ...compraRepuesto, valor: v })}
                              />
                            </label>
                            <label>
                              <span className="label-text">Responsable</span>
                              <SelectMecanico
                                value={compraRepuesto.responsable}
                                onChange={(v) => setCompraRepuesto({ ...compraRepuesto, responsable: v })}
                                placeholder="— Sin asignar —"
                              />
                            </label>
                            <label className="full-width">
                              <span className="label-text">Nota</span>
                              <textarea
                                placeholder="Notas adicionales..."
                                value={compraRepuesto.nota}
                                onChange={(e) => setCompraRepuesto({ ...compraRepuesto, nota: e.target.value })}
                                rows="2"
                              />
                            </label>
                          </div>
                        )}
                        <button
                          className="button-primary"
                          onClick={onAddRepuesto}
                          disabled={loading || !repuesto.nombre}
                        >
                          {loading ? "Agregando..." : "Agregar Repuesto"}
                        </button>
                      </div>
                    )}

                    <div className="items-list">
                      <h4 className="section-title">Repuestos Utilizados</h4>
                      {resumen.repuestos.length === 0 ? (
                        <p className="empty-state">No hay repuestos registrados</p>
                      ) : (
                        (() => {
                          const nombresComprados = new Set((resumen.compras || []).map(c => c.descripcion));
                          const comprasPorNombre = Object.fromEntries((resumen.compras || []).map(c => [c.descripcion, c]));
                          return resumen.repuestos.map((r) => {
                            const compra = comprasPorNombre[r.nombre];
                            const fotoSrc = r.foto_url
                              ? `${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}${r.foto_url}`
                              : compra?.soporte_url || null;
                            return (
                              <div key={r.id} className="item-card" style={{ position: "relative" }}>
                                {isEditable && (
                                  <button
                                    onClick={() => onDeleteRepuesto(r.id)}
                                    disabled={loading}
                                    style={{ position: "absolute", top: 8, right: 8, zIndex: 1, background: "#ef4444", color: "#fff", border: "none", borderRadius: "50%", width: 22, height: 22, cursor: "pointer", fontSize: 12, fontWeight: 700, lineHeight: "22px", padding: 0 }}
                                    title="Eliminar repuesto"
                                  >✕</button>
                                )}
                                {fotoSrc && (
                                  <img
                                    src={fotoSrc}
                                    alt={r.nombre}
                                    style={{ width: "100%", maxHeight: 180, objectFit: "cover", borderRadius: "8px 8px 0 0", marginBottom: 8 }}
                                  />
                                )}
                                <div className="item-header">
                                  <strong>{r.nombre}</strong>
                                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                                    {nombresComprados.has(r.nombre) && (
                                      <span className="badge" style={{ background: "#dcfce7", color: "#166534" }}>🛒 Comprado</span>
                                    )}
                                    <span className="badge">x{r.cantidad}</span>
                                  </div>
                                </div>
                                {r.marca_referencia && <p className="item-desc">{r.marca_referencia}</p>}
                                {compra?.valor > 0 && (
                                  <p className="item-desc" style={{ color: "#dc2626", fontWeight: 600 }}>
                                    ${compra.valor.toLocaleString("es-CO")}
                                    {compra.responsable && ` · ${compra.responsable}`}
                                    {compra.nota && ` · ${compra.nota}`}
                                  </p>
                                )}
                              </div>
                            );
                          });
                        })()
                      )}
                    </div>
                  </div>
                )}

                {/* TAB: FOTOS */}
                {activeTab === "fotos" && (
                  <div className="tab-panel">
                    {isEditable && (
                      <div className="form-section">
                        <h4 className="section-title">Agregar Foto</h4>
                        <div className="form-grid">
                          <label>
                            <span className="label-text">Tipo de Foto</span>
                            <select
                              value={foto.tipo}
                              onChange={(e) => setFoto({ ...foto, tipo: e.target.value })}
                            >
                              <option value="ANTES">Antes</option>
                              <option value="DESPUES">Después</option>
                              <option value="OTRA">Otra</option>
                            </select>
                          </label>
                          <label className="full-width">
                            <span className="label-text">Subir Foto desde el Equipo</span>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={onFotoFileChange}
                              className="file-input"
                            />
                            {fotoPreview && (
                              <div className="image-preview">
                                <img src={fotoPreview} alt="Preview" />
                              </div>
                            )}
                          </label>
                          <label className="full-width">
                            <span className="label-text">O pegar URL de la Foto</span>
                            <input
                              type="text"
                              placeholder="https://..."
                              value={foto.archivo_url}
                              onChange={(e) => setFoto({ ...foto, archivo_url: e.target.value })}
                              disabled={!!fotoFile}
                            />
                          </label>
                          <label className="full-width">
                            <span className="label-text">Descripción</span>
                            <input
                              type="text"
                              placeholder="Descripción de la foto"
                              value={foto.descripcion}
                              onChange={(e) => setFoto({ ...foto, descripcion: e.target.value })}
                            />
                          </label>
                        </div>
                        <button
                          className="button-primary"
                          onClick={onAddFoto}
                          disabled={loading || (!foto.archivo_url && !fotoFile)}
                        >
                          {loading ? "Agregando..." : "Agregar Foto"}
                        </button>
                      </div>
                    )}

                    <div className="items-list">
                      <h4 className="section-title">Fotos de Evidencia</h4>
                      {resumen.fotos.filter(f => f.tipo !== "PROCESO").length === 0 ? (
                        <p className="empty-state">No hay fotos registradas</p>
                      ) : (
                        <div className="fotos-grid">
                          {resumen.fotos.filter(f => f.tipo !== "PROCESO").map((f) => (
                            <div key={f.id} className="foto-card">
                              <div className="foto-badge">{f.tipo}</div>
                              {isEditable && (
                                <button
                                  className="foto-delete"
                                  onClick={() => onDeleteFoto(f.id)}
                                  disabled={loading}
                                  title="Eliminar foto"
                                >
                                  ✕
                                </button>
                              )}
                              <img src={f.archivo_url} alt={f.descripcion} className="foto-img" />
                              {f.descripcion && <p className="foto-desc">{f.descripcion}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}



                {/* TAB: FINANZAS */}
                {activeTab === "finanzas" && (
                  <div className="tab-panel">
                    {/* Cálculo de egresos y cobros */}
                    {(() => {
                      const totalEgresos = resumen.compras.reduce((sum, c) => sum + c.valor, 0);
                      const totalCobros = resumen.cobros.reduce((sum, c) => sum + c.valor, 0);
                      const anticipo = resumen.ticket.anticipo_recibido || 0;
                      const totalServicio = resumen.ticket.total_servicio || totalCobros;
                      const saldoPendiente = resumen.ticket.saldo_pendiente || 0;
                      const gananciaEstimada = totalServicio - totalEgresos;
                      
                      return (
                        <>
                          {/* Alerta de egresos */}
                          {totalEgresos > 0 && (
                            <div className="finanzas-alert">
                              <div className="alert-icon">$</div>
                              <div className="alert-content">
                                <strong>Egresos del Ticket: ${totalEgresos.toLocaleString()}</strong>
                                <p>Has gastado ${totalEgresos.toLocaleString()} en compras para este ticket.</p>
                              </div>
                            </div>
                          )}

                          <div className="finanzas-summary">
                            <div className="finanzas-card">
                              <span className="finanzas-label">Anticipo Recibido</span>
                              <span className="finanzas-value">${anticipo.toLocaleString()}</span>
                            </div>
                            <div className="finanzas-card egresos">
                              <span className="finanzas-label">Total Egresos</span>
                              <span className="finanzas-value negative">${totalEgresos.toLocaleString()}</span>
                            </div>
                            <div className="finanzas-card">
                              <span className="finanzas-label">Total del Servicio</span>
                              <span className="finanzas-value highlight">${totalServicio.toLocaleString()}</span>
                            </div>
                            <div className="finanzas-card">
                              <span className="finanzas-label">Saldo Pendiente</span>
                              <span className="finanzas-value">${saldoPendiente.toLocaleString()}</span>
                            </div>
                            {totalServicio > 0 && (
                              <div className="finanzas-card ganancia">
                                <span className="finanzas-label">Ganancia Estimada</span>
                                <span className={`finanzas-value ${gananciaEstimada >= 0 ? 'positive' : 'negative'}`}>
                                  ${gananciaEstimada.toLocaleString()}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Detalle de egresos */}
                          {resumen.compras.length > 0 && (
                            <div className="egresos-detalle">
                              <h4 className="section-title">Detalle de Egresos</h4>
                              <div className="egresos-list">
                                {resumen.compras.map((c) => (
                                  <div
                                    key={c.id}
                                    className={`egreso-item ${isEditable ? "egreso-item-clickable" : ""}`}
                                    onClick={isEditable ? () => onAddCobro(c.descripcion, c.valor) : undefined}
                                    title={isEditable ? "Clic para agregar como cobro" : undefined}
                                  >
                                    <span className="egreso-desc">{c.descripcion}</span>
                                    <span className="egreso-valor">${c.valor.toLocaleString()}</span>
                                  </div>
                                ))}
                                <div className="egreso-item total">
                                  <span className="egreso-desc"><strong>Total Egresos</strong></span>
                                  <span className="egreso-valor"><strong>${totalEgresos.toLocaleString()}</strong></span>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Sección de Cobros */}
                          <div className="form-section">
                            <h4 className="section-title">Cobros y Cierre</h4>

                            {isEditable && (
                              <div className="cobros-form">
                                <div className="form-grid">
                                  <label className="full-width">
                                    <span className="label-text">Concepto *</span>
                                    {cobrosRapidos.length > 0 && (
                                      <div className="quick-actions" style={{ marginBottom: 6 }}>
                                        {cobrosRapidos.map((c) => (
                                          <button
                                            key={c}
                                            className="quick-button"
                                            type="button"
                                            onClick={() => setCobro({ ...cobro, concepto: c })}
                                          >
                                            {c}
                                          </button>
                                        ))}
                                      </div>
                                    )}
                                    <input
                                      type="text"
                                      placeholder="Ej: Mantenimiento, Mano de obra, Diagnóstico"
                                      value={cobro.concepto}
                                      onChange={(e) => setCobro({ ...cobro, concepto: e.target.value })}
                                    />
                                  </label>
                                  <label>
                                    <span className="label-text">Valor *</span>
                                    <InputDinero
                                      value={cobro.valor}
                                      onChange={(v) => setCobro({ ...cobro, valor: v })}
                                    />
                                  </label>
                                </div>
                                <button
                                  className="button-primary"
                                  onClick={() => onAddCobro()}
                                  disabled={loading || !cobro.concepto || !cobro.valor}
                                >
                                  {loading ? "Agregando..." : "Agregar Cobro"}
                                </button>
                              </div>
                            )}

                            {/* Lista de cobros */}
                            <div className="cobros-list">
                              {resumen.cobros.length === 0 ? (
                                <p className="empty-state">No hay cobros definidos</p>
                              ) : (
                                <>
                                  {resumen.cobros.map((c) => (
                                    <div key={c.id} className="cobro-item">
                                      <span className="cobro-concepto">{c.concepto}</span>
                                      <div className="cobro-actions">
                                        <span className="cobro-valor">${c.valor.toLocaleString()}</span>
                                        {isEditable && (
                                          <button
                                            className="delete-button"
                                            onClick={() => onDeleteCobro(c.id)}
                                            disabled={loading}
                                          >
                                            ✕
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                  <div className="cobro-item total">
                                    <span className="cobro-concepto"><strong>Total del Servicio</strong></span>
                                    <span className="cobro-valor"><strong>${totalCobros.toLocaleString()}</strong></span>
                                  </div>
                                  {anticipo > 0 && (
                                    <>
                                      <div className="cobro-item" style={{ color: '#16a34a' }}>
                                        <span className="cobro-concepto">— Anticipo recibido</span>
                                        <span className="cobro-valor">-${anticipo.toLocaleString()}</span>
                                      </div>
                                      <div className="cobro-item total" style={{ borderTop: '2px solid #1d4ed8' }}>
                                        <span className="cobro-concepto"><strong>Saldo a Pagar</strong></span>
                                        <span className="cobro-valor" style={{ color: '#1d4ed8' }}>
                                          <strong>${Math.max(0, totalCobros - anticipo).toLocaleString()}</strong>
                                        </span>
                                      </div>
                                    </>
                                  )}
                                </>
                              )}
                            </div>

                            {/* Método de pago y guardar — solo si hay cobros */}
                            {isEditable && resumen.cobros.length > 0 && (
                              <div className="form-grid" style={{ marginTop: 16 }}>
                                <label>
                                  <span className="label-text">Método de Pago Final</span>
                                  <select
                                    value={finanzas.metodo_pago_final}
                                    onChange={(e) => setFinanzas({ ...finanzas, metodo_pago_final: e.target.value })}
                                  >
                                    <option value="EFECTIVO">Efectivo</option>
                                    <option value="NEQUI">Nequi</option>
                                    <option value="DAVIPLATA">Daviplata</option>
                                    <option value="TRANSFERENCIA">Transferencia</option>
                                    <option value="TARJETA">Tarjeta</option>
                                  </select>
                                </label>
                                <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                                  <button
                                    className="button-primary"
                                    onClick={onUpdateFinanzas}
                                    disabled={loading || !totalCobros}
                                  >
                                    {loading ? "Guardando..." : "Guardar Finanzas"}
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        </>
                      );
                    })()}

                    {isEditable && (
                      <div className="finalizar-section">
                        <button
                          className="button-finalizar"
                          onClick={onFinalizar}
                          disabled={loading || !resumen.ticket.total_servicio}
                        >
                          {loading ? "Finalizando..." : "Finalizar Ticket"}
                        </button>
                        <p className="finalizar-note">
                          Al finalizar el ticket se generará el cobro final y no podrás agregar más procesos.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB: ENTREGA */}
                {activeTab === "entrega" && isFinalizado && (
                  <div className="tab-panel">
                    <div className="info-card">
                      <h4 className="section-title">Descargar Comprobante</h4>
                      <p className="info-text">
                        Genera un PDF completo con toda la información del servicio, incluyendo fotos de evidencia, 
                        procesos realizados, repuestos utilizados y detalle de cobros.
                      </p>
                      <button
                        className="button-download-pdf"
                        onClick={async () => {
                          try {
                            const blob = await api.descargarPdfTicket(selectedId);
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `ticket-${resumen?.ticket?.ticket_codigo || selectedId}.pdf`;
                            a.click();
                            window.URL.revokeObjectURL(url);
                          } catch (err) {
                            setMsg("Error al descargar PDF: " + err.message);
                          }
                        }}
                      >
                        Descargar PDF Completo
                      </button>
                    </div>

                    <div className="form-section">
                      <h4 className="section-title">Entregar Ticket al Cliente</h4>
                      <div className="form-grid">
                        <label className="full-width">
                          <span className="label-text">Confirmado por *</span>
                          <input
                            type="text"
                            placeholder="Nombre de quien recibe"
                            value={entrega.confirmado_entrega_por}
                            onChange={(e) => setEntrega({ ...entrega, confirmado_entrega_por: e.target.value })}
                          />
                        </label>
                        <label className="full-width">
                          <span className="label-text">URL de Firma (opcional)</span>
                          <input
                            type="text"
                            placeholder="https://..."
                            value={entrega.firma_entrega_url}
                            onChange={(e) => setEntrega({ ...entrega, firma_entrega_url: e.target.value })}
                          />
                        </label>
                        <label className="full-width">
                          <span className="label-text">Observaciones Finales</span>
                          <textarea
                            placeholder="Observaciones sobre el trabajo realizado..."
                            value={observaciones.observaciones_finales}
                            onChange={(e) => setObservaciones({ ...observaciones, observaciones_finales: e.target.value })}
                            rows="3"
                          />
                        </label>
                        <label className="full-width">
                          <span className="label-text">Recomendaciones</span>
                          <textarea
                            placeholder="Recomendaciones para el cliente..."
                            value={observaciones.recomendaciones}
                            onChange={(e) => setObservaciones({ ...observaciones, recomendaciones: e.target.value })}
                            rows="3"
                          />
                        </label>
                        <label className="full-width">
                          <span className="label-text">Próximo Mantenimiento</span>
                          <input
                            type="text"
                            placeholder="Ej: 2026-06 o en 5000 km"
                            value={observaciones.proximo_mantenimiento}
                            onChange={(e) => setObservaciones({ ...observaciones, proximo_mantenimiento: e.target.value })}
                          />
                        </label>
                      </div>
                      <button
                        className="button-primary"
                        onClick={onEntregar}
                        disabled={loading || !entrega.confirmado_entrega_por}
                      >
                        {loading ? "Entregando..." : "Marcar como Entregado"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>

      {msg && <div className={`message-toast ${msg.includes("✓") ? "success" : "error"}`}>{msg}</div>}
    </section>
  );
}
