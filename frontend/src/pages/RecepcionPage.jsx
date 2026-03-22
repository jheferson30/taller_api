import { useState } from "react";
import { api } from "../api";
import InputDinero from "../components/InputDinero";
import SelectMecanico from "../components/SelectMecanico";

const emptyVehiculo = {
  placa: "",
  marca: "",
  modelo: "",
  anio: new Date().getFullYear(),
  cilindraje: "",
  color: "",
  nombre_propietario: "",
  telefono_propietario: "",
};

const emptyTicket = {
  motivo_visita: "",
  observaciones_recepcion: "",
  kilometraje: "",
  estado_inicial: "",
  anticipo_recibido: 0,
  metodo_pago_anticipo: "EFECTIVO",
  recepcionado_por: "",
};

export default function RecepcionPage() {
  const [step, setStep] = useState("search"); // search | new-vehicle | existing-vehicle
  const [placaBusqueda, setPlacaBusqueda] = useState("");
  const [vehiculo, setVehiculo] = useState(emptyVehiculo);
  const [ticket, setTicket] = useState(emptyTicket);
  const [ficha, setFicha] = useState(null);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  async function onBuscar(e) {
    e.preventDefault();
    if (!placaBusqueda.trim()) return;
    
    setMsg("");
    setLoading(true);
    try {
      const data = await api.buscarVehiculo(placaBusqueda);
      if (!data.existe) {
        setVehiculo({ ...emptyVehiculo, placa: placaBusqueda.toUpperCase() });
        setTicket(emptyTicket);
        setFicha(null);
        setStep("new-vehicle");
      } else {
        // Vehículo existe - verificar si tiene datos completos o incompletos
        const vehiculoData = data.vehiculo;
        const tieneDataCompleta = vehiculoData.marca && vehiculoData.modelo && vehiculoData.anio;
        
        if (tieneDataCompleta) {
          // Vehículo con datos completos - ir a crear ticket
          setVehiculo(vehiculoData);
          const detalle = await api.fichaVehiculo(vehiculoData.placa);
          setFicha(detalle);
          setTicket(emptyTicket);
          setStep("existing-vehicle");
        } else {
          // Vehículo existe pero sin datos completos - permitir completarlos
          setVehiculo({
            ...emptyVehiculo,
            ...vehiculoData,
            marca: vehiculoData.marca || "",
            modelo: vehiculoData.modelo || "",
            anio: vehiculoData.anio || new Date().getFullYear(),
          });
          setTicket(emptyTicket);
          setFicha(null);
          setStep("incomplete-vehicle");
        }
      }
    } catch (err) {
      setMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onCrearVehiculoYTicket() {
    setMsg("");
    setLoading(true);
    try {
      // Crear vehículo
      await api.crearVehiculo(vehiculo);
      
      // Crear ticket
      await api.crearTicketIngreso(vehiculo.placa, {
        ...ticket,
        kilometraje: ticket.kilometraje ? Number(ticket.kilometraje) : null,
        anticipo_recibido: Number(ticket.anticipo_recibido || 0),
      });
      
      setMsg("✓ Vehículo y ticket creados exitosamente");
      
      // Resetear y volver a búsqueda
      setTimeout(() => {
        resetForm();
      }, 2000);
    } catch (err) {
      setMsg("✗ Error: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onActualizarVehiculoYCrearTicket() {
    setMsg("");
    setLoading(true);
    try {
      // Actualizar vehículo con datos completos
      await api.actualizarVehiculo(vehiculo.placa, {
        marca: vehiculo.marca,
        modelo: vehiculo.modelo,
        anio: vehiculo.anio,
        cilindraje: vehiculo.cilindraje,
        color: vehiculo.color,
        nombre_propietario: vehiculo.nombre_propietario,
        telefono_propietario: vehiculo.telefono_propietario,
      });
      
      // Crear ticket
      await api.crearTicketIngreso(vehiculo.placa, {
        ...ticket,
        kilometraje: ticket.kilometraje ? Number(ticket.kilometraje) : null,
        anticipo_recibido: Number(ticket.anticipo_recibido || 0),
      });
      
      setMsg("✓ Vehículo actualizado y ticket creado exitosamente");
      
      // Resetear y volver a búsqueda
      setTimeout(() => {
        resetForm();
      }, 2000);
    } catch (err) {
      setMsg("✗ Error: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onCrearTicketExistente() {
    setMsg("");
    setLoading(true);
    try {
      await api.crearTicketIngreso(vehiculo.placa, {
        ...ticket,
        kilometraje: ticket.kilometraje ? Number(ticket.kilometraje) : null,
        anticipo_recibido: Number(ticket.anticipo_recibido || 0),
      });
      
      setMsg("✓ Ticket creado exitosamente");
      
      // Resetear y volver a búsqueda
      setTimeout(() => {
        resetForm();
      }, 2000);
    } catch (err) {
      setMsg("✗ Error: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setStep("search");
    setPlacaBusqueda("");
    setVehiculo(emptyVehiculo);
    setTicket(emptyTicket);
    setFicha(null);
    setMsg("");
  }

  // PANTALLA DE BÚSQUEDA
  if (step === "search") {
    return (
      <section className="recepcion-container">
        <div className="recepcion-header">
          <h2>Recepción de Vehículos</h2>
          <p className="subtitle">Ingresa la placa del vehículo para comenzar</p>
        </div>

        <div className="search-card">
          <form onSubmit={onBuscar} className="search-form">
            <div className="search-input-group">
              <input
                type="text"
                placeholder="Ej: ABC123"
                value={placaBusqueda}
                onChange={(e) => setPlacaBusqueda(e.target.value.toUpperCase())}
                className="search-input"
                autoFocus
                disabled={loading}
              />
              <button type="submit" className="search-button" disabled={loading}>
                {loading ? "Buscando..." : "Buscar Vehículo"}
              </button>
            </div>
          </form>
          {msg && <p className="message error">{msg}</p>}
        </div>
      </section>
    );
  }

  // PANTALLA DE VEHÍCULO NUEVO
  if (step === "new-vehicle") {
    return (
      <section className="recepcion-container">
        <div className="recepcion-header">
          <button onClick={resetForm} className="back-button">Volver a búsqueda</button>
          <h2>Nuevo Vehículo - {vehiculo.placa}</h2>
          <p className="subtitle">Completa los datos del vehículo y el motivo de la visita</p>
        </div>

        <div className="form-sections">
          <div className="form-section">
            <h3 className="section-title">Datos del Vehículo</h3>
            <div className="form-grid">
              <label>
                <span className="label-text">Placa *</span>
                <input
                  type="text"
                  value={vehiculo.placa}
                  disabled
                  className="input-disabled"
                />
              </label>
              <label>
                <span className="label-text">Marca *</span>
                <input
                  type="text"
                  placeholder="Ej: Yamaha"
                  value={vehiculo.marca}
                  onChange={(e) => setVehiculo({ ...vehiculo, marca: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Modelo *</span>
                <input
                  type="text"
                  placeholder="Ej: FZ-16"
                  value={vehiculo.modelo}
                  onChange={(e) => setVehiculo({ ...vehiculo, modelo: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Año *</span>
                <input
                  type="number"
                  placeholder="2024"
                  value={vehiculo.anio}
                  onChange={(e) => setVehiculo({ ...vehiculo, anio: Number(e.target.value) })}
                />
              </label>
              <label>
                <span className="label-text">Cilindraje</span>
                <input
                  type="text"
                  placeholder="Ej: 150cc"
                  value={vehiculo.cilindraje}
                  onChange={(e) => setVehiculo({ ...vehiculo, cilindraje: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Color</span>
                <input
                  type="text"
                  placeholder="Ej: Negro"
                  value={vehiculo.color}
                  onChange={(e) => setVehiculo({ ...vehiculo, color: e.target.value })}
                />
              </label>
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Datos del Propietario</h3>
            <div className="form-grid">
              <label>
                <span className="label-text">Nombre del Propietario</span>
                <input
                  type="text"
                  placeholder="Ej: Juan Pérez"
                  value={vehiculo.nombre_propietario}
                  onChange={(e) => setVehiculo({ ...vehiculo, nombre_propietario: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Teléfono</span>
                <input
                  type="tel"
                  placeholder="Ej: 3001234567"
                  value={vehiculo.telefono_propietario}
                  onChange={(e) => setVehiculo({ ...vehiculo, telefono_propietario: e.target.value })}
                />
              </label>
            </div>
          </div>

          <div className="form-section highlight">
            <h3 className="section-title">Motivo de la Visita</h3>
            <div className="form-grid">
              <label className="full-width">
                <span className="label-text">¿Por qué viene el cliente? *</span>
                <input
                  type="text"
                  placeholder="Ej: Cambio de aceite y revisión de frenos"
                  value={ticket.motivo_visita}
                  onChange={(e) => setTicket({ ...ticket, motivo_visita: e.target.value })}
                />
              </label>
              <label className="full-width">
                <span className="label-text">Observaciones del Cliente</span>
                <textarea
                  placeholder="Ej: El cliente menciona ruido en el freno delantero..."
                  value={ticket.observaciones_recepcion}
                  onChange={(e) => setTicket({ ...ticket, observaciones_recepcion: e.target.value })}
                  rows="3"
                />
              </label>
              <label>
                <span className="label-text">Kilometraje Actual</span>
                <input
                  type="number"
                  placeholder="Ej: 15000"
                  value={ticket.kilometraje}
                  onChange={(e) => setTicket({ ...ticket, kilometraje: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Estado Inicial</span>
                <input
                  type="text"
                  placeholder="Ej: Freno blando"
                  value={ticket.estado_inicial}
                  onChange={(e) => setTicket({ ...ticket, estado_inicial: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Anticipo Recibido</span>
                <InputDinero value={ticket.anticipo_recibido} onChange={(v) => setTicket({ ...ticket, anticipo_recibido: v })} />
              </label>
              <label>
                <span className="label-text">Método de Pago</span>
                <select
                  value={ticket.metodo_pago_anticipo}
                  onChange={(e) => setTicket({ ...ticket, metodo_pago_anticipo: e.target.value })}
                >
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="NEQUI">Nequi</option>
                  <option value="DAVIPLATA">Daviplata</option>
                  <option value="TRANSFERENCIA">Transferencia</option>
                  <option value="TARJETA">Tarjeta</option>
                </select>
              </label>
              <label className="full-width">
                <span className="label-text">Recepcionado Por</span>
                <SelectMecanico
                  value={ticket.recepcionado_por}
                  onChange={(v) => setTicket({ ...ticket, recepcionado_por: v })}
                  placeholder="Sin asignar"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button onClick={resetForm} className="button-secondary" disabled={loading}>
            Cancelar
          </button>
          <button 
            onClick={onCrearVehiculoYTicket} 
            className="button-primary"
            disabled={loading || !vehiculo.marca || !vehiculo.modelo || !ticket.motivo_visita}
          >
            {loading ? "Guardando..." : "Crear Vehículo y Ticket"}
          </button>
        </div>

        {msg && <p className={`message ${msg.includes("✓") ? "success" : "error"}`}>{msg}</p>}
      </section>
    );
  }

  // PANTALLA DE VEHÍCULO INCOMPLETO (creado desde cita)
  if (step === "incomplete-vehicle") {
    return (
      <section className="recepcion-container">
        <div className="recepcion-header">
          <button onClick={resetForm} className="back-button">Volver a búsqueda</button>
          <h2>Completar Datos - {vehiculo.placa}</h2>
          <p className="subtitle">Este vehículo fue creado desde una cita. Completa los datos faltantes.</p>
        </div>

        <div className="form-sections">
          <div className="form-section">
            <h3 className="section-title">Datos del Vehículo</h3>
            <div className="form-grid">
              <label>
                <span className="label-text">Placa *</span>
                <input
                  type="text"
                  value={vehiculo.placa}
                  disabled
                  className="input-disabled"
                />
              </label>
              <label>
                <span className="label-text">Marca *</span>
                <input
                  type="text"
                  placeholder="Ej: Yamaha"
                  value={vehiculo.marca}
                  onChange={(e) => setVehiculo({ ...vehiculo, marca: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Modelo *</span>
                <input
                  type="text"
                  placeholder="Ej: FZ-16"
                  value={vehiculo.modelo}
                  onChange={(e) => setVehiculo({ ...vehiculo, modelo: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Año *</span>
                <input
                  type="number"
                  placeholder="2024"
                  value={vehiculo.anio}
                  onChange={(e) => setVehiculo({ ...vehiculo, anio: Number(e.target.value) })}
                />
              </label>
              <label>
                <span className="label-text">Cilindraje</span>
                <input
                  type="text"
                  placeholder="Ej: 150cc"
                  value={vehiculo.cilindraje}
                  onChange={(e) => setVehiculo({ ...vehiculo, cilindraje: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Color</span>
                <input
                  type="text"
                  placeholder="Ej: Negro"
                  value={vehiculo.color}
                  onChange={(e) => setVehiculo({ ...vehiculo, color: e.target.value })}
                />
              </label>
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Datos del Propietario</h3>
            <div className="form-grid">
              <label>
                <span className="label-text">Nombre del Propietario</span>
                <input
                  type="text"
                  placeholder="Ej: Juan Pérez"
                  value={vehiculo.nombre_propietario}
                  onChange={(e) => setVehiculo({ ...vehiculo, nombre_propietario: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Teléfono</span>
                <input
                  type="tel"
                  placeholder="Ej: 3001234567"
                  value={vehiculo.telefono_propietario}
                  onChange={(e) => setVehiculo({ ...vehiculo, telefono_propietario: e.target.value })}
                />
              </label>
            </div>
          </div>

          <div className="form-section highlight">
            <h3 className="section-title">Motivo de la Visita</h3>
            <div className="form-grid">
              <label className="full-width">
                <span className="label-text">¿Por qué viene el cliente? *</span>
                <input
                  type="text"
                  placeholder="Ej: Cambio de aceite y revisión de frenos"
                  value={ticket.motivo_visita}
                  onChange={(e) => setTicket({ ...ticket, motivo_visita: e.target.value })}
                />
              </label>
              <label className="full-width">
                <span className="label-text">Observaciones del Cliente</span>
                <textarea
                  placeholder="Ej: El cliente menciona ruido en el freno delantero..."
                  value={ticket.observaciones_recepcion}
                  onChange={(e) => setTicket({ ...ticket, observaciones_recepcion: e.target.value })}
                  rows="3"
                />
              </label>
              <label>
                <span className="label-text">Kilometraje Actual</span>
                <input
                  type="number"
                  placeholder="Ej: 15000"
                  value={ticket.kilometraje}
                  onChange={(e) => setTicket({ ...ticket, kilometraje: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Estado Inicial</span>
                <input
                  type="text"
                  placeholder="Ej: Freno blando"
                  value={ticket.estado_inicial}
                  onChange={(e) => setTicket({ ...ticket, estado_inicial: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Anticipo Recibido</span>
                <InputDinero value={ticket.anticipo_recibido} onChange={(v) => setTicket({ ...ticket, anticipo_recibido: v })} />
              </label>
              <label>
                <span className="label-text">Método de Pago</span>
                <select
                  value={ticket.metodo_pago_anticipo}
                  onChange={(e) => setTicket({ ...ticket, metodo_pago_anticipo: e.target.value })}
                >
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="NEQUI">Nequi</option>
                  <option value="DAVIPLATA">Daviplata</option>
                  <option value="TRANSFERENCIA">Transferencia</option>
                  <option value="TARJETA">Tarjeta</option>
                </select>
              </label>
              <label className="full-width">
                <span className="label-text">Recepcionado Por</span>
                <SelectMecanico
                  value={ticket.recepcionado_por}
                  onChange={(v) => setTicket({ ...ticket, recepcionado_por: v })}
                  placeholder="Sin asignar"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button onClick={resetForm} className="button-secondary" disabled={loading}>
            Cancelar
          </button>
          <button 
            onClick={onActualizarVehiculoYCrearTicket} 
            className="button-primary"
            disabled={loading || !vehiculo.marca || !vehiculo.modelo || !ticket.motivo_visita}
          >
            {loading ? "Guardando..." : "Actualizar Vehículo y Crear Ticket"}
          </button>
        </div>

        {msg && <p className={`message ${msg.includes("✓") ? "success" : "error"}`}>{msg}</p>}
      </section>
    );
  }

  // PANTALLA DE VEHÍCULO EXISTENTE
  if (step === "existing-vehicle") {
    return (
      <section className="recepcion-container">
        <div className="recepcion-header">
          <button onClick={resetForm} className="back-button">Volver a búsqueda</button>
          <h2>Vehículo Registrado - {vehiculo.placa}</h2>
          <p className="subtitle">Crea un nuevo ticket de ingreso</p>
        </div>

        <div className="form-sections">
          <div className="info-card">
            <h3 className="section-title">Información del Vehículo</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Marca</span>
                <span className="info-value">{vehiculo.marca}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Modelo</span>
                <span className="info-value">{vehiculo.modelo}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Año</span>
                <span className="info-value">{vehiculo.anio}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Color</span>
                <span className="info-value">{vehiculo.color || "N/A"}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Propietario</span>
                <span className="info-value">{vehiculo.nombre_propietario || "N/A"}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Teléfono</span>
                <span className="info-value">{vehiculo.telefono_propietario || "N/A"}</span>
              </div>
            </div>

            {ficha?.historial_visitas && ficha.historial_visitas.length > 0 && (
              <div className="historial-section">
                <h4 className="historial-title">Historial de Visitas ({ficha.historial_visitas.length})</h4>
                <div className="historial-list">
                  {ficha.historial_visitas.slice(0, 3).map((h) => (
                    <div key={h.ticket_codigo} className="historial-item">
                      <div className="historial-header">
                        <strong>{h.ticket_codigo}</strong>
                        <span className={`badge badge-${h.estado.toLowerCase()}`}>{h.estado}</span>
                      </div>
                      <p className="historial-motivo">{h.motivo_visita}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="form-section highlight">
            <h3 className="section-title">Nuevo Ticket de Ingreso</h3>
            <div className="form-grid">
              <label className="full-width">
                <span className="label-text">¿Por qué viene el cliente? *</span>
                <input
                  type="text"
                  placeholder="Ej: Cambio de aceite y revisión de frenos"
                  value={ticket.motivo_visita}
                  onChange={(e) => setTicket({ ...ticket, motivo_visita: e.target.value })}
                  autoFocus
                />
              </label>
              <label className="full-width">
                <span className="label-text">Observaciones del Cliente</span>
                <textarea
                  placeholder="Ej: El cliente menciona ruido en el freno delantero..."
                  value={ticket.observaciones_recepcion}
                  onChange={(e) => setTicket({ ...ticket, observaciones_recepcion: e.target.value })}
                  rows="3"
                />
              </label>
              <label>
                <span className="label-text">Kilometraje Actual</span>
                <input
                  type="number"
                  placeholder="Ej: 15000"
                  value={ticket.kilometraje}
                  onChange={(e) => setTicket({ ...ticket, kilometraje: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Estado Inicial</span>
                <input
                  type="text"
                  placeholder="Ej: Freno blando"
                  value={ticket.estado_inicial}
                  onChange={(e) => setTicket({ ...ticket, estado_inicial: e.target.value })}
                />
              </label>
              <label>
                <span className="label-text">Anticipo Recibido</span>
                <InputDinero value={ticket.anticipo_recibido} onChange={(v) => setTicket({ ...ticket, anticipo_recibido: v })} />
              </label>
              <label>
                <span className="label-text">Método de Pago</span>
                <select
                  value={ticket.metodo_pago_anticipo}
                  onChange={(e) => setTicket({ ...ticket, metodo_pago_anticipo: e.target.value })}
                >
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="NEQUI">Nequi</option>
                  <option value="DAVIPLATA">Daviplata</option>
                  <option value="TRANSFERENCIA">Transferencia</option>
                  <option value="TARJETA">Tarjeta</option>
                </select>
              </label>
              <label className="full-width">
                <span className="label-text">Recepcionado Por</span>
                <SelectMecanico
                  value={ticket.recepcionado_por}
                  onChange={(v) => setTicket({ ...ticket, recepcionado_por: v })}
                  placeholder="Sin asignar"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button onClick={resetForm} className="button-secondary" disabled={loading}>
            Cancelar
          </button>
          <button 
            onClick={onCrearTicketExistente} 
            className="button-primary"
            disabled={loading || !ticket.motivo_visita}
          >
            {loading ? "Creando..." : "Crear Ticket de Ingreso"}
          </button>
        </div>

        {msg && <p className={`message ${msg.includes("✓") ? "success" : "error"}`}>{msg}</p>}
      </section>
    );
  }
}
