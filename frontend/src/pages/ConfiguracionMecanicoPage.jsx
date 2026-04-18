import { useState, useEffect } from "react";
import { api } from "../api";
import authService from "../services/authService";
import { QRCodeSVG } from "qrcode.react";
import { FiUser } from "react-icons/fi";

export default function ConfiguracionMecanicoPage() {
  const user = authService.getUser();
  const [perfil, setPerfil] = useState(null);

  // ── Cambio de contraseña ──
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", confirm: "" });
  const [msgPass, setMsgPass] = useState("");
  const [loadingPass, setLoadingPass] = useState(false);

  // ── Conexión app móvil ──
  const [infoSistema, setInfoSistema] = useState(null);
  const [qrData, setQrData] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [mostrarQr, setMostrarQr] = useState(false);

  useEffect(() => {
    api.infoSistema().then(setInfoSistema).catch(() => {});
    api.infoConexionQr().then((r) => setQrData(r.qr_data)).catch(() => {});
    if (user?.id) api.obtenerPerfil(user.id).then(setPerfil).catch(() => {});
  }, []);

  async function handleCambiarPassword(e) {
    e.preventDefault();
    if (passwords.new_password !== passwords.confirm) {
      setMsgPass("✗ Las contraseñas nuevas no coinciden");
      return;
    }
    setLoadingPass(true);
    setMsgPass("");
    try {
      await api.cambiarPasswordPropio({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
      });
      setPasswords({ current_password: "", new_password: "", confirm: "" });
      setMsgPass("✓ Contraseña actualizada exitosamente");
      setTimeout(() => setMsgPass(""), 3000);
    } catch (err) {
      setMsgPass("✗ " + err.message);
    } finally {
      setLoadingPass(false);
    }
  }

  const copiarIP = () => {
    if (!infoSistema) return;
    navigator.clipboard.writeText(infoSistema.ip_servidor).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    });
  };

  return (
    <div className="config-page">

      {/* ── Perfil ── */}
      <section className="config-section">
        <h2 className="config-section-title">Mi Perfil</h2>
        <div className="config-list">
          <div className="config-list-item">
            <span className="config-item-name"><FiUser size={14} style={{marginRight:5, verticalAlign:"middle"}} />{user?.username}</span>
            <span style={{ fontSize: "0.8rem", background: "#dbeafe", color: "#1e40af", padding: "2px 10px", borderRadius: "12px" }}>
              {user?.roles?.join(", ")}
            </span>
          </div>
          {perfil?.nombre_completo && (
            <div className="config-list-item">
              <span style={{ color: "#64748b", fontSize: "0.85rem" }}>Nombre</span>
              <span>{perfil.nombre_completo}</span>
            </div>
          )}
          {perfil?.telefono && (
            <div className="config-list-item">
              <span style={{ color: "#64748b", fontSize: "0.85rem" }}>Teléfono</span>
              <span>{perfil.telefono}</span>
            </div>
          )}
          {perfil?.direccion && (
            <div className="config-list-item">
              <span style={{ color: "#64748b", fontSize: "0.85rem" }}>Dirección</span>
              <span>{perfil.direccion}</span>
            </div>
          )}
          <div className="config-list-item">
            <span style={{ color: "#64748b", fontSize: "0.85rem" }}>Email</span>
            <span>{perfil?.email || "—"}</span>
          </div>
        </div>
      </section>

      {/* ── Cambio de contraseña ── */}
      <section className="config-section">
        <h2 className="config-section-title">Cambiar Contraseña</h2>
        <form onSubmit={handleCambiarPassword} className="config-form">
          <div className="config-field">
            <label>Contraseña actual</label>
            <input className="config-input" type="password" value={passwords.current_password}
              onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })} required />
          </div>
          <div className="config-field">
            <label>Nueva contraseña</label>
            <input className="config-input" type="password" placeholder="Mín. 8 caracteres, mayúscula y número"
              value={passwords.new_password}
              onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })} required />
          </div>
          <div className="config-field">
            <label>Confirmar nueva contraseña</label>
            <input className="config-input" type="password" value={passwords.confirm}
              onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} required />
          </div>
          <div className="config-save-row">
            <button className="btn-primary" type="submit" disabled={loadingPass}>
              {loadingPass ? "Actualizando..." : "Cambiar Contraseña"}
            </button>
            {msgPass && <span className={`config-msg ${msgPass.startsWith("✓") ? "ok" : "err"}`}>{msgPass}</span>}
          </div>
        </form>
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
            <button className="btn-primary" style={{ marginBottom: 12 }} onClick={() => setMostrarQr(!mostrarQr)}>
              {mostrarQr ? "Ocultar QR" : "Mostrar QR de conexión"}
            </button>
            {mostrarQr && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 8 }}>
                <div style={{ background: "#fff", padding: 16, borderRadius: 12, display: "inline-block", border: "1px solid #e2e8f0" }}>
                  <QRCodeSVG value={qrData} size={200} />
                </div>
                <p className="ip-hint">
                  En la app: toca <strong>Configuracion → Escanear QR</strong> y apunta la cámara aquí.
                </p>
              </div>
            )}
          </div>
        )}
      </section>

    </div>
  );
}
