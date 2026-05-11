import { useState, useEffect } from "react";
import { apiSuperAdmin } from "../api";
import { FiRefreshCw, FiLock, FiUnlock, FiUserPlus, FiActivity, FiServer, FiAlertTriangle, FiShield, FiList, FiEdit2, FiKey, FiEye, FiSend, FiCheckSquare, FiSquare, FiBell, FiCheckCircle, FiUpload } from "react-icons/fi";

// ── Helpers ──────────────────────────────────────────────────────────────────

function Badge({ estado }) {
  const colores = {
    TRIAL: "#f59e0b",
    ACTIVO: "#10b981",
    SUSPENDIDO: "#ef4444",
    CANCELADO: "#6b7280",
  };
  return (
    <span style={{
      background: colores[estado] || "#6b7280",
      color: "#fff",
      borderRadius: 4,
      padding: "2px 8px",
      fontSize: "0.75rem",
      fontWeight: 700,
    }}>
      {estado}
    </span>
  );
}

function Card({ title, value, sub, color = "#f59e0b" }) {
  return (
    <div style={{
      background: "#1e293b",
      borderRadius: 10,
      padding: "1.2rem 1.5rem",
      borderLeft: `4px solid ${color}`,
      minWidth: 160,
    }}>
      <div style={{ color: "#94a3b8", fontSize: "0.8rem", marginBottom: 4 }}>{title}</div>
      <div style={{ color: "#f1f5f9", fontSize: "1.8rem", fontWeight: 700 }}>{value ?? "—"}</div>
      {sub && <div style={{ color: "#64748b", fontSize: "0.75rem", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Panel de métricas globales ────────────────────────────────────────────────

function MetricasGlobales() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiSuperAdmin.metricasGlobales()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "#94a3b8" }}>Cargando métricas...</p>;
  if (!data) return <p style={{ color: "#ef4444" }}>Error cargando métricas</p>;

  return (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "2rem" }}>
      <Card title="Total Talleres" value={data.total_talleres} color="#f59e0b" />
      <Card title="En Trial" value={data.talleres_por_estado?.TRIAL ?? 0} color="#f59e0b" />
      <Card title="Activos" value={data.talleres_por_estado?.ACTIVO ?? 0} color="#10b981" />
      <Card title="Suspendidos" value={data.talleres_por_estado?.SUSPENDIDO ?? 0} color="#ef4444" />
      <Card title="Cancelados" value={data.talleres_por_estado?.CANCELADO ?? 0} color="#6b7280" />
      <Card title="Usuarios Activos" value={data.total_usuarios_activos} color="#3b82f6" />
      <Card title="Total Usuarios" value={data.total_usuarios} color="#8b5cf6" />
    </div>
  );
}

// ── Tabla de talleres ─────────────────────────────────────────────────────────

