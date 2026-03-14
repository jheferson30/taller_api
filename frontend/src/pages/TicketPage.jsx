import { useEffect, useState } from "react";
import { api } from "../api";

const PROCESOS_RAPIDOS = [
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

  // Forms
  const [proceso, setProceso] = useState({ nombre: "", descripcion: "", mecanico: "" });
  const [repuesto, setRepuesto] = useState({ nombre: "", cantidad: 1, marca_referencia: "" });
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
      await api.agregarProceso(selectedId, proceso);
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
      await api.agregarRepuesto(selectedId, repuesto);
      setRepuesto({ nombre: "", cantidad: 1, marca_referencia: "" });
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

  async function onAddCobro() {
    if (!cobro.concepto || !cobro.valor) return;
    setLoading(true);
    try {
      await api.agregarCobro(selectedId, { ...cobro, valor: Number(cobro.valor) });
      setCobro({ concepto: "", valor: 0 });
      await loadResumen(selectedId);
      
      // Actualizar el total automáticamente
      const totalCobros = [...resumen.cobros, { valor: Number(cobro.valor) }].reduce((sum, c) => sum + c.valor, 0);
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
      await api.entregarTicket(selectedId, entrega);
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
                    📅 {new Date(t.fecha_ingreso).toLocaleDateString('es-CO', { 
                      day: '2-digit', 
                      month: '2-digit', 
                      year: 'numeric' 
                    })}
                    {' '}
                    🕐 {new Date(t.fecha_ingreso).toLocaleTimeString('es-CO', { 
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
                  Fotos ({resumen.fotos.length})
                </button>
                <button
                  className={`tab ${activeTab === "compras" ? "active" : ""}`}
                  onClick={() => setActiveTab("compras")}
                >
                  Compras ({resumen.compras.length})
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
                          {PROCESOS_RAPIDOS.map((p) => (
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
                            <input
                              type="text"
                              placeholder="Nombre del mecánico"
                              value={proceso.mecanico}
                              onChange={(e) => setProceso({ ...proceso, mecanico: e.target.value })}
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
                          <div key={p.id} className="item-card">
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
                        </div>
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
                        resumen.repuestos.map((r) => (
                          <div key={r.id} className="item-card">
                            <div className="item-header">
                              <strong>{r.nombre}</strong>
                              <span className="badge">x{r.cantidad}</span>
                            </div>
                            {r.marca_referencia && <p className="item-desc">{r.marca_referencia}</p>}
                          </div>
                        ))
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
                      {resumen.fotos.length === 0 ? (
                        <p className="empty-state">No hay fotos registradas</p>
                      ) : (
                        <div className="fotos-grid">
                          {resumen.fotos.map((f) => (
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

                {/* TAB: COMPRAS */}
                {activeTab === "compras" && (
                  <div className="tab-panel">
                    {isEditable && (
                      <div className="form-section">
                        <h4 className="section-title">Registrar Compra</h4>
                        <div className="form-grid">
                          <label className="full-width">
                            <span className="label-text">Descripción *</span>
                            <input
                              type="text"
                              placeholder="Ej: Pastillas de freno"
                              value={compra.descripcion}
                              onChange={(e) => setCompra({ ...compra, descripcion: e.target.value })}
                            />
                          </label>
                          <label>
                            <span className="label-text">Valor *</span>
                            <input
                              type="number"
                              min="0"
                              placeholder="0"
                              value={compra.valor}
                              onChange={(e) => setCompra({ ...compra, valor: e.target.value })}
                            />
                          </label>
                          <label>
                            <span className="label-text">Responsable</span>
                            <input
                              type="text"
                              placeholder="Nombre"
                              value={compra.responsable}
                              onChange={(e) => setCompra({ ...compra, responsable: e.target.value })}
                            />
                          </label>
                          <label className="full-width">
                            <span className="label-text">Subir Soporte (Factura/Recibo)</span>
                            <input
                              type="file"
                              accept="image/*,.pdf"
                              onChange={onCompraFileChange}
                              className="file-input"
                            />
                            {compraFile && (
                              <small className="file-selected">✓ Archivo seleccionado: {compraFile.name}</small>
                            )}
                          </label>
                          <label className="full-width">
                            <span className="label-text">O pegar URL del Soporte</span>
                            <input
                              type="text"
                              placeholder="https://..."
                              value={compra.soporte_url}
                              onChange={(e) => setCompra({ ...compra, soporte_url: e.target.value })}
                              disabled={!!compraFile}
                            />
                          </label>
                          <label className="full-width">
                            <span className="label-text">Nota</span>
                            <textarea
                              placeholder="Notas adicionales..."
                              value={compra.nota}
                              onChange={(e) => setCompra({ ...compra, nota: e.target.value })}
                              rows="2"
                            />
                          </label>
                        </div>
                        <button
                          className="button-primary"
                          onClick={onAddCompra}
                          disabled={loading || !compra.descripcion || !compra.valor}
                        >
                          {loading ? "Registrando..." : "Registrar Compra"}
                        </button>
                      </div>
                    )}

                    <div className="items-list">
                      <h4 className="section-title">Compras Realizadas</h4>
                      {resumen.compras.length === 0 ? (
                        <p className="empty-state">No hay compras registradas</p>
                      ) : (
                        <div className="compras-grid">
                          {resumen.compras.map((c) => (
                            <div key={c.id} className="compra-card">
                              {c.soporte_url && (
                                <div className="compra-soporte">
                                  {c.soporte_url.endsWith('.pdf') ? (
                                    <div className="pdf-preview">
                                      <span className="pdf-icon">📄</span>
                                      <a href={c.soporte_url} target="_blank" rel="noopener noreferrer">
                                        Ver PDF
                                      </a>
                                    </div>
                                  ) : (
                                    <img src={c.soporte_url} alt={c.descripcion} className="compra-img" />
                                  )}
                                </div>
                              )}
                              <div className="compra-info">
                                <div className="compra-header">
                                  <strong className="compra-desc">{c.descripcion}</strong>
                                  <span className="compra-valor">${c.valor.toLocaleString()}</span>
                                </div>
                                {c.responsable && (
                                  <p className="compra-detail">
                                    <span className="detail-label">Responsable:</span> {c.responsable}
                                  </p>
                                )}
                                {c.nota && (
                                  <p className="compra-detail">
                                    <span className="detail-label">Nota:</span> {c.nota}
                                  </p>
                                )}
                              </div>
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
                              <div className="alert-icon">💰</div>
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
                                  <div key={c.id} className="egreso-item">
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
                            <h4 className="section-title">Items de Cobro</h4>
                            
                            {isEditable && (
                              <div className="cobros-form">
                                <div className="form-grid">
                                  <label className="full-width">
                                    <span className="label-text">Concepto *</span>
                                    <input
                                      type="text"
                                      placeholder="Ej: Mantenimiento, Mano de obra, Diagnóstico"
                                      value={cobro.concepto}
                                      onChange={(e) => setCobro({ ...cobro, concepto: e.target.value })}
                                    />
                                  </label>
                                  <label>
                                    <span className="label-text">Valor *</span>
                                    <input
                                      type="number"
                                      min="0"
                                      placeholder="0"
                                      value={cobro.valor}
                                      onChange={(e) => setCobro({ ...cobro, valor: e.target.value })}
                                    />
                                  </label>
                                </div>
                                <button
                                  className="button-primary"
                                  onClick={onAddCobro}
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
                                    <span className="cobro-concepto"><strong>Total a Cobrar</strong></span>
                                    <span className="cobro-valor"><strong>${totalCobros.toLocaleString()}</strong></span>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </>
                      );
                    })()}
                    

                    {isEditable && (
                      <div className="form-section">
                        <h4 className="section-title">Definir Finanzas</h4>
                        <div className="form-grid">
                          <label>
                            <span className="label-text">Total del Servicio *</span>
                            <input
                              type="number"
                              min="0"
                              placeholder="0"
                              value={finanzas.total_servicio}
                              onChange={(e) => setFinanzas({ ...finanzas, total_servicio: e.target.value })}
                            />
                          </label>
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
                        </div>
                        <button
                          className="button-primary"
                          onClick={onUpdateFinanzas}
                          disabled={loading || !finanzas.total_servicio}
                        >
                          {loading ? "Actualizando..." : "Actualizar Finanzas"}
                        </button>
                      </div>
                    )}

                    <div className="form-section">
                      <h4 className="section-title">Observaciones Finales</h4>
                      <div className="form-grid">
                        <label className="full-width">
                          <span className="label-text">Observaciones Finales</span>
                          <textarea
                            placeholder="Observaciones sobre el trabajo realizado..."
                            value={observaciones.observaciones_finales}
                            onChange={(e) => setObservaciones({ ...observaciones, observaciones_finales: e.target.value })}
                            rows="3"
                            disabled={!isEditable}
                          />
                        </label>
                        <label className="full-width">
                          <span className="label-text">Recomendaciones</span>
                          <textarea
                            placeholder="Recomendaciones para el cliente..."
                            value={observaciones.recomendaciones}
                            onChange={(e) => setObservaciones({ ...observaciones, recomendaciones: e.target.value })}
                            rows="3"
                            disabled={!isEditable}
                          />
                        </label>
                        <label className="full-width">
                          <span className="label-text">Próximo Mantenimiento</span>
                          <input
                            type="text"
                            placeholder="Ej: 2026-06 o en 5000 km"
                            value={observaciones.proximo_mantenimiento}
                            onChange={(e) => setObservaciones({ ...observaciones, proximo_mantenimiento: e.target.value })}
                            disabled={!isEditable}
                          />
                        </label>
                      </div>
                    </div>

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
                        onClick={() => window.open(`http://127.0.0.1:8000/tickets/${selectedId}/pdf?token=${encodeURIComponent(import.meta.env.VITE_ADMIN_PASSWORD || '')}`, '_blank')}
                      >
                        📄 Descargar PDF Completo
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
