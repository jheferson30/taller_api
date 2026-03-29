import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function CitasPage() {
  const navigate = useNavigate();
  const [citas, setCitas] = useState([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("TODAS");
  const [vistaActual, setVistaActual] = useState("lista"); // "lista" o "calendario"
  
  // Formulario
  const [form, setForm] = useState({
    placa: "",
    marca: "",
    modelo: "",
    anio: new Date().getFullYear(),
    cilindraje: "",
    color: "",
    nombre_cliente: "",
    telefono_cliente: "",
    fecha_cita: "",
    motivo: "",
    observaciones: "",
  });

  // Mini calendario
  const [mesActual, setMesActual] = useState(new Date());
  const [diaSeleccionado, setDiaSeleccionado] = useState(null);

  // Funciones para el calendario
  function obtenerDiasDelMes(fecha) {
    const year = fecha.getFullYear();
    const month = fecha.getMonth();
    const primerDia = new Date(year, month, 1);
    const ultimoDia = new Date(year, month + 1, 0);
    const diasEnMes = ultimoDia.getDate();
    const primerDiaSemana = primerDia.getDay();
    
    const dias = [];
    
    // Días vacíos al inicio
    for (let i = 0; i < primerDiaSemana; i++) {
      dias.push(null);
    }
    
    // Días del mes
    for (let dia = 1; dia <= diasEnMes; dia++) {
      dias.push(new Date(year, month, dia));
    }
    
    return dias;
  }

  function obtenerCitasDelDia(fecha) {
    if (!fecha) return [];
    return citasFiltradas.filter(cita => {
      const fechaCita = new Date(cita.fecha_cita);
      return fechaCita.toDateString() === fecha.toDateString();
    });
  }

  function cambiarMes(direccion) {
    setMesActual(prev => {
      const nuevaFecha = new Date(prev);
      nuevaFecha.setMonth(prev.getMonth() + direccion);
      return nuevaFecha;
    });
  }

  async function loadCitas() {
    setLoading(true);
    try {
      const data = await api.listarCitasProximas(30);
      setCitas(data);
    } catch (e) {
      setMsg("Error al cargar citas: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCitas();
  }, []);

  async function onBuscarPlaca() {
    if (!form.placa) return;
    try {
      const vehiculo = await api.buscarVehiculo(form.placa);
      if (vehiculo.existe) {
        const v = vehiculo.vehiculo;
        setForm({
          ...form,
          marca: v.marca || "",
          modelo: v.modelo || "",
          anio: v.anio || new Date().getFullYear(),
          cilindraje: v.cilindraje || "",
          color: v.color || "",
          nombre_cliente: v.nombre_propietario || "",
          telefono_cliente: v.telefono_propietario || "",
        });
        setMsg("✓ Vehículo encontrado - Datos cargados");
        setTimeout(() => setMsg(""), 2000);
      } else {
        setMsg("Vehículo no encontrado, ingresa los datos completos");
        setTimeout(() => setMsg(""), 3000);
      }
    } catch (e) {
      setMsg("Vehículo no encontrado, ingresa los datos completos");
      setTimeout(() => setMsg(""), 3000);
    }
  }

  async function onCrearCita(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.crearCita({
        ...form,
        fecha_cita: new Date(form.fecha_cita).toISOString(),
      });
      setForm({
        placa: "",
        marca: "",
        modelo: "",
        anio: new Date().getFullYear(),
        cilindraje: "",
        color: "",
        nombre_cliente: "",
        telefono_cliente: "",
        fecha_cita: "",
        motivo: "",
        observaciones: "",
      });
      setMostrarForm(false);
      await loadCitas();
      setMsg("✓ Cita agendada exitosamente");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onGenerarTicket(citaId) {
    if (!confirm("¿Generar ticket de ingreso desde esta cita?")) return;
    setLoading(true);
    try {
      const result = await api.generarTicketDesdeCita(citaId);
      await loadCitas();
      setMsg(`✓ Ticket ${result.ticket_codigo} generado`);
      setTimeout(() => {
        navigate("/tickets");
      }, 1500);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onConfirmarCita(citaId) {
    if (!confirm("¿Confirmar esta cita?")) return;
    setLoading(true);
    try {
      await api.actualizarCita(citaId, { estado: "CONFIRMADA" });
      await loadCitas();
      setMsg("✓ Cita confirmada");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onCancelarCita(citaId) {
    if (!confirm("¿Cancelar esta cita?")) return;
    setLoading(true);
    try {
      await api.cancelarCita(citaId);
      await loadCitas();
      setMsg("✓ Cita cancelada");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  const citasFiltradas = citas.filter((c) => {
    if (filtroEstado === "TODAS") return c.estado !== "CANCELADA" && c.estado !== "CONVERTIDA";
    return c.estado === filtroEstado;
  });

  const citasHoy = citasFiltradas.filter((c) => {
    const hoy = new Date().toDateString();
    return new Date(c.fecha_cita).toDateString() === hoy;
  });

  const citasProximas = citasFiltradas.filter((c) => {
    const hoy = new Date().toDateString();
    return new Date(c.fecha_cita).toDateString() !== hoy;
  });


  return (
    <div className="citas-page">
      {/* Header */}
      <div className="citas-header">
        <div>
          <h2>Agenda de Citas</h2>
          <p className="subtitle">Gestiona las citas programadas del taller</p>
        </div>
        <button
          className="btn-nueva-cita"
          onClick={() => setMostrarForm(!mostrarForm)}
        >
          {mostrarForm ? "Cerrar" : "+ Nueva Cita"}
        </button>
      </div>

      {/* Formulario de nueva cita */}
      {mostrarForm && (
        <div className="form-cita-card">
          <h3>Agendar Nueva Cita</h3>
          <form onSubmit={onCrearCita}>
            {/* Datos del Vehículo */}
            <div className="form-section-title">Datos del Vehículo</div>
            
            <div className="form-row">
              <div className="form-group-inline">
                <label>
                  <span>Placa *</span>
                  <input
                    type="text"
                    value={form.placa}
                    onChange={(e) => setForm({ ...form, placa: e.target.value.toUpperCase() })}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onBuscarPlaca(); } }}
                    placeholder="ABC123"
                    required
                  />
                </label>
                <button
                  type="button"
                  className="btn-buscar"
                  onClick={onBuscarPlaca}
                  disabled={!form.placa}
                >
                  Buscar
                </button>
              </div>
            </div>

            <div className="form-row">
              <label>
                <span>Marca</span>
                <input
                  type="text"
                  value={form.marca}
                  onChange={(e) => setForm({ ...form, marca: e.target.value })}
                  placeholder="Ej: Yamaha"
                />
              </label>
              <label>
                <span>Modelo</span>
                <input
                  type="text"
                  value={form.modelo}
                  onChange={(e) => setForm({ ...form, modelo: e.target.value })}
                  placeholder="Ej: FZ-16"
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                <span>Año</span>
                <input
                  type="number"
                  value={form.anio}
                  onChange={(e) => setForm({ ...form, anio: Number(e.target.value) })}
                  placeholder="2024"
                />
              </label>
              <label>
                <span>Cilindraje</span>
                <input
                  type="text"
                  value={form.cilindraje}
                  onChange={(e) => setForm({ ...form, cilindraje: e.target.value })}
                  placeholder="Ej: 150cc"
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                <span>Color</span>
                <input
                  type="text"
                  value={form.color}
                  onChange={(e) => setForm({ ...form, color: e.target.value })}
                  placeholder="Ej: Negro"
                />
              </label>
            </div>

            {/* Datos del Cliente */}
            <div className="form-section-title">Datos del Cliente</div>

            <div className="form-row">
              <label>
                <span>Nombre del Cliente *</span>
                <input
                  type="text"
                  value={form.nombre_cliente}
                  onChange={(e) => setForm({ ...form, nombre_cliente: e.target.value })}
                  placeholder="Nombre completo"
                  required
                />
              </label>
              <label>
                <span>Teléfono *</span>
                <input
                  type="tel"
                  value={form.telefono_cliente}
                  onChange={(e) => setForm({ ...form, telefono_cliente: e.target.value })}
                  placeholder="3001234567"
                  required
                />
              </label>
            </div>

            {/* Datos de la Cita */}
            <div className="form-section-title">Datos de la Cita</div>

            <div className="form-row">
              <label>
                <span>Fecha y Hora de la Cita *</span>
                <input
                  type="datetime-local"
                  value={form.fecha_cita}
                  onChange={(e) => setForm({ ...form, fecha_cita: e.target.value })}
                  required
                />
              </label>
              <label>
                <span>Motivo *</span>
                <input
                  type="text"
                  value={form.motivo}
                  onChange={(e) => setForm({ ...form, motivo: e.target.value })}
                  placeholder="Ej: Mantenimiento preventivo"
                  required
                />
              </label>
            </div>

            <label>
              <span>Observaciones</span>
              <textarea
                value={form.observaciones}
                onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
                placeholder="Notas adicionales..."
                rows="2"
              />
            </label>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Agendando..." : "Agendar Cita"}
            </button>
          </form>
        </div>
      )}

      {/* Filtros */}
      <div className="filtros-citas">
        <div className="filtros-grupo">
          <button
            className={`filtro-btn ${filtroEstado === "TODAS" ? "active" : ""}`}
            onClick={() => setFiltroEstado("TODAS")}
          >
            Todas ({citasFiltradas.length})
          </button>
          <button
            className={`filtro-btn ${filtroEstado === "PENDIENTE" ? "active" : ""}`}
            onClick={() => setFiltroEstado("PENDIENTE")}
          >
            Pendientes
          </button>
          <button
            className={`filtro-btn ${filtroEstado === "CONFIRMADA" ? "active" : ""}`}
            onClick={() => setFiltroEstado("CONFIRMADA")}
          >
            Confirmadas
          </button>
        </div>
        
        <div className="vista-toggle">
          <button
            className={`vista-btn ${vistaActual === "lista" ? "active" : ""}`}
            onClick={() => setVistaActual("lista")}
            title="Vista de lista"
          >
            Lista
          </button>
          <button
            className={`vista-btn ${vistaActual === "calendario" ? "active" : ""}`}
            onClick={() => setVistaActual("calendario")}
            title="Vista de calendario"
          >
            Calendario
          </button>
        </div>
      </div>

      {loading && <p className="loading">Cargando citas...</p>}

      {/* Vista de Calendario */}
      {vistaActual === "calendario" && (
        <div className="calendario-container">
          <div className="calendario-header">
            <button className="calendario-nav" onClick={() => cambiarMes(-1)}>
              ← Anterior
            </button>
            <h3 className="calendario-titulo">
              {mesActual.toLocaleDateString("es-CO", { month: "long", year: "numeric" })}
            </h3>
            <button className="calendario-nav" onClick={() => cambiarMes(1)}>
              Siguiente →
            </button>
          </div>

          <div className="calendario-grid">
            <div className="calendario-dia-nombre">Dom</div>
            <div className="calendario-dia-nombre">Lun</div>
            <div className="calendario-dia-nombre">Mar</div>
            <div className="calendario-dia-nombre">Mié</div>
            <div className="calendario-dia-nombre">Jue</div>
            <div className="calendario-dia-nombre">Vie</div>
            <div className="calendario-dia-nombre">Sáb</div>

            {obtenerDiasDelMes(mesActual).map((fecha, index) => {
              if (!fecha) {
                return <div key={`empty-${index}`} className="calendario-dia-vacio" />;
              }

              const citasDelDia = obtenerCitasDelDia(fecha);
              const esHoy = fecha.toDateString() === new Date().toDateString();
              const tieneCitas = citasDelDia.length > 0;
              const esDiaSeleccionado = diaSeleccionado && fecha.toDateString() === diaSeleccionado.toDateString();

              return (
                <div
                  key={index}
                  className={`calendario-dia ${esHoy ? "hoy" : ""} ${tieneCitas ? "con-citas" : ""} ${esDiaSeleccionado ? "dia-seleccionado" : ""}`}
                  onClick={() => tieneCitas && setDiaSeleccionado(esDiaSeleccionado ? null : fecha)}
                  style={tieneCitas ? { cursor: "pointer" } : {}}
                >
                  <div className="calendario-dia-numero">{fecha.getDate()}</div>
                  <button
                    className="calendario-dia-add"
                    title="Agendar cita este día"
                    onClick={(e) => {
                      e.stopPropagation();
                      const pad = (n) => String(n).padStart(2, '0');
                      const fechaStr = `${fecha.getFullYear()}-${pad(fecha.getMonth()+1)}-${pad(fecha.getDate())}T09:00`;
                      setForm(f => ({ ...f, fecha_cita: fechaStr }));
                      setVistaActual("lista");
                      setMostrarForm(true);
                      setTimeout(() => document.querySelector('.form-cita-card')?.scrollIntoView({ behavior: 'smooth' }), 100);
                    }}
                  >+</button>
                  {tieneCitas && (
                    <div className="calendario-citas-badge">
                      {citasDelDia.length} cita{citasDelDia.length > 1 ? "s" : ""}
                    </div>
                  )}
                  {citasDelDia.length > 0 && (
                    <div className="calendario-citas-mini">
                      {citasDelDia.slice(0, 2).map((cita) => (
                        <div key={cita.id} className="calendario-cita-mini">
                          <span className="cita-hora-mini">
                            {new Date(cita.fecha_cita).toLocaleTimeString("es-CO", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          <span className="cita-cliente-mini">{cita.nombre_cliente}</span>
                        </div>
                      ))}
                      {citasDelDia.length > 2 && (
                        <div className="calendario-cita-mas">
                          +{citasDelDia.length - 2} más
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Panel agenda del día seleccionado */}
          {diaSeleccionado && (() => {
            const citasDelDia = obtenerCitasDelDia(diaSeleccionado);
            return (
              <div className="agenda-dia-panel">
                <div className="agenda-dia-header">
                  <h3 className="agenda-dia-titulo">
                    {diaSeleccionado.toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" })}
                    <span className="agenda-dia-count">{citasDelDia.length} cita{citasDelDia.length > 1 ? "s" : ""}</span>
                  </h3>
                  <button className="agenda-dia-cerrar" onClick={() => setDiaSeleccionado(null)}>✕</button>
                </div>
                <div className="agenda-dia-lista">
                  {citasDelDia
                    .sort((a, b) => new Date(a.fecha_cita) - new Date(b.fecha_cita))
                    .map((cita) => (
                      <div key={cita.id} className="agenda-dia-item">
                        <div className="agenda-dia-hora">
                          {new Date(cita.fecha_cita).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                        </div>
                        <div className="agenda-dia-info">
                          <div className="agenda-dia-cliente">
                            <strong>{cita.nombre_cliente}</strong>
                            {cita.placa && <span className="placa-badge">{cita.placa}</span>}
                            <span className={`badge-cita badge-${cita.estado.toLowerCase()}`}>{cita.estado}</span>
                          </div>
                          <div className="agenda-dia-motivo">{cita.motivo}</div>
                          <div className="agenda-dia-tel">{cita.telefono_cliente}</div>
                          {cita.observaciones && <div className="agenda-dia-obs">{cita.observaciones}</div>}
                        </div>
                        {cita.estado !== "CONVERTIDA" && cita.estado !== "CANCELADA" && (
                          <div className="agenda-dia-actions">
                            {cita.estado === "PENDIENTE" && (
                              <button className="btn-confirmar-cita" onClick={() => onConfirmarCita(cita.id)} disabled={loading}>Confirmar</button>
                            )}
                            <button className="btn-generar-ticket" onClick={() => onGenerarTicket(cita.id)} disabled={loading}>Ticket</button>
                            <button className="btn-cancelar-cita" onClick={() => onCancelarCita(cita.id)} disabled={loading}>Cancelar</button>
                          </div>
                        )}
                        {cita.estado === "CONVERTIDA" && (
                          <div className="cita-convertida" style={{ fontSize: "11px" }}>✓ {cita.ticket_codigo}</div>
                        )}
                      </div>
                    ))
                  }
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Vista de Lista */}
      {vistaActual === "lista" && (
        <>
          {/* Citas de hoy */}
          {citasHoy.length > 0 && (
            <div className="seccion-citas">
              <h3 className="seccion-titulo">Citas de Hoy</h3>
              <div className="citas-grid">
                {citasHoy.map((c) => (
                  <CitaCard
                    key={c.id}
                    cita={c}
                    onGenerarTicket={onGenerarTicket}
                    onConfirmar={onConfirmarCita}
                    onCancelar={onCancelarCita}
                    loading={loading}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Próximas citas */}
          {citasProximas.length > 0 && (
            <div className="seccion-citas">
              <h3 className="seccion-titulo">Proximas Citas</h3>
              <div className="citas-grid">
                {citasProximas.map((c) => (
                  <CitaCard
                    key={c.id}
                    cita={c}
                    onGenerarTicket={onGenerarTicket}
                    onConfirmar={onConfirmarCita}
                    onCancelar={onCancelarCita}
                    loading={loading}
                  />
                ))}
              </div>
            </div>
          )}

          {citasFiltradas.length === 0 && !loading && (
            <div className="empty-state-citas">
              <p>No hay citas programadas</p>
              <button className="btn-primary" onClick={() => setMostrarForm(true)}>
                Agendar Primera Cita
              </button>
            </div>
          )}
        </>
      )}

      {msg && <p className={`status ${msg.startsWith("✓") ? "success" : "error"}`}>{msg}</p>}
    </div>
  );
}

// Componente para cada cita
function CitaCard({ cita, onGenerarTicket, onConfirmar, onCancelar, loading }) {
  const fechaCita = new Date(cita.fecha_cita);
  const esHoy = fechaCita.toDateString() === new Date().toDateString();
  const esPasada = fechaCita < new Date();

  return (
    <div className={`cita-card ${esHoy ? "hoy" : ""} ${esPasada ? "pasada" : ""}`}>
      <div className="cita-header">
        <div className="cita-fecha-hora">
          <span className="cita-fecha">
            {fechaCita.toLocaleDateString("es-CO", {
              weekday: "short",
              day: "2-digit",
              month: "short",
            })}
          </span>
          <span className="cita-hora">
            {fechaCita.toLocaleTimeString("es-CO", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <span className={`badge-cita badge-${cita.estado.toLowerCase()}`}>
          {cita.estado}
        </span>
      </div>

      <div className="cita-body">
        <div className="cita-cliente">
          <strong>{cita.nombre_cliente}</strong>
          {cita.placa && <span className="placa-badge">{cita.placa}</span>}
        </div>
        <p className="cita-motivo">{cita.motivo}</p>
        <p className="cita-telefono">{cita.telefono_cliente}</p>
        {cita.observaciones && (
          <p className="cita-obs">{cita.observaciones}</p>
        )}
      </div>

      {cita.estado !== "CONVERTIDA" && cita.estado !== "CANCELADA" && (
        <div className="cita-actions">
          {cita.estado === "PENDIENTE" && (
            <button
              className="btn-confirmar-cita"
              onClick={() => onConfirmar(cita.id)}
              disabled={loading}
              title="Confirmar cita"
            >
              Confirmar
            </button>
          )}
          <button
            className="btn-generar-ticket"
            onClick={() => onGenerarTicket(cita.id)}
            disabled={loading}
          >
            Generar Ticket
          </button>
          <button
            className="btn-cancelar-cita"
            onClick={() => onCancelar(cita.id)}
            disabled={loading}
            title="Cancelar cita"
          >
            Cancelar
          </button>
        </div>
      )}

      {cita.estado === "CONVERTIDA" && (
        <div className="cita-convertida">
          Convertida en ticket: {cita.ticket_codigo}
        </div>
      )}
    </div>
  );
}