function TablaTalleres({ talleres, onAccion }) {
  if (!Array.isArray(talleres) || !talleres.length) return <p style={{ color: "#94a3b8" }}>No hay talleres registrados.</p>;

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #334155" }}>
            {["ID", "Nombre", "NIT", "Estado", "Trial restante", "Bloqueado", "Acciones"].map(h => (
              <th key={h} style={{ padding: "0.6rem 0.8rem", textAlign: "left", color: "#94a3b8", fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {talleres.map(t => (
            <tr key={t.id} style={{ borderBottom: "1px solid #1e293b" }}>
              <td style={{ padding: "0.6rem 0.8rem", color: "#64748b" }}>{t.id}</td>
              <td style={{ padding: "0.6rem 0.8rem", color: "#f1f5f9", fontWeight: 600 }}>{t.nombre}</td>
              <td style={{ padding: "0.6rem 0.8rem", color: "#94a3b8" }}>{t.nit || "—"}</td>
              <td style={{ padding: "0.6rem 0.8rem" }}><Badge estado={t.estado} /></td>
              <td style={{ padding: "0.6rem 0.8rem", color: "#94a3b8" }}>
                {t.dias_restantes_trial != null ? `${t.dias_restantes_trial} días` : "—"}
              </td>
              <td style={{ padding: "0.6rem 0.8rem" }}>
                {t.bloqueado_emergencia
                  ? <span style={{ color: "#ef4444", fontWeight: 700 }}>🔴 SÍ</span>
                  : <span style={{ color: "#10b981" }}>✅ No</span>}
              </td>
              <td style={{ padding: "0.6rem 0.8rem" }}>
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                  <button
                    onClick={() => onAccion("metricas", t)}
                    style={btnStyle("#3b82f6")}
                    title="Ver métricas"
                  ><FiActivity size={13} /> Métricas</button>
                  {!t.bloqueado_emergencia ? (
                    <button
                      onClick={() => onAccion("bloquear", t)}
                      style={btnStyle("#ef4444")}
                      title="Bloqueo de emergencia"
                    ><FiLock size={13} /> Bloquear</button>
                  ) : (
                    <button
                      onClick={() => onAccion("desbloquear", t)}
                      style={btnStyle("#10b981")}
                      title="Levantar bloqueo"
                    ><FiUnlock size={13} /> Desbloquear</button>
                  )}
                  <button
                    onClick={() => onAccion("cambiarEstado", t)}
                    style={btnStyle("#f59e0b")}
                    title="Cambiar estado"
                  ><FiRefreshCw size={13} /> Estado</button>
                  <button
                    onClick={() => onAccion("crearAdmin", t)}
                    style={btnStyle("#8b5cf6")}
                    title="Crear admin del taller"
                  ><FiUserPlus size={13} /> Admin</button>
                  <button
                    onClick={() => onAccion("editar", t)}
                    style={btnStyle("#3b82f6")}
                    title="Editar datos del taller"
                  ><FiEdit2 size={13} /> Editar</button>
                  <button
                    onClick={() => onAccion("resetMasivo", t)}
                    style={btnStyle("#f97316")}
                    title="Reset masivo de contraseñas"
                  ><FiKey size={13} /> Reset</button>
                  <button
                    onClick={() => onAccion("importarBD", t)}
                    style={btnStyle("#10b981")}
                    title="Importar base de datos"
                  ><FiUpload size={13} /> Importar BD</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function btnStyle(color) {
  return {
    background: "transparent",
    border: `1px solid ${color}`,
    color: color,
    borderRadius: 5,
    padding: "3px 8px",
    cursor: "pointer",
    fontSize: "0.75rem",
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
  };
}

// ── Modal genérico ────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }) {
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "#0f172a", border: "1px solid #334155", borderRadius: 12,
        padding: "2rem", minWidth: 360, maxWidth: 500, width: "90%",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
          <h3 style={{ color: "#f1f5f9", margin: 0 }}>{title}</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ── Modal: Métricas del taller ────────────────────────────────────────────────

function ModalMetricas({ taller, onClose }) {
  const [data, setData] = useState(null);
  const [recursos, setRecursos] = useState(null);

  useEffect(() => {
    apiSuperAdmin.metricasTaller(taller.id).then(setData).catch(console.error);
    apiSuperAdmin.recursosTaller(taller.id).then(setRecursos).catch(console.error);
  }, [taller.id]);

  return (
    <Modal title={`Métricas — ${taller.nombre}`} onClose={onClose}>
      {data ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
          <Row label="Usuarios activos" value={data.usuarios_activos} />
          <Row label="Tickets históricos" value={data.tickets_historicos} />
          <Row label="Tickets este mes" value={data.tickets_mes_actual} />
          <Row label="Último acceso" value={data.fecha_ultimo_acceso ? new Date(data.fecha_ultimo_acceso).toLocaleString() : "Sin registros"} />
          {recursos && <>
            <hr style={{ border: "none", borderTop: "1px solid #334155", margin: "0.5rem 0" }} />
            <Row label="Almacenamiento" value={`${recursos.almacenamiento_mb} MB`} />
          </>}
        </div>
      ) : <p style={{ color: "#94a3b8" }}>Cargando...</p>}
    </Modal>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", color: "#f1f5f9" }}>
      <span style={{ color: "#94a3b8" }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}

// ── Modal: Bloqueo de emergencia ──────────────────────────────────────────────

function ModalBloqueo({ taller, onClose, onSuccess }) {
  const [motivo, setMotivo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleBloquear() {
    if (motivo.trim().length < 10) {
      setError("El motivo debe tener al menos 10 caracteres");
      return;
    }
    setLoading(true);
    try {
      await apiSuperAdmin.bloquearEmergencia(taller.id, motivo);
      onSuccess();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title={`🔴 Bloqueo de emergencia — ${taller.nombre}`} onClose={onClose}>
      <p style={{ color: "#fbbf24", fontSize: "0.85rem", marginBottom: "1rem" }}>
        ⚠️ Esto bloqueará inmediatamente el acceso de todos los usuarios del taller e invalidará sus tokens JWT.
      </p>
      <label style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Motivo del bloqueo *</label>
      <textarea
        value={motivo}
        onChange={e => setMotivo(e.target.value)}
        placeholder="Describe el motivo del bloqueo de emergencia..."
        rows={3}
        style={{ width: "100%", marginTop: 6, marginBottom: 12, background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#f1f5f9", padding: "0.6rem", resize: "vertical", boxSizing: "border-box" }}
      />
      {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>}
      <button
        onClick={handleBloquear}
        disabled={loading}
        style={{ width: "100%", background: "#ef4444", color: "#fff", border: "none", borderRadius: 6, padding: "0.7rem", cursor: "pointer", fontWeight: 700 }}
      >
        {loading ? "Bloqueando..." : "Confirmar Bloqueo de Emergencia"}
      </button>
    </Modal>
  );
}

// ── Modal: Cambiar estado ─────────────────────────────────────────────────────

function ModalCambiarEstado({ taller, onClose, onSuccess }) {
  const estados = ["TRIAL", "ACTIVO", "SUSPENDIDO", "CANCELADO"];
  const [nuevoEstado, setNuevoEstado] = useState(taller.estado);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCambiar() {
    if (nuevoEstado === taller.estado) {
      setError("El taller ya está en ese estado");
      return;
    }
    setLoading(true);
    try {
      await apiSuperAdmin.cambiarEstado(taller.id, nuevoEstado);
      onSuccess();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title={`Cambiar estado — ${taller.nombre}`} onClose={onClose}>
      <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "1rem" }}>
        Estado actual: <Badge estado={taller.estado} />
      </p>
      <label style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Nuevo estado</label>
      <select
        value={nuevoEstado}
        onChange={e => setNuevoEstado(e.target.value)}
        style={{ width: "100%", marginTop: 6, marginBottom: 12, background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#f1f5f9", padding: "0.6rem" }}
      >
        {estados.map(e => <option key={e} value={e}>{e}</option>)}
      </select>
      {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>}
      <button
        onClick={handleCambiar}
        disabled={loading}
        style={{ width: "100%", background: "#f59e0b", color: "#000", border: "none", borderRadius: 6, padding: "0.7rem", cursor: "pointer", fontWeight: 700 }}
      >
        {loading ? "Cambiando..." : "Confirmar Cambio de Estado"}
      </button>
    </Modal>
  );
}

// ── Modal: Crear admin del taller ─────────────────────────────────────────────

function ModalCrearAdmin({ taller, onClose, onSuccess }) {
  const [usuarios, setUsuarios] = useState([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [form, setForm] = useState({ username: "", email: "", password: "", nombre_completo: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiSuperAdmin.listarUsuariosTaller(taller.id)
      .then(setUsuarios)
      .catch(console.error);
  }, [taller.id]);

  async function handleCrear() {
    if (!form.username || !form.email || !form.password) {
      setError("Username, email y contraseña son obligatorios");
      return;
    }
    // Validación básica de email
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError("El email no tiene un formato válido");
      return;
    }
    if (form.password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await apiSuperAdmin.crearAdminTaller(taller.id, form);
      console.log("Admin creado:", result);
      onSuccess();
      onClose();
    } catch (e) {
      console.error("Error creando admin:", e);
      // Extraer mensaje legible del error
      const msg = e?.response?.data?.detail || e?.message || "Error al crear administrador";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = {
    width: "100%", marginTop: 4, marginBottom: 10, background: "#1e293b",
    border: "1px solid #334155", borderRadius: 6, color: "#f1f5f9",
    padding: "0.6rem", boxSizing: "border-box",
  };

  return (
    <Modal title={`Usuarios — ${taller.nombre}`} onClose={onClose}>
      {/* Lista de usuarios existentes */}
      {usuarios.length > 0 && !mostrarForm && (
        <div style={{ marginBottom: "1rem" }}>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            Usuarios actuales:
          </p>
          {usuarios.map(u => (
            <div key={u.id} style={{ background: "#1e293b", borderRadius: 6, padding: "0.6rem", marginBottom: "0.4rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ color: "#f1f5f9", fontWeight: 600 }}>{u.username}</div>
                <div style={{ color: "#64748b", fontSize: "0.75rem" }}>{u.email}</div>
              </div>
              <div style={{ color: "#8b5cf6", fontSize: "0.75rem", fontWeight: 700 }}>
                {u.roles.join(", ")}
              </div>
            </div>
          ))}
          <button
            onClick={() => setMostrarForm(true)}
            style={{ width: "100%", background: "transparent", border: "1px solid #8b5cf6", color: "#8b5cf6", borderRadius: 6, padding: "0.6rem", cursor: "pointer", fontWeight: 600, marginTop: "0.5rem" }}
          >
            + Agregar otro usuario
          </button>
        </div>
      )}

      {/* Formulario de crear (solo si no hay usuarios o se hace clic en agregar) */}
      {(usuarios.length === 0 || mostrarForm) && (
        <>
          {mostrarForm && (
            <button
              onClick={() => setMostrarForm(false)}
              style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", marginBottom: "0.5rem", fontSize: "0.85rem" }}
            >
              ← Volver a la lista
            </button>
          )}
          {["username", "email", "password", "nombre_completo"].map(field => (
            <div key={field}>
              <label style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
                {field === "nombre_completo" ? "Nombre completo (opcional)" : field.charAt(0).toUpperCase() + field.slice(1)}
              </label>
              <input
                type={field === "password" ? "password" : field === "email" ? "email" : "text"}
                value={form[field]}
                onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                style={inputStyle}
                autoComplete="off"
              />
            </div>
          ))}
          {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>}
          <button
            onClick={handleCrear}
            disabled={loading}
            style={{ width: "100%", background: "#8b5cf6", color: "#fff", border: "none", borderRadius: 6, padding: "0.7rem", cursor: "pointer", fontWeight: 700 }}
          >
            {loading ? "Creando..." : "Crear Administrador"}
          </button>
        </>
      )}
    </Modal>
  );
}

// ── Modal: Crear taller ───────────────────────────────────────────────────────

function ModalCrearTaller({ onClose, onSuccess }) {
  const [form, setForm] = useState({ nombre: "", nit: "", direccion: "", telefono: "", dias_trial: 30 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCrear() {
    if (!form.nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    try {
      await apiSuperAdmin.crearTaller(form);
      onSuccess();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = {
    width: "100%", marginTop: 4, marginBottom: 10, background: "#1e293b",
    border: "1px solid #334155", borderRadius: 6, color: "#f1f5f9",
    padding: "0.6rem", boxSizing: "border-box",
  };

  return (
    <Modal title="Crear Nuevo Taller" onClose={onClose}>
      {[
        { key: "nombre", label: "Nombre *", type: "text" },
        { key: "nit", label: "NIT", type: "text" },
        { key: "direccion", label: "Dirección", type: "text" },
        { key: "telefono", label: "Teléfono", type: "text" },
        { key: "dias_trial", label: "Días de trial", type: "number" },
      ].map(({ key, label, type }) => (
        <div key={key}>
          <label style={{ color: "#94a3b8", fontSize: "0.8rem" }}>{label}</label>
          <input
            type={type}
            value={form[key]}
            onChange={e => setForm(f => ({ ...f, [key]: type === "number" ? parseInt(e.target.value) || 30 : e.target.value }))}
            style={inputStyle}
          />
        </div>
      ))}
      {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>}
      <button
        onClick={handleCrear}
        disabled={loading}
        style={{ width: "100%", background: "#10b981", color: "#fff", border: "none", borderRadius: 6, padding: "0.7rem", cursor: "pointer", fontWeight: 700 }}
      >
        {loading ? "Creando..." : "Crear Taller"}
      </button>
    </Modal>
  );
}

// ── Modal: Editar taller ──────────────────────────────────────────────────────

function ModalEditarTaller({ taller, onClose, onSuccess }) {
  const [form, setForm] = useState({
    nombre: taller.nombre || "",
    nit: taller.nit || "",
    direccion: taller.direccion || "",
    telefono: taller.telefono || "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGuardar() {
    if (!form.nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    try {
      await apiSuperAdmin.actualizarTaller(taller.id, form);
      onSuccess();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = {
    width: "100%", marginTop: 4, marginBottom: 10, background: "#1e293b",
    border: "1px solid #334155", borderRadius: 6, color: "#f1f5f9",
    padding: "0.6rem", boxSizing: "border-box",
  };

  return (
    <Modal title={`Editar — ${taller.nombre}`} onClose={onClose}>
      {[
        { key: "nombre", label: "Nombre *" },
        { key: "nit", label: "NIT" },
        { key: "direccion", label: "Dirección" },
        { key: "telefono", label: "Teléfono" },
      ].map(({ key, label }) => (
        <div key={key}>
          <label style={{ color: "#94a3b8", fontSize: "0.8rem" }}>{label}</label>
          <input
            type="text"
            value={form[key]}
            onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
            style={inputStyle}
          />
        </div>
      ))}
      {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>}
      <button
        onClick={handleGuardar}
        disabled={loading}
        style={{ width: "100%", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "0.7rem", cursor: "pointer", fontWeight: 700 }}
      >
        {loading ? "Guardando..." : "Guardar Cambios"}
      </button>
    </Modal>
  );
}

// ── Modal: Reset password masivo ──────────────────────────────────────────────

function ModalResetMasivo({ taller, onClose }) {
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");

  async function handleReset() {
    setLoading(true);
    try {
      const r = await apiSuperAdmin.resetPasswordMasivo(taller.id);
      setResultado(r.usuarios_afectados);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title={`Reset Masivo — ${taller.nombre}`} onClose={onClose}>
      {resultado === null ? (
        <>
          <p style={{ color: "#fbbf24", fontSize: "0.85rem", marginBottom: "1rem" }}>
            ⚠️ Esto invalidará los tokens JWT de <strong>todos los usuarios</strong> del taller.
            Deberán iniciar sesión nuevamente.
          </p>
          {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>}
          <button
            onClick={handleReset}
            disabled={loading}
            style={{ width: "100%", background: "#ef4444", color: "#fff", border: "none", borderRadius: 6, padding: "0.7rem", cursor: "pointer", fontWeight: 700 }}
          >
            {loading ? "Procesando..." : "Confirmar Reset Masivo"}
          </button>
        </>
      ) : (
        <div style={{ textAlign: "center", padding: "1rem" }}>
          <div style={{ color: "#10b981", fontSize: "2rem", marginBottom: "0.5rem" }}>✅</div>
          <p style={{ color: "#f1f5f9", fontWeight: 700 }}>{resultado} usuarios afectados</p>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Todos los tokens han sido invalidados.</p>
          <button onClick={onClose} style={{ marginTop: "1rem", background: "#334155", color: "#f1f5f9", border: "none", borderRadius: 6, padding: "0.6rem 1.5rem", cursor: "pointer" }}>
            Cerrar
          </button>
        </div>
      )}
    </Modal>
  );
}

// ── Modal: Notificaciones masivas ─────────────────────────────────────────────

function ModalNotificacionMasiva({ talleres, onClose }) {
  const [form, setForm] = useState({
    titulo: "",
    mensaje: "",
    solo_admins: true,
    talleres_ids: null,
  });
  const [talleresSeleccionados, setTalleresSeleccionados] = useState([]);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);

  async function handleEnviar() {
    if (!form.titulo.trim() || form.titulo.length < 5) {
      alert("El título debe tener al menos 5 caracteres");
      return;
    }
    if (!form.mensaje.trim() || form.mensaje.length < 10) {
      alert("El mensaje debe tener al menos 10 caracteres");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        ...form,
        talleres_ids: talleresSeleccionados.length > 0 ? talleresSeleccionados : null,
      };
      const r = await apiSuperAdmin.enviarNotificacionMasiva(payload);
      setResultado(r);
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleTaller(tallerId) {
    setTalleresSeleccionados(prev =>
      prev.includes(tallerId)
        ? prev.filter(id => id !== tallerId)
        : [...prev, tallerId]
    );
  }

  if (resultado) {
    return (
      <Modal title={<div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><FiCheckCircle /> Notificación enviada</div>} onClose={onClose}>
        <div style={{ textAlign: "center", padding: "1rem" }}>
          <div style={{ color: "#10b981", fontSize: "3rem", marginBottom: "0.5rem", display: "flex", justifyContent: "center" }}>
            <FiBell />
          </div>
          <p style={{ color: "#f1f5f9", fontWeight: 700, marginBottom: "0.5rem" }}>
            {resultado.notificaciones_enviadas} notificaciones enviadas
          </p>
          <div style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "1rem" }}>
            <p>Talleres afectados: {resultado.talleres_afectados}</p>
            <p>Usuarios notificados: {resultado.usuarios_notificados}</p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "#334155",
              color: "#f1f5f9",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem 1.5rem",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Cerrar
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title={<div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><FiBell /> Enviar Notificación Masiva</div>} onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {/* Título */}
        <div>
          <label style={{ display: "block", color: "#94a3b8", fontSize: "0.85rem", marginBottom: "0.3rem" }}>
            Título *
          </label>
          <input
            type="text"
            value={form.titulo}
            onChange={(e) => setForm({ ...form, titulo: e.target.value })}
            placeholder="Ej: Mantenimiento programado"
            maxLength={200}
            style={{
              width: "100%",
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 6,
              padding: "0.6rem",
              color: "#f1f5f9",
              fontSize: "0.9rem",
            }}
          />
          <div style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "0.2rem" }}>
            {form.titulo.length}/200 caracteres
          </div>
        </div>

        {/* Mensaje */}
        <div>
          <label style={{ display: "block", color: "#94a3b8", fontSize: "0.85rem", marginBottom: "0.3rem" }}>
            Mensaje *
          </label>
          <textarea
            value={form.mensaje}
            onChange={(e) => setForm({ ...form, mensaje: e.target.value })}
            placeholder="Ej: El sistema estará en mantenimiento el 15 de mayo de 2:00 AM a 4:00 AM. Disculpe las molestias."
            maxLength={500}
            rows={4}
            style={{
              width: "100%",
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 6,
              padding: "0.6rem",
              color: "#f1f5f9",
              fontSize: "0.9rem",
              resize: "vertical",
            }}
          />
          <div style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "0.2rem" }}>
            {form.mensaje.length}/500 caracteres
          </div>
        </div>

        {/* Solo admins */}
        <div>
          <label 
            style={{ 
              display: "flex", 
              alignItems: "center", 
              gap: "0.5rem", 
              cursor: "pointer" 
            }}
            onClick={() => setForm({ ...form, solo_admins: !form.solo_admins })}
          >
            <div style={{ fontSize: "1.2rem", color: form.solo_admins ? "#10b981" : "#64748b", display: "flex", alignItems: "center" }}>
              {form.solo_admins ? <FiCheckSquare /> : <FiSquare />}
            </div>
            <span style={{ color: "#f1f5f9", fontSize: "0.9rem" }}>
              Solo enviar a administradores
            </span>
          </label>
          <p style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "0.3rem", marginLeft: "1.7rem" }}>
            Si está marcado, solo los usuarios con rol ADMIN recibirán la notificación
          </p>
        </div>

        {/* Selección de talleres */}
        <div>
          <label style={{ display: "block", color: "#94a3b8", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            Talleres destinatarios
          </label>
          <div style={{
            background: "#0f172a",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "0.8rem",
            maxHeight: "200px",
            overflowY: "auto",
          }}>
            <label 
              style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "0.5rem", 
                marginBottom: "0.5rem", 
                cursor: "pointer" 
              }}
              onClick={() => setTalleresSeleccionados([])}
            >
              <div style={{ fontSize: "1.2rem", color: talleresSeleccionados.length === 0 ? "#10b981" : "#64748b", display: "flex", alignItems: "center" }}>
                {talleresSeleccionados.length === 0 ? <FiCheckSquare /> : <FiSquare />}
              </div>
              <span style={{ color: "#f1f5f9", fontWeight: 600 }}>
                Todos los talleres activos
              </span>
            </label>
            <div style={{ borderTop: "1px solid #334155", paddingTop: "0.5rem", marginTop: "0.5rem" }}>
              {talleres.filter(t => t.estado === "ACTIVO").map(t => (
                <label
                  key={t.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.3rem 0",
                    cursor: "pointer",
                  }}
                  onClick={() => toggleTaller(t.id)}
                >
                  <div style={{ fontSize: "1.2rem", color: talleresSeleccionados.includes(t.id) ? "#10b981" : "#64748b", display: "flex", alignItems: "center" }}>
                    {talleresSeleccionados.includes(t.id) ? <FiCheckSquare /> : <FiSquare />}
                  </div>
                  <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                    {t.nombre} (ID: {t.id})
                  </span>
                </label>
              ))}
            </div>
          </div>
          <p style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "0.3rem" }}>
            {talleresSeleccionados.length === 0
              ? "Se enviará a todos los talleres activos"
              : `Se enviará a ${talleresSeleccionados.length} taller(es) seleccionado(s)`}
          </p>
        </div>

        {/* Botones */}
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              flex: 1,
              background: "#334155",
              color: "#f1f5f9",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem",
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 600,
              opacity: loading ? 0.5 : 1,
            }}
          >
            Cancelar
          </button>
          <button
            onClick={handleEnviar}
            disabled={loading}
            style={{
              flex: 2,
              background: "#10b981",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem",
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 700,
              opacity: loading ? 0.5 : 1,
            }}
          >
            {loading ? "Enviando..." : "📢 Enviar Notificación"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Modal: Importar Base de Datos ─────────────────────────────────────────────

function ModalImportarBD({ taller, onClose, onSuccess }) {
  const [archivo, setArchivo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");

  async function handleImportar() {
    if (!archivo) {
      setError("Debes seleccionar un archivo SQL");
      return;
    }

    setLoading(true);
    setError("");
    
    try {
      const res = await apiSuperAdmin.importarBDTaller(taller.id, archivo);
      setResultado(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleArchivoChange(e) {
    const file = e.target.files[0];
    if (file) {
      // Validar extensión
      if (!file.name.endsWith('.sql') && !file.name.endsWith('.dump')) {
        setError("Solo se permiten archivos .sql o .dump");
        setArchivo(null);
        return;
      }
      setArchivo(file);
      setError("");
    }
  }

  if (resultado) {
    return (
      <Modal title={<div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><FiCheckCircle /> Importación Completada</div>} onClose={onClose}>
        <div style={{ textAlign: "center", padding: "1rem" }}>
          <div style={{ color: "#10b981", fontSize: "3rem", marginBottom: "0.5rem", display: "flex", justifyContent: "center" }}>
            <FiCheckCircle />
          </div>
          <p style={{ color: "#f1f5f9", fontWeight: 700, marginBottom: "0.5rem" }}>
            ¡Datos importados exitosamente!
          </p>
          <div style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "1rem", textAlign: "left" }}>
            <p><strong>Taller:</strong> {resultado.taller_nombre}</p>
            <p><strong>Archivo:</strong> {resultado.archivo}</p>
            <hr style={{ border: "none", borderTop: "1px solid #334155", margin: "0.5rem 0" }} />
            <p><strong>Usuarios importados:</strong> {resultado.estadisticas.usuarios}</p>
            <p><strong>Clientes importados:</strong> {resultado.estadisticas.clientes}</p>
            <p><strong>Vehículos importados:</strong> {resultado.estadisticas.vehiculos}</p>
            <p><strong>Tickets importados:</strong> {resultado.estadisticas.tickets}</p>
          </div>
          <button
            onClick={() => {
              onSuccess();
              onClose();
            }}
            style={{
              background: "#334155",
              color: "#f1f5f9",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem 1.5rem",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Cerrar
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title={<div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><FiUpload /> Importar Base de Datos</div>} onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 6, padding: "1rem" }}>
          <p style={{ color: "#f1f5f9", fontWeight: 600, marginBottom: "0.5rem" }}>
            Taller: {taller.nombre}
          </p>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
            ID: {taller.id}
          </p>
        </div>

        <div>
          <label style={{ display: "block", color: "#94a3b8", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            Archivo SQL *
          </label>
          <input
            type="file"
            accept=".sql,.dump"
            onChange={handleArchivoChange}
            style={{
              width: "100%",
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 6,
              padding: "0.6rem",
              color: "#f1f5f9",
              fontSize: "0.9rem",
              cursor: "pointer",
            }}
          />
          <p style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "0.3rem" }}>
            Formatos soportados: .sql, .dump
          </p>
          {archivo && (
            <p style={{ color: "#10b981", fontSize: "0.85rem", marginTop: "0.5rem" }}>
              ✓ Archivo seleccionado: {archivo.name} ({(archivo.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        <div style={{ background: "#1e293b", border: "1px solid #f59e0b", borderRadius: 6, padding: "1rem" }}>
          <p style={{ color: "#f59e0b", fontWeight: 600, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <FiAlertTriangle /> Importante
          </p>
          <ul style={{ color: "#94a3b8", fontSize: "0.85rem", marginLeft: "1.2rem" }}>
            <li>El archivo debe ser un backup de una BD mono-tenant (sin taller_id)</li>
            <li>Los datos se importarán automáticamente agregando el taller_id</li>
            <li>Este proceso puede tardar varios minutos</li>
            <li>No cerrar esta ventana durante la importación</li>
          </ul>
        </div>

        {error && (
          <div style={{ background: "#7f1d1d", border: "1px solid #ef4444", borderRadius: 6, padding: "0.8rem" }}>
            <p style={{ color: "#fca5a5", fontSize: "0.85rem", margin: 0 }}>
              {error}
            </p>
          </div>
        )}

        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              flex: 1,
              background: "#334155",
              color: "#f1f5f9",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem",
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 600,
              opacity: loading ? 0.5 : 1,
            }}
          >
            Cancelar
          </button>
          <button
            onClick={handleImportar}
            disabled={loading || !archivo}
            style={{
              flex: 2,
              background: archivo && !loading ? "#10b981" : "#334155",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem",
              cursor: loading || !archivo ? "not-allowed" : "pointer",
              fontWeight: 700,
              opacity: loading || !archivo ? 0.5 : 1,
            }}
          >
            {loading ? "Importando..." : "Importar Base de Datos"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Sección: Seguridad (intentos fallidos) ────────────────────────────────────

function SeccionSeguridad({ talleres }) {
  const [tallerSeleccionado, setTallerSeleccionado] = useState(talleres[0]?.id || "");
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [desde, setDesde] = useState("");

  async function cargar() {
    if (!tallerSeleccionado) return;
    setLoading(true);
    try {
      const r = await apiSuperAdmin.intentosFallidos(tallerSeleccionado, { desde: desde || undefined });
      setRegistros(r.registros || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargar(); }, [tallerSeleccionado]);

  return (
    <div>
      <h2 style={{ color: "#f1f5f9", marginBottom: "1rem", display: "flex", alignItems: "center", gap: 8 }}>
        <FiShield color="#ef4444" /> Intentos de Login Fallidos
      </h2>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <select
          value={tallerSeleccionado}
          onChange={e => setTallerSeleccionado(e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#f1f5f9", borderRadius: 6, padding: "0.5rem 1rem" }}
        >
          {talleres.map(t => <option key={t.id} value={t.id}>{t.nombre}</option>)}
        </select>
        <input
          type="date"
          value={desde}
          onChange={e => setDesde(e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#f1f5f9", borderRadius: 6, padding: "0.5rem 1rem" }}
        />
        <button onClick={cargar} style={{ background: "#334155", color: "#f1f5f9", border: "none", borderRadius: 6, padding: "0.5rem 1rem", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
          <FiRefreshCw size={14} /> Buscar
        </button>
      </div>

      {loading ? (
        <p style={{ color: "#94a3b8" }}>Cargando...</p>
      ) : registros.length === 0 ? (
        <div style={{ background: "#0f172a", borderRadius: 8, padding: "2rem", textAlign: "center", color: "#64748b" }}>
          ✅ No se encontraron intentos fallidos
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155" }}>
                {["Timestamp", "IP", "User Agent", "Detalles"].map(h => (
                  <th key={h} style={{ padding: "0.6rem", textAlign: "left", color: "#94a3b8" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {registros.map((r, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "0.6rem", color: "#f1f5f9" }}>{new Date(r.timestamp).toLocaleString()}</td>
                  <td style={{ padding: "0.6rem", color: "#ef4444", fontFamily: "monospace" }}>{r.ip_address}</td>
                  <td style={{ padding: "0.6rem", color: "#64748b", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.user_agent}</td>
                  <td style={{ padding: "0.6rem", color: "#94a3b8", fontSize: "0.75rem" }}>{JSON.stringify(r.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Sección: Auditoría global ─────────────────────────────────────────────────

function SeccionAuditoria({ talleres }) {
  const [filtros, setFiltros] = useState({ taller_id: "", accion: "", desde: "", hasta: "" });
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const ACCIONES = ["LOGIN", "LOGOUT", "LOGIN_FAILED", "USER_CREATE", "TALLER_CREATE",
    "TALLER_UPDATE", "TALLER_ACTIVATE", "TALLER_SUSPEND", "TALLER_CANCEL",
    "TALLER_EMERGENCY_BLOCK", "TALLER_EMERGENCY_UNBLOCK", "PASSWORD_RESET_FORCED", "PASSWORD_RESET_MASS"];

  async function cargar(p = 1) {
    setLoading(true);
    try {
      const params = { page: p, page_size: 50 };
      if (filtros.taller_id) params.taller_id = filtros.taller_id;
      if (filtros.accion) params.accion = filtros.accion;
      if (filtros.desde) params.desde = filtros.desde;
      if (filtros.hasta) params.hasta = filtros.hasta;
      const r = await apiSuperAdmin.auditoriaGlobal(params);
      setRegistros(r.registros || []);
      setPage(p);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  const colorAccion = (accion) => {
    if (accion?.includes("FAILED") || accion?.includes("BLOCK")) return "#ef4444";
    if (accion?.includes("CREATE") || accion?.includes("ACTIVATE")) return "#10b981";
    if (accion?.includes("SUSPEND") || accion?.includes("CANCEL")) return "#f59e0b";
    return "#94a3b8";
  };

  return (
    <div>
      <h2 style={{ color: "#f1f5f9", marginBottom: "1rem", display: "flex", alignItems: "center", gap: 8 }}>
        <FiList color="#3b82f6" /> Auditoría Global
      </h2>

      {/* Filtros */}
      <div style={{ display: "flex", gap: "0.8rem", marginBottom: "1rem", flexWrap: "wrap", background: "#0f172a", padding: "1rem", borderRadius: 8 }}>
        <select
          value={filtros.taller_id}
          onChange={e => setFiltros(f => ({ ...f, taller_id: e.target.value }))}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#f1f5f9", borderRadius: 6, padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}
        >
          <option value="">Todos los talleres</option>
          {talleres.map(t => <option key={t.id} value={t.id}>{t.nombre}</option>)}
        </select>
        <select
          value={filtros.accion}
          onChange={e => setFiltros(f => ({ ...f, accion: e.target.value }))}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#f1f5f9", borderRadius: 6, padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}
        >
          <option value="">Todas las acciones</option>
          {ACCIONES.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <input type="date" value={filtros.desde} onChange={e => setFiltros(f => ({ ...f, desde: e.target.value }))}
          placeholder="Desde"
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#f1f5f9", borderRadius: 6, padding: "0.4rem 0.8rem", fontSize: "0.85rem" }} />
        <input type="date" value={filtros.hasta} onChange={e => setFiltros(f => ({ ...f, hasta: e.target.value }))}
          placeholder="Hasta"
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#f1f5f9", borderRadius: 6, padding: "0.4rem 0.8rem", fontSize: "0.85rem" }} />
        <button onClick={() => cargar(1)} style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "0.4rem 1rem", cursor: "pointer", fontWeight: 600, fontSize: "0.85rem" }}>
          Filtrar
        </button>
        <button onClick={() => { setFiltros({ taller_id: "", accion: "", desde: "", hasta: "" }); cargar(1); }}
          style={{ background: "transparent", border: "1px solid #334155", color: "#94a3b8", borderRadius: 6, padding: "0.4rem 0.8rem", cursor: "pointer", fontSize: "0.85rem" }}>
          Limpiar
        </button>
      </div>

      {loading ? (
        <p style={{ color: "#94a3b8" }}>Cargando...</p>
      ) : registros.length === 0 ? (
        <div style={{ background: "#0f172a", borderRadius: 8, padding: "2rem", textAlign: "center", color: "#64748b" }}>
          No hay registros con los filtros aplicados
        </div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #334155" }}>
                  {["Timestamp", "Taller", "Usuario", "Acción", "Recurso", "IP"].map(h => (
                    <th key={h} style={{ padding: "0.5rem 0.6rem", textAlign: "left", color: "#94a3b8", fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {registros.map(r => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #1e293b" }}>
                    <td style={{ padding: "0.5rem 0.6rem", color: "#64748b", whiteSpace: "nowrap" }}>{new Date(r.timestamp).toLocaleString()}</td>
                    <td style={{ padding: "0.5rem 0.6rem", color: "#94a3b8" }}>{r.taller_id || "—"}</td>
                    <td style={{ padding: "0.5rem 0.6rem", color: "#94a3b8" }}>{r.user_id || "—"}</td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>
                      <span style={{ color: colorAccion(r.action), fontWeight: 600, fontSize: "0.75rem" }}>{r.action}</span>
                    </td>
                    <td style={{ padding: "0.5rem 0.6rem", color: "#64748b" }}>{r.resource_type}{r.resource_id ? ` #${r.resource_id}` : ""}</td>
                    <td style={{ padding: "0.5rem 0.6rem", color: "#64748b", fontFamily: "monospace", fontSize: "0.75rem" }}>{r.ip_address}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", justifyContent: "center" }}>
            <button onClick={() => cargar(page - 1)} disabled={page === 1}
              style={{ background: "#1e293b", color: "#f1f5f9", border: "1px solid #334155", borderRadius: 6, padding: "0.4rem 0.8rem", cursor: page === 1 ? "not-allowed" : "pointer" }}>
              ← Anterior
            </button>
            <span style={{ color: "#94a3b8", padding: "0.4rem 0.8rem" }}>Página {page}</span>
            <button onClick={() => cargar(page + 1)} disabled={registros.length < 50}
              style={{ background: "#1e293b", color: "#f1f5f9", border: "1px solid #334155", borderRadius: 6, padding: "0.4rem 0.8rem", cursor: registros.length < 50 ? "not-allowed" : "pointer" }}>
              Siguiente →
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function SuperAdminPage() {
  const [talleres, setTalleres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // { tipo, taller }
  const [error, setError] = useState("");
  const [tab, setTab] = useState("talleres"); // talleres | seguridad | auditoria

  async function cargarTalleres() {
    setLoading(true);
    setError("");
    try {
      const data = await apiSuperAdmin.listarTalleres();
      console.log("Talleres recibidos:", data);
      // Asegurarse de que data es un array
      if (Array.isArray(data)) {
        setTalleres(data);
      } else {
        console.error("La respuesta no es un array:", data);
        setTalleres([]);
        setError("Error: La respuesta del servidor no es válida");
      }
    } catch (e) {
      console.error("Error cargando talleres:", e);
      setError(e.message);
      setTalleres([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargarTalleres(); }, []);

  async function handleDesbloquear(taller) {
    try {
      await apiSuperAdmin.desbloquearEmergencia(taller.id);
      cargarTalleres();
    } catch (e) {
      alert("Error: " + e.message);
    }
  }

  function handleAccion(tipo, taller) {
    if (tipo === "desbloquear") {
      if (confirm(`¿Levantar el bloqueo de emergencia de "${taller.nombre}"?`)) {
        handleDesbloquear(taller);
      }
      return;
    }
    setModal({ tipo, taller });
  }

  return (
    <div style={{ padding: "1.5rem", color: "#f1f5f9", maxWidth: 1400, background: "#0a1628", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem", color: "#f1f5f9" }}>
            <FiServer style={{ marginRight: 8, verticalAlign: "middle", color: "#f59e0b" }} />
            Panel de Administración de Plataforma
          </h1>
          <p style={{ color: "#94a3b8", margin: "0.3rem 0 0", fontSize: "0.85rem" }}>
            Control total de talleres, usuarios y métricas del SaaS
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => setModal({ tipo: "notificacionMasiva" })}
            style={{
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "0.6rem 1.2rem",
              cursor: "pointer",
              fontWeight: 700,
              fontSize: "0.9rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
            title="Enviar notificación masiva a todos los talleres"
          >
            <FiSend size={16} />
            Notificación Masiva
          </button>
          {tab === "talleres" && (
            <button
              onClick={() => setModal({ tipo: "crearTaller" })}
              style={{
                background: "#10b981",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "0.6rem 1.2rem",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.9rem",
              }}
            >
              + Nuevo Taller
            </button>
          )}
        </div>
      </div>

      {/* Métricas globales */}
      <MetricasGlobales />

      {/* Tabs de navegación */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", borderBottom: "1px solid #1e293b", paddingBottom: "0.5rem" }}>
        {[
          { id: "talleres", label: "Talleres", icon: <FiServer size={15} /> },
          { id: "seguridad", label: "Seguridad", icon: <FiShield size={15} /> },
          { id: "auditoria", label: "Auditoría", icon: <FiList size={15} /> },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: tab === t.id ? "#1e293b" : "transparent",
              border: tab === t.id ? "1px solid #334155" : "1px solid transparent",
              color: tab === t.id ? "#f1f5f9" : "#64748b",
              borderRadius: 6,
              padding: "0.5rem 1rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Contenido según tab */}
      {tab === "talleres" && (
        <div style={{ background: "#0f172a", borderRadius: 10, padding: "1.5rem", border: "1px solid #1e293b" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem", color: "#f1f5f9" }}>Talleres</h2>
            <button
              onClick={cargarTalleres}
              style={{ background: "transparent", border: "1px solid #334155", color: "#94a3b8", borderRadius: 6, padding: "0.4rem 0.8rem", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}
            >
              <FiRefreshCw size={14} /> Actualizar
            </button>
          </div>

        {error && (
          <div style={{ background: "#450a0a", border: "1px solid #ef4444", borderRadius: 6, padding: "0.8rem", marginBottom: "1rem", color: "#fca5a5", display: "flex", alignItems: "center", gap: 8 }}>
            <FiAlertTriangle /> {error}
          </div>
        )}

        {loading ? (
          <p style={{ color: "#94a3b8" }}>Cargando talleres...</p>
        ) : (
          <TablaTalleres talleres={talleres} onAccion={handleAccion} />
        )}
        </div>
      )}

      {tab === "seguridad" && (
        <div style={{ background: "#0f172a", borderRadius: 10, padding: "1.5rem", border: "1px solid #1e293b" }}>
          <SeccionSeguridad talleres={talleres} />
        </div>
      )}

      {tab === "auditoria" && (
        <div style={{ background: "#0f172a", borderRadius: 10, padding: "1.5rem", border: "1px solid #1e293b" }}>
          <SeccionAuditoria talleres={talleres} />
        </div>
      )}

      {/* Modales */}
      {modal?.tipo === "metricas" && (
        <ModalMetricas taller={modal.taller} onClose={() => setModal(null)} />
      )}
      {modal?.tipo === "bloquear" && (
        <ModalBloqueo taller={modal.taller} onClose={() => setModal(null)} onSuccess={cargarTalleres} />
      )}
      {modal?.tipo === "cambiarEstado" && (
        <ModalCambiarEstado taller={modal.taller} onClose={() => setModal(null)} onSuccess={cargarTalleres} />
      )}
      {modal?.tipo === "crearAdmin" && (
        <ModalCrearAdmin taller={modal.taller} onClose={() => setModal(null)} onSuccess={cargarTalleres} />
      )}
      {modal?.tipo === "crearTaller" && (
        <ModalCrearTaller onClose={() => setModal(null)} onSuccess={cargarTalleres} />
      )}
      {modal?.tipo === "editar" && (
        <ModalEditarTaller taller={modal.taller} onClose={() => setModal(null)} onSuccess={cargarTalleres} />
      )}
      {modal?.tipo === "resetMasivo" && (
        <ModalResetMasivo taller={modal.taller} onClose={() => setModal(null)} />
      )}
      {modal?.tipo === "notificacionMasiva" && (
        <ModalNotificacionMasiva talleres={talleres} onClose={() => setModal(null)} />
      )}
      {modal?.tipo === "importarBD" && (
        <ModalImportarBD taller={modal.taller} onClose={() => setModal(null)} onSuccess={cargarTalleres} />
      )}
    </div>
  );
}
