import { useState, useEffect } from "react";
import { api } from "../api";
import { QRCodeSVG } from "qrcode.react";
import authService from "../services/authService";
import PageHero from "../components/PageHero";

export default function ConfiguracionPage() {
  return <ConfiguracionInterna />;
}

function ConfiguracionInterna() {
  const currentUser = authService.getUser();
  const isAdmin = currentUser?.roles?.includes("ADMIN");

  // ── Usuarios (solo ADMIN) ──
  const [usuarios, setUsuarios] = useState([]);
  const [nuevoUsuario, setNuevoUsuario] = useState({ username: "", email: "", password: "", roles: ["MECANICO"], nombre_completo: "", telefono: "", direccion: "" });
  const [loadingUsuarios, setLoadingUsuarios] = useState(false);
  const [msgUsuarios, setMsgUsuarios] = useState("");
  const [mostrarFormUsuario, setMostrarFormUsuario] = useState(false);

  // ── Mecánicos ──
  // (eliminado: los mecánicos son los usuarios con rol MECANICO)

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
  const [qrData, setQrData] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [mostrarQr, setMostrarQr] = useState(false);

  // ── Email SMTP ──
  const [emailConfig, setEmailConfig] = useState({ smtp_user: "", smtp_password: "", smtp_from: "" });
  const [emailPasswordSet, setEmailPasswordSet] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);
  const [msgEmail, setMsgEmail] = useState("");

  // ── Contraseña Admin ──
  const [adminPwd, setAdminPwd] = useState({ actual: "", nueva: "", confirmar: "" });
  const [savingAdminPwd, setSavingAdminPwd] = useState(false);
  const [msgAdminPwd, setMsgAdminPwd] = useState("");

  useEffect(() => {
    api.obtenerConfigTaller().then(setTaller);
    api.obtenerProcesosRapidos().then((r) => setProcesos(r.procesos));
    api.obtenerCobrosRapidos().then((r) => setCobros(r.cobros));
    api.infoSistema().then(setInfoSistema).catch(() => {});
    api.infoConexionQr().then((r) => setQrData(r.qr_data)).catch(() => {});
    if (isAdmin) {
      cargarUsuarios();
      api.obtenerConfigEmail().then((r) => {
        setEmailConfig({ smtp_user: r.smtp_user || "", smtp_from: r.smtp_from || "", smtp_password: "" });
        setEmailPasswordSet(r.smtp_password_set || false);
      }).catch(() => {});
    }
  }, []);

  const copiarIP = () => {
    if (!infoSistema) return;
    navigator.clipboard.writeText(infoSistema.ip_servidor).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    });
  };

  async function cargarUsuarios() {
    try {
      const data = await api.listarUsuarios();
      setUsuarios(data.users || []);
    } catch (err) {
      console.error("Error cargando usuarios:", err);
    }
  }

  async function handleCrearUsuario(e) {
    e.preventDefault();
    setLoadingUsuarios(true);
    setMsgUsuarios("");
    try {
      await api.crearUsuario(nuevoUsuario);
      setNuevoUsuario({ username: "", email: "", password: "", roles: ["MECANICO"], nombre_completo: "", telefono: "", direccion: "" });
      setMostrarFormUsuario(false);
      setMsgUsuarios("✓ Usuario creado");
      await cargarUsuarios();
      setTimeout(() => setMsgUsuarios(""), 3000);
    } catch (err) {
      setMsgUsuarios("✗ " + err.message);
    } finally {
      setLoadingUsuarios(false);
    }
  }

  async function handleEliminarUsuario(id, username) {
    if (!confirm(`¿Desactivar al usuario "${username}"?`)) return;
    setLoadingUsuarios(true);
    try {
      await api.eliminarUsuario(id);
      setMsgUsuarios("✓ Usuario desactivado");
      await cargarUsuarios();
      setTimeout(() => setMsgUsuarios(""), 3000);
    } catch (err) {
      setMsgUsuarios("✗ " + err.message);
    } finally {
      setLoadingUsuarios(false);
    }
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

  async function handleGuardarEmail(e) {
    e.preventDefault();
    setSavingEmail(true);
    setMsgEmail("");
    try {
      const body = { smtp_user: emailConfig.smtp_user, smtp_from: emailConfig.smtp_from };
      if (emailConfig.smtp_password) body.smtp_password = emailConfig.smtp_password;
      await api.actualizarConfigEmail(body);
      setEmailConfig((prev) => ({ ...prev, smtp_password: "" }));
      setEmailPasswordSet(true);
      setMsgEmail("✓ Configuración guardada");
      setTimeout(() => setMsgEmail(""), 3000);
    } catch (err) {
      setMsgEmail("✗ " + err.message);
    } finally {
      setSavingEmail(false);
    }
  }

  async function handleCambiarPasswordAdmin(e) {
    e.preventDefault();
    if (adminPwd.nueva !== adminPwd.confirmar) {
      setMsgAdminPwd("✗ Las contraseñas nuevas no coinciden");
      return;
    }
    if (adminPwd.nueva.length < 6) {
      setMsgAdminPwd("✗ La nueva contraseña debe tener al menos 6 caracteres");
      return;
    }
    setSavingAdminPwd(true);
    setMsgAdminPwd("");
    try {
      await api.cambiarPasswordAdmin({ password_actual: adminPwd.actual, nueva_password: adminPwd.nueva });
      setAdminPwd({ actual: "", nueva: "", confirmar: "" });
      setMsgAdminPwd("✓ Contraseña actualizada correctamente");
      setTimeout(() => setMsgAdminPwd(""), 4000);
    } catch (err) {
      setMsgAdminPwd("✗ " + err.message);
    } finally {
      setSavingAdminPwd(false);
    }
  }

  return (
    <>
      <PageHero
        titulo="Configuración del Taller"
        subtitulo="Ajustes generales del sistema"
      />
      <div className="config-page">
      {isAdmin && (
        <section className="config-section config-section-full">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 className="config-section-title" style={{ margin: 0 }}>Usuarios del sistema</h2>
            <button className="btn-primary" onClick={() => setMostrarFormUsuario(!mostrarFormUsuario)}>
              {mostrarFormUsuario ? "Cancelar" : "+ Nuevo Usuario"}
            </button>
          </div>

          {mostrarFormUsuario && (
            <form onSubmit={handleCrearUsuario} className="config-form" style={{ marginBottom: "1rem", background: "#f8fafc", padding: "1rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div className="config-field">
                <label>Usuario *</label>
                <input className="config-input" placeholder="nombre_usuario" value={nuevoUsuario.username}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, username: e.target.value })} required />
              </div>
              <div className="config-field">
                <label>Email *</label>
                <input className="config-input" type="email" placeholder="correo@taller.com" value={nuevoUsuario.email}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, email: e.target.value })} required />
              </div>
              <div className="config-field">
                <label>Contraseña * (mín. 8 caracteres, mayúscula, número)</label>
                <input className="config-input" type="password" placeholder="Contraseña123" value={nuevoUsuario.password}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, password: e.target.value })} required />
              </div>
              <div className="config-field">
                <label>Rol *</label>
                <select className="config-input" value={nuevoUsuario.roles[0]}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, roles: [e.target.value] })}>
                  <option value="MECANICO">Mecánico</option>
                  <option value="RECEPCIONISTA">Recepcionista</option>
                  <option value="ADMIN">Administrador</option>
                </select>
              </div>
              <div className="config-field">
                <label>Nombre completo</label>
                <input className="config-input" placeholder="Ej: Juan Pérez" value={nuevoUsuario.nombre_completo}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, nombre_completo: e.target.value })} />
              </div>
              <div className="config-field">
                <label>Teléfono</label>
                <input className="config-input" placeholder="Ej: 3001234567" value={nuevoUsuario.telefono}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, telefono: e.target.value })} />
              </div>
              <div className="config-field">
                <label>Dirección</label>
                <input className="config-input" placeholder="Ej: Calle 10 #5-20" value={nuevoUsuario.direccion}
                  onChange={(e) => setNuevoUsuario({ ...nuevoUsuario, direccion: e.target.value })} />
              </div>
              <div className="config-save-row">
                <button className="btn-primary" type="submit" disabled={loadingUsuarios}>
                  {loadingUsuarios ? "Creando..." : "Crear Usuario"}
                </button>
              </div>
            </form>
          )}

          {msgUsuarios && <span className={`config-msg ${msgUsuarios.startsWith("✓") ? "ok" : "err"}`}>{msgUsuarios}</span>}

          <div className="config-list">
            {usuarios.length === 0 && <p className="config-empty">Sin usuarios registrados</p>}
            {usuarios.map((u) => (
              <div key={u.id} className="config-list-item">
                <div>
                  <span className="config-item-name">{u.username}</span>
                  <small style={{ color: "#64748b", marginLeft: "0.5rem" }}>{u.email}</small>
                  <span style={{ marginLeft: "0.5rem", fontSize: "0.75rem", background: "#dbeafe", color: "#1e40af", padding: "2px 8px", borderRadius: "12px" }}>
                    {u.roles?.join(", ")}
                  </span>
                </div>
                <div className="config-item-actions">
                  <button className="btn-chip btn-chip-danger"
                    onClick={() => handleEliminarUsuario(u.id, u.username)}
                    disabled={loadingUsuarios || u.username === currentUser?.username}>
                    Desactivar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

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
        <p className="config-section-desc">Escanea el QR desde la app para configurarla automáticamente</p>

        <div className="ip-display" style={{ marginTop: 12 }}>
          <span className="ip-value">{infoSistema?.ip_servidor || "Cargando..."}</span>
          {infoSistema && <span className="ip-port">:{infoSistema.puerto}</span>}
          {infoSistema && (
            <button className="btn-copiar" onClick={copiarIP}>
              {copiado ? "✓ Copiado" : "Copiar IP"}
            </button>
          )}
        </div>

        {qrData && (
          <div style={{ marginTop: 16 }}>
            <button
              className="btn-secondary"
              style={{ marginBottom: 12 }}
              onClick={() => setMostrarQr(!mostrarQr)}
            >
              {mostrarQr ? "Ocultar QR" : "Mostrar QR de conexión"}
            </button>
            {mostrarQr && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 8 }}>
                <div style={{ background: "#fff", padding: 16, borderRadius: 12, display: "inline-block", border: "1px solid #e2e8f0" }}>
                  <QRCodeSVG value={qrData} size={200} />
                </div>
                <p className="ip-hint">
                  En la app: toca <strong>Configuracion → Escanear QR</strong> y apunta la cámara aquí.
                  Se configurará la IP y contraseña automáticamente.
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Configuración Email (solo ADMIN) ── */}
      {isAdmin && (
        <section className="config-section">
          <h2 className="config-section-title">Correo para recuperación de contraseña</h2>
          <p className="config-section-desc">
            Configura el correo Gmail desde el que se enviarán los emails de recuperación de contraseña.
            Necesitas una <strong>contraseña de aplicación</strong> de Google (no tu contraseña normal).
          </p>
          <form onSubmit={handleGuardarEmail} className="config-form" style={{ marginTop: "1rem" }}>
            <div className="config-field">
              <label>Correo Gmail</label>
              <input className="config-input" type="email" placeholder="tucorreo@gmail.com"
                value={emailConfig.smtp_user}
                onChange={(e) => setEmailConfig({ ...emailConfig, smtp_user: e.target.value })} />
            </div>
            <div className="config-field">
              <label>Correo remitente (puede ser el mismo)</label>
              <input className="config-input" type="email" placeholder="tucorreo@gmail.com"
                value={emailConfig.smtp_from}
                onChange={(e) => setEmailConfig({ ...emailConfig, smtp_from: e.target.value })} />
            </div>
            <div className="config-field">
              <label>
                Contraseña de aplicación Google
                {emailPasswordSet && <span style={{ marginLeft: 8, fontSize: "0.8rem", color: "#16a34a" }}>✓ ya configurada</span>}
              </label>
              <input className="config-input" type="password"
                placeholder={emailPasswordSet ? "Dejar vacío para no cambiar" : "xxxx xxxx xxxx xxxx"}
                value={emailConfig.smtp_password}
                onChange={(e) => setEmailConfig({ ...emailConfig, smtp_password: e.target.value })} />
              <small style={{ color: "#64748b" }}>
                Generala en: Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones
              </small>
            </div>
            <div className="config-save-row">
              <button className="btn-primary" type="submit" disabled={savingEmail}>
                {savingEmail ? "Guardando..." : "Guardar"}
              </button>
              {msgEmail && <span className={`config-msg ${msgEmail.startsWith("✓") ? "ok" : "err"}`}>{msgEmail}</span>}
            </div>
          </form>
        </section>
      )}

      {isAdmin && (
        <section className="config-section">
          <h2 className="config-section-title">Contraseña Admin (App Móvil)</h2>
          <p className="config-section-desc">
            Cambia la contraseña que usan los mecánicos para conectar la app móvil al servidor.
          </p>
          <form onSubmit={handleCambiarPasswordAdmin} className="config-form" style={{ marginTop: "1rem" }}>
            <div className="config-field">
              <label>Contraseña actual</label>
              <input className="config-input" type="password" placeholder="Contraseña actual"
                value={adminPwd.actual} onChange={(e) => setAdminPwd({ ...adminPwd, actual: e.target.value })} required />
            </div>
            <div className="config-field">
              <label>Nueva contraseña (mín. 6 caracteres)</label>
              <input className="config-input" type="password" placeholder="Nueva contraseña"
                value={adminPwd.nueva} onChange={(e) => setAdminPwd({ ...adminPwd, nueva: e.target.value })} required />
            </div>
            <div className="config-field">
              <label>Confirmar nueva contraseña</label>
              <input className="config-input" type="password" placeholder="Repite la nueva contraseña"
                value={adminPwd.confirmar} onChange={(e) => setAdminPwd({ ...adminPwd, confirmar: e.target.value })} required />
            </div>
            <div className="config-save-row">
              <button className="btn-primary" type="submit" disabled={savingAdminPwd}>
                {savingAdminPwd ? "Guardando..." : "Cambiar Contraseña"}
              </button>
              {msgAdminPwd && <span className={`config-msg ${msgAdminPwd.startsWith("✓") ? "ok" : "err"}`}>{msgAdminPwd}</span>}
            </div>
          </form>
        </section>
      )}

    </div>
    </>
  );
}
