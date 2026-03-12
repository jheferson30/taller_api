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
  
  // Formulario
  const [form, setForm] = useState({
    placa: "",
    nombre_cliente: "",
    telefono_cliente: "",
    fecha_cita: "",
    motivo: "",
    observaciones: "",
  });

  // Mini calendario
  const [mesActual, setMesActual] = useState(new Date());

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
      if (vehiculo) {
        setForm({
          ...form,
          nombre_cliente: vehiculo.nombre_propietario || "",
          telefono_cliente: vehiculo.telefono_propietario || "",
        });
        setMsg("✓ Vehículo encontrado");
        setTimeout(() => setMsg(""), 2000);
      }
    } catch (e) {
      setMsg("Vehículo no encontrado, ingresa los datos del cliente");
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
          <h2>📅 Agenda de Citas</h2>
          <p className="subtitle">Gestiona las citas programadas del taller</p>
        </div>
        <button
          className="btn-nueva-cita"
          onClick={() => setMostrarForm(!mostrarForm)}
        >
          {mostrarForm ? "✕ Cerrar" : "➕ Nueva Cita"}
        </button>
      </div>

      {/* Formulario de nueva cita */}
      {mostrarForm && (
        <div className="form-cita-card">
          <h3>Agendar Nueva Cita</h3>
          <form onSubmit={onCrearCita}>
            <div className="form-row">
              <div className="form-group-inline">
                <label>
                  <span>Placa</span>
                  <input
                    type="text"
                    value={form.placa}
                    onChange={(e) => setForm({ ...form, placa: e.target.value.toUpperCase() })}
                    placeholder="ABC123"
                  />
                </label>
                <button
                  type="button"
                  className="btn-buscar"
                  onClick={onBuscarPlaca}
                  disabled={!form.placa}
                >
                  🔍 Buscar
                </button>
              </div>
            </div>

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

      {loading && <p className="loading">Cargando citas...</p>}

      {/* Citas de hoy */}
      {citasHoy.length > 0 && (
        <div className="seccion-citas">
          <h3 className="seccion-titulo">🔥 Citas de Hoy</h3>
          <div className="citas-grid">
            {citasHoy.map((c) => (
              <CitaCard
                key={c.id}
                cita={c}
                onGenerarTicket={onGenerarTicket}
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
          <h3 className="seccion-titulo">📆 Próximas Citas</h3>
          <div className="citas-grid">
            {citasProximas.map((c) => (
              <CitaCard
                key={c.id}
                cita={c}
                onGenerarTicket={onGenerarTicket}
                onCancelar={onCancelarCita}
                loading={loading}
              />
            ))}
          </div>
        </div>
      )}

      {citasFiltradas.length === 0 && !loading && (
        <div className="empty-state-citas">
          <p>📭 No hay citas programadas</p>
          <button className="btn-primary" onClick={() => setMostrarForm(true)}>
            Agendar Primera Cita
          </button>
        </div>
      )}

      {msg && <p className={`status ${msg.startsWith("✓") ? "success" : "error"}`}>{msg}</p>}
    </div>
  );
}

// Componente para cada cita
function CitaCard({ cita, onGenerarTicket, onCancelar, loading }) {
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
        <p className="cita-telefono">📞 {cita.telefono_cliente}</p>
        {cita.observaciones && (
          <p className="cita-obs">💬 {cita.observaciones}</p>
        )}
      </div>

      {cita.estado !== "CONVERTIDA" && cita.estado !== "CANCELADA" && (
        <div className="cita-actions">
          <button
            className="btn-generar-ticket"
            onClick={() => onGenerarTicket(cita.id)}
            disabled={loading}
          >
            🎫 Generar Ticket
          </button>
          <button
            className="btn-cancelar-cita"
            onClick={() => onCancelar(cita.id)}
            disabled={loading}
          >
            ✕
          </button>
        </div>
      )}

      {cita.estado === "CONVERTIDA" && (
        <div className="cita-convertida">
          ✓ Convertida en ticket: {cita.ticket_codigo}
        </div>
      )}
    </div>
  );
}
