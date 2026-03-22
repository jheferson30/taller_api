import { useState } from "react";
import { api } from "../api";

export default function EconomiaAuth({ onAutenticado, modoInicial = "login" }) {
  const [modo, setModo] = useState(modoInicial); // login, crear, recuperar
  const [password, setPassword] = useState("");
  const [palabraClave, setPalabraClave] = useState("");
  const [nuevaPassword, setNuevaPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();
    setMsg("");
    setLoading(true);

    try {
      await api.validarPasswordEconomia({ password });
      onAutenticado();
    } catch (err) {
      setMsg("✗ " + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCrear(e) {
    e.preventDefault();
    setMsg("");
    setLoading(true);

    try {
      await api.crearPasswordEconomia({ password, palabra_clave: palabraClave });
      setMsg("✓ Contraseña creada exitosamente");
      setTimeout(() => {
        onAutenticado();
      }, 1000);
    } catch (err) {
      setMsg("✗ " + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecuperar(e) {
    e.preventDefault();
    setMsg("");
    setLoading(false);

    try {
      await api.recuperarPasswordEconomia({
        palabra_clave: palabraClave,
        nueva_password: nuevaPassword,
      });
      setMsg("✓ Contraseña actualizada exitosamente");
      setTimeout(() => {
        setModo("login");
        setPassword("");
        setPalabraClave("");
        setNuevaPassword("");
        setMsg("");
      }, 1500);
    } catch (err) {
      setMsg("✗ " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="economia-auth-container">
      <div className="economia-auth-card">
        <div className="auth-icon"></div>
        <h2>Acceso a Economía</h2>
        <p className="auth-subtitle">
          Esta sección contiene información financiera sensible
        </p>

        {modo === "login" && (
          <form onSubmit={handleLogin} className="auth-form">
            <div className="form-group">
              <label>Contraseña</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Ingresa tu contraseña"
                required
                autoFocus
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Verificando..." : "Ingresar"}
            </button>

            <div className="auth-links">
              <button
                type="button"
                onClick={() => setModo("recuperar")}
                className="link-button"
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>
          </form>
        )}

        {modo === "crear" && (
          <form onSubmit={handleCrear} className="auth-form">
            <p className="info-text">
              Crea una contraseña para proteger el acceso a la información
              financiera
            </p>

            <div className="form-group">
              <label>Contraseña (mínimo 4 caracteres)</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Crea una contraseña"
                required
                minLength={4}
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Palabra Clave de Recuperación (mínimo 3 caracteres)</label>
              <input
                type="text"
                value={palabraClave}
                onChange={(e) => setPalabraClave(e.target.value)}
                placeholder="Ej: nombre de tu mascota"
                required
                minLength={3}
              />
              <small className="help-text">
                Úsala para recuperar tu contraseña si la olvidas
              </small>
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Creando..." : "Crear Contraseña"}
            </button>
          </form>
        )}

        {modo === "recuperar" && (
          <form onSubmit={handleRecuperar} className="auth-form">
            <p className="info-text">
              Ingresa tu palabra clave para restablecer tu contraseña
            </p>

            <div className="form-group">
              <label>Palabra Clave</label>
              <input
                type="text"
                value={palabraClave}
                onChange={(e) => setPalabraClave(e.target.value)}
                placeholder="Tu palabra clave de recuperación"
                required
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Nueva Contraseña (mínimo 4 caracteres)</label>
              <input
                type="password"
                value={nuevaPassword}
                onChange={(e) => setNuevaPassword(e.target.value)}
                placeholder="Nueva contraseña"
                required
                minLength={4}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Actualizando..." : "Restablecer Contraseña"}
            </button>

            <div className="auth-links">
              <button
                type="button"
                onClick={() => {
                  setModo("login");
                  setPalabraClave("");
                  setNuevaPassword("");
                  setMsg("");
                }}
                className="link-button"
              >
                Volver al inicio de sesión
              </button>
            </div>
          </form>
        )}

        {msg && (
          <p className={`auth-message ${msg.startsWith("✓") ? "success" : "error"}`}>
            {msg}
          </p>
        )}
      </div>
    </div>
  );
}
