import { useState, useEffect } from "react";
import { api } from "../api";
import EconomiaAuth from "../components/EconomiaAuth";
export default function ConfiguracionPage() {
  const [autenticado, setAutenticado] = useState(false);
  const [tienePassword, setTienePassword] = useState(null);

  useEffect(() => {
    api.verificarTienePassword().then((r) => setTienePassword(r.tiene_password));
  }, []);

  if (tienePassword === null) return <div className="loading">Cargando...</div>;

  if (!autenticado) {
    return (
      <EconomiaAuth
        onAutenticado={() => setAutenticado(true)}
        modoInicial={tienePassword ? "login" : "crear"}
      />
    );
  }

  return <ConfiguracionInterna />;
}

function ConfiguracionInterna() {
  // ── Mecánicos ──
  const [mecanicos, setMecanicos] = useState([]);
  const [nuevoMecanico, setNuevoMecanico] = useState("");
  const [loadingMec, setLoadingMec] = useState(false);

  // ── Taller ──
  const [taller, setTaller] = useState({ nombre_taller: "", direccion: "", telefono: "", nit: "" });
  const [savingTaller, setSavingTaller] = useState(false);
  const [msgTaller, setMsgTaller] = useState("");

  // ── Procesos rápidos ──
  const [procesos, setProcesos] = useState([]);
  const [nuevoProceso, setNuevoProceso] = useState("");
  const [savingProcesos, setSavingProcesos] = useState(false);
  const [msgProcesos, setMsgProcesos] = useState("");

  // ── Cobros rápidos ──
  const [cobros, setCobros] = useState([]);
  const [nuevoCobro, setNuevoCobro] = useState("");
  const [savingCobros, setSavingCobros] = useState(false);
  const [msgCobros, setMsgCobros] = useState("");

  // ── IP del servidor ──
  const [infoSistema, setInfoSistema] = useState(null);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    cargarMecanicos();
    api.obtenerConfigTaller().then(setTaller);
    api.obtenerProcesosRapidos().then((r) => setProcesos(r.procesos));
    api.obtenerCobrosRapidos().then((r) => setCobros(r.cobros));
    api.infoSistema().then(setInfoSistema).catch(() => {});
  }, []);

  const copiarIP = () => {
    if (!infoSistema) return;
    navigator.clipboard.writeText(infoSistema.ip_servidor).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    });
  };

  async function cargarMecanicos() {
    const data = await api.listarMecanicos();
    setMecanicos(data);
  }

  async function handleAgregarMecanico(e) {
    e.preventDefault();
    if (!nuevoMecanico.trim()) return;
    setLoadingMec(true);
    try {
      await api.crearMecanico({ nombre: nuevoMecanico.trim() });
      setNuevoMecanico("");
      await cargarMecanicos();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoadingMec(false);
    }
  }

  async function handleToggleMecanico(id) {
    await api.toggleMecanico(id);
    await cargarMecanicos();
  }

  async function handleEliminarMecanico(id, nombre) {
    if (!confirm(`¿Eliminar a ${nombre}?`)) return;
    await api.eliminarMecanico(id);
    await cargarMecanicos();
  }

  async function handleGuardarTaller(e) {
    e.preventDefault();
    setSavingTaller(true);
    setMsgTaller("");
    try {
      await api.actualizarConfigTaller(taller);
      setMsgTaller("✓ Guardado");
      setTimeout(() => setMsgTaller(""), 2000);
    } catch (err) {
      setMsgTaller("✗ " + err.message);
    } finally {
      setSavingTaller(false);
    }
  }

  async function handleAgregarProceso(e) {
    e.preventDefault();
    if (!nuevoProceso.trim()) return;
    const nuevos = [...procesos, nuevoProceso.trim()];
    setProcesos(nuevos);
    setNuevoProceso("");
    await guardarProcesos(nuevos);
  }

  async function handleEliminarProceso(idx) {
    const nuevos = procesos.filter((_, i) => i !== idx);
    setProcesos(nuevos);
    await guardarProcesos(nuevos);
  }

  async function guardarProcesos(lista) {
    setSavingProcesos(true);
    setMsgProcesos("");
    try {
      await api.actualizarProcesosRapidos(lista);
      setMsgProcesos("✓ Guardado");
      setTimeout(() => setMsgProcesos(""), 2000);
    } catch (err) {
      setMsgProcesos("✗ " + err.message);
    } finally {
      setSavingProcesos(false);
    }
  }

  async function handleAgregarCobro(e) {
    e.preventDefault();
    if (!nuevoCobro.trim()) return;
    const nuevos = [...cobros, nuevoCobro.trim()];
    setCobros(nuevos);
    setNuevoCobro("");
    await guardarCobros(nuevos);
  }

  async function handleEliminarCobro(idx) {
    const nuevos = cobros.filter((_, i) => i !== idx);
    setCobros(nuevos);
    await guardarCobros(nuevos);
  }

  async function guardarCobros(lista) {
    setSavingCobros(true);
    setMsgCobros("");
    try {
      await api.actualizarCobrosRapidos(lista);
      setMsgCobros("✓ Guardado");
      setTimeout(() => setMsgCobros(""), 2000);
    } catch (err) {
      setMsgCobros("✗ " + err.message);
    } finally {
      setSavingCobros(false);
    }
  }

  return (
    <div className="config-page">

      {/* ── Mecánicos ── */}
      <section className="config-section config-section-full">
        <h2 className="config-section-title">Mecánicos del taller</h2>
        <form onSubmit={handleAgregarMecanico} className="config-add-row">
          <input
            className="config-input"
            placeholder="Nombre del mecánico"
            value={nuevoMecanico}
            onChange={(e) => setNuevoMecanico(e.target.value)}
          />
          <button className="btn-primary" type="submit" disabled={loadingMec}>
            {loadingMec ? "..." : "Agregar"}
          </button>
        </form>
        <div className="config-list">
          {mecanicos.length === 0 && <p className="config-empty">Sin mecánicos registrados</p>}
          {mecanicos.map((m) => (
            <div key={m.id} className={`config-list-item ${!m.activo ? "inactivo" : ""}`}>
              <span className="config-item-name">{m.nombre}</span>
              <div className="config-item-actions">
                <button
                  className={`btn-chip ${m.activo ? "btn-chip-warning" : "btn-chip-success"}`}
                  onClick={() => handleToggleMecanico(m.id)}
                >
                  {m.activo ? "Desactivar" : "Activar"}
                </button>
                <button
                  className="btn-chip btn-chip-danger"
                  onClick={() => handleEliminarMecanico(m.id, m.nombre)}
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Datos del taller ── */}
      <section className="config-section">
        <h2 className="config-section-title">Datos del taller</h2>
        <p className="config-section-desc">Se usan en los PDFs generados</p>
        <form onSubmit={handleGuardarTaller} className="config-form">
          <div className="config-field">
            <label>Nombre del taller</label>
            <input
              className="config-input"
              value={taller.nombre_taller}
              onChange={(e) => setTaller({ ...taller, nombre_taller: e.target.value })}
              required
            />
          </div>
          <div className="config-field">
            <label>Dirección</label>
            <input
              className="config-input"
              value={taller.direccion}
              onChange={(e) => setTaller({ ...taller, direccion: e.target.value })}
            />
          </div>
          <div className="config-field">
            <label>Teléfono</label>
            <input
              className="config-input"
              value={taller.telefono}
              onChange={(e) => setTaller({ ...taller, telefono: e.target.value })}
            />
          </div>
          <div className="config-field">
            <label>NIT</label>
            <input
              className="config-input"
              value={taller.nit}
              onChange={(e) => setTaller({ ...taller, nit: e.target.value })}
            />
          </div>
          <div className="config-save-row">
            <button className="btn-primary" type="submit" disabled={savingTaller}>
              {savingTaller ? "Guardando..." : "Guardar datos"}
            </button>
            {msgTaller && <span className={`config-msg ${msgTaller.startsWith("✓") ? "ok" : "err"}`}>{msgTaller}</span>}
          </div>
        </form>
      </section>

      {/* ── Procesos rápidos ── */}
      <section className="config-section">
        <h2 className="config-section-title">Procesos frecuentes</h2>
        <p className="config-section-desc">Aparecen como chips en la app móvil y en tickets</p>
        <form onSubmit={handleAgregarProceso} className="config-add-row">
          <input
            className="config-input"
            placeholder="Ej: Cambio de aceite"
            value={nuevoProceso}
            onChange={(e) => setNuevoProceso(e.target.value)}
          />
          <button className="btn-primary" type="submit">Agregar</button>
        </form>
        {msgProcesos && <span className={`config-msg ${msgProcesos.startsWith("✓") ? "ok" : "err"}`}>{msgProcesos}</span>}
        <div className="config-chips-edit">
          {procesos.length === 0 && <p className="config-empty">Sin procesos registrados</p>}
          {procesos.map((p, i) => (
            <div key={i} className="config-chip-item">
              <span>{p}</span>
              <button className="chip-remove" onClick={() => handleEliminarProceso(i)}>✕</button>
            </div>
          ))}
        </div>
      </section>

      {/* ── Cobros rápidos ── */}
      <section className="config-section">
        <h2 className="config-section-title">Cobros frecuentes</h2>
        <p className="config-section-desc">Aparecen como accesos rápidos en la pestaña Finanzas de los tickets</p>
        <form onSubmit={handleAgregarCobro} className="config-add-row">
          <input
            className="config-input"
            placeholder="Ej: Mano de obra, Diagnóstico, Revisión"
            value={nuevoCobro}
            onChange={(e) => setNuevoCobro(e.target.value)}
          />
          <button className="btn-primary" type="submit">Agregar</button>
        </form>
        {msgCobros && <span className={`config-msg ${msgCobros.startsWith("✓") ? "ok" : "err"}`}>{msgCobros}</span>}
        <div className="config-chips-edit">
          {cobros.length === 0 && <p className="config-empty">Sin cobros registrados</p>}
          {cobros.map((c, i) => (
            <div key={i} className="config-chip-item">
              <span>{c}</span>
              <button className="chip-remove" onClick={() => handleEliminarCobro(i)}>✕</button>
            </div>
          ))}
        </div>
      </section>

      {/* ── Conexión App Móvil ── */}
      <section className="config-section">
        <h2 className="config-section-title">Conexión App Móvil</h2>
        <p className="config-section-desc">Usa esta IP en la app móvil para conectarla al sistema</p>
        <div className="ip-display" style={{ marginTop: 12 }}>
          <span className="ip-value">{infoSistema?.ip_servidor || "Cargando..."}</span>
          {infoSistema && <span className="ip-port">:{infoSistema.puerto}</span>}
          {infoSistema && (
            <button className="btn-copiar" onClick={copiarIP}>
              {copiado ? "✓ Copiado" : "Copiar IP"}
            </button>
          )}
        </div>
        <p className="ip-hint" style={{ marginTop: 10 }}>
          En la app móvil: toca Configuracion → ingresa <strong>{infoSistema?.ip_servidor || "..."}</strong>
        </p>
      </section>

    </div>
  );
}
