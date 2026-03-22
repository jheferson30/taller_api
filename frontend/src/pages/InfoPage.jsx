import { useEffect, useState } from "react";
import { api } from "../api";

export default function InfoPage() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    api.infoSistema().then(setInfo).catch(() => {});
  }, []);

  return (
    <section className="info-page">
      <div className="info-header">
        <h2>Información del Sistema</h2>
        <p className="subtitle">Datos de configuración y contacto del desarrollador</p>
      </div>

      {/* Tarjeta sistema */}
      <div className="info-sys-card">
        <div className="info-sys-card-icon">⚙</div>
        <div className="info-sys-card-content">
          <h3>Sistema</h3>
          <div className="info-rows">
            <div className="info-row">
              <span className="info-label">Nombre</span>
              <span className="info-value">{info?.sistema || "Taller Manager"}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Versión</span>
              <span className="info-value">{info?.version || "1.0.0"}</span>
            </div>
            <div className="info-row">
              <span className="info-label">URL completa</span>
              <span className="info-value">{info?.url_app_movil || "..."}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tarjeta desarrollador */}
      <div className="info-sys-card dev-card">
        <div className="info-sys-card-icon">Dev</div>
        <div className="info-sys-card-content">
          <h3>Desarrollador</h3>
          <div className="info-rows">
            <div className="info-row">
              <span className="info-label">Nombre</span>
              <span className="info-value">{info?.desarrollador?.nombre}</span>
            </div>
            <div className="info-row">
              <span className="info-label">WhatsApp</span>
              <a
                className="info-value info-link"
                href={`https://wa.me/57${info?.desarrollador?.whatsapp}`}
                target="_blank"
                rel="noreferrer"
              >
                {info?.desarrollador?.whatsapp}
              </a>
            </div>
            <div className="info-row">
              <span className="info-label">Correo</span>
              <a
                className="info-value info-link"
                href={`mailto:${info?.desarrollador?.correo}`}
              >
                {info?.desarrollador?.correo}
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
