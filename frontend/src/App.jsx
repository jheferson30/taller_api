import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import RecepcionPage from "./pages/RecepcionPage";
import TicketPage from "./pages/TicketPage";
import EconomiaPage from "./pages/EconomiaPage";
import CitasPage from "./pages/CitasPage";
import EntregadosPage from "./pages/EntregadosPage";
import InfoPage from "./pages/InfoPage";
import ConfiguracionPage from "./pages/ConfiguracionPage";
import ConfiguracionMecanicoPage from "./pages/ConfiguracionMecanicoPage";
import SuperAdminPage from "./pages/SuperAdminPage";
import Starfield from "./components/Starfield";
import LoginPage from "./pages/LoginPage";
import authService from "./services/authService";
import NotificationBadge from "./components/NotificationBadge";
import NotificationBanner from "./components/NotificationBanner";
import { FiEdit2, FiCamera, FiGrid, FiClipboard, FiCalendar, FiCheckSquare, FiTrendingUp, FiSettings, FiInfo, FiShield } from 'react-icons/fi';
import { api } from "./api";

function getRoles() {
  const user = authService.getUser();
  const roles = user?.roles || [];
  return {
    isSuperAdmin: roles.includes("SUPER_ADMIN"),
    isAdmin: roles.includes("ADMIN") && !roles.includes("SUPER_ADMIN"),
    isMecanico: roles.includes("MECANICO") && !roles.includes("ADMIN") && !roles.includes("SUPER_ADMIN"),
    isRecepcionista: roles.includes("RECEPCIONISTA") && !roles.includes("ADMIN") && !roles.includes("SUPER_ADMIN"),
    username: user?.username || "",
  };
}

function AppLayout({ children }) {
  const { isSuperAdmin, isAdmin, isMecanico, isRecepcionista, username } = getRoles();
  const [logoUrl, setLogoUrl] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const fileInputRef = useRef(null);
  const notifRefreshRef = useRef(null);

  // Escuchar evento global para refrescar notificaciones desde cualquier página
  useEffect(() => {
    function handleNotifRefresh() {
      if (notifRefreshRef.current) notifRefreshRef.current();
    }
    window.addEventListener("notif:refresh", handleNotifRefresh);
    return () => window.removeEventListener("notif:refresh", handleNotifRefresh);
  }, []);

  useEffect(() => {
    api.obtenerLogo()
      .then(r => setLogoUrl(r.logo_url || "/assets/logo.png"))
      .catch(() => setLogoUrl("/assets/logo.png"));
  }, []);

  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  // Si es SUPER_ADMIN, redirigir a su dashboard
  if (isSuperAdmin && window.location.pathname !== "/super-admin") {
    return <Navigate to="/super-admin" replace />;
  }

  async function handleLogoChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const r = await api.subirLogo(formData);
      setLogoUrl(r.logo_url);
    } catch (err) {
      alert("Error subiendo logo: " + err.message);
    }
  }

  async function handleLogout() {
    await authService.logout();
    window.location.href = "/login";
  }

  // En producción, usar URL relativa (mismo dominio). En desarrollo, localhost:8000
  const API_BASE = import.meta.env.VITE_API_URL !== undefined 
    ? import.meta.env.VITE_API_URL 
    : (import.meta.env.MODE === 'production' ? '' : 'http://127.0.0.1:8000');

  return (
    <div className="app-shell">
      {/* Botón hamburguesa para móvil */}
      <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menú">
        <span /><span /><span />
      </button>
      {/* Overlay para cerrar sidebar en móvil */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? " sidebar--open" : ""}`}>
        <div className="brand" style={{ position: "relative", cursor: isAdmin ? "pointer" : "default" }}
          onClick={() => isAdmin && fileInputRef.current?.click()}
          title={isAdmin ? "Haz clic para cambiar el logo" : ""}
        >
          {logoUrl ? (
            <img src={logoUrl.startsWith("/uploads") ? `${API_BASE}${logoUrl}` : logoUrl} alt="Logo taller" className="brand-logo-img" />
          ) : (
            <div style={{ width: "100%", maxWidth: 140, height: 80, border: "2px dashed rgba(255,255,255,0.3)", borderRadius: 8, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.5)", fontSize: "0.75rem", textAlign: "center", padding: "0.5rem" }}>
              {isAdmin ? <><FiCamera size={20} style={{marginBottom:4}} /><br />Subir logo</> : "Sin logo"}
            </div>
          )}
          {isAdmin && logoUrl && (
            <div style={{ position: "absolute", bottom: 0, right: 0, background: "rgba(0,0,0,0.6)", borderRadius: "50%", width: 24, height: 24, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <FiEdit2 size={12} color="#fff" />
            </div>
          )}
        </div>
        {isAdmin && <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleLogoChange} />}
        <nav className="nav">
          {isSuperAdmin ? (
            // Menú para SUPER_ADMIN
            <>
              <NavLink to="/super-admin" onClick={() => setSidebarOpen(false)}>
                <FiShield size={17} style={{marginRight:8, verticalAlign:'middle'}} />Dashboard
              </NavLink>
              <NavLink to="/info" onClick={() => setSidebarOpen(false)}>
                <FiInfo size={17} style={{marginRight:8, verticalAlign:'middle'}} />Info
              </NavLink>
            </>
          ) : (
            // Menú para roles de taller (ADMIN, MECANICO, RECEPCIONISTA)
            <>
              <NavLink to="/" end onClick={() => setSidebarOpen(false)}><FiGrid size={17} style={{marginRight:8, verticalAlign:'middle'}} />Recepcion</NavLink>
              <NavLink to="/tickets" onClick={() => setSidebarOpen(false)}><FiClipboard size={17} style={{marginRight:8, verticalAlign:'middle'}} />Tickets</NavLink>
              <NavLink to="/citas" onClick={() => setSidebarOpen(false)}><FiCalendar size={17} style={{marginRight:8, verticalAlign:'middle'}} />Citas</NavLink>
              {(isAdmin || isRecepcionista) && <NavLink to="/entregados" onClick={() => setSidebarOpen(false)}><FiCheckSquare size={17} style={{marginRight:8, verticalAlign:'middle'}} />Entregados</NavLink>}
              {isAdmin && <NavLink to="/economia" onClick={() => setSidebarOpen(false)}><FiTrendingUp size={17} style={{marginRight:8, verticalAlign:'middle'}} />Economia</NavLink>}
              {(isAdmin || isMecanico || isRecepcionista) && <NavLink to="/configuracion" onClick={() => setSidebarOpen(false)}><FiSettings size={17} style={{marginRight:8, verticalAlign:'middle'}} />Configuracion</NavLink>}
              <NavLink to="/info" onClick={() => setSidebarOpen(false)}><FiInfo size={17} style={{marginRight:8, verticalAlign:'middle'}} />Info</NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-footer">
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#1e293b", border: "2px solid var(--brand-primary)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "700", fontSize: "0.8rem", color: "var(--brand-primary)", flexShrink: 0 }}>
                {username.slice(0, 2).toUpperCase()}
              </div>
              <span className="sidebar-user" style={{ fontSize: "0.9rem" }}>{username}</span>
            </div>
            {!isSuperAdmin && <NotificationBadge onRefreshRef={notifRefreshRef} />}
          </div>
          <button className="sidebar-logout" onClick={handleLogout}>
            Cerrar Sesión
          </button>
        </div>
      </aside>
      <main className="content">
        {!isSuperAdmin && <NotificationBanner />}
        {children}
      </main>
    </div>
  );
}

// Componente que bloquea acceso si el rol no tiene permiso
function RoleGuard({ allowed, children }) {
  const { isSuperAdmin, isAdmin, isMecanico, isRecepcionista } = getRoles();
  const hasAccess =
    (allowed.includes("SUPER_ADMIN") && isSuperAdmin) ||
    (allowed.includes("ADMIN") && isAdmin) ||
    (allowed.includes("MECANICO") && isMecanico) ||
    (allowed.includes("RECEPCIONISTA") && isRecepcionista);

  if (!hasAccess) return <Navigate to="/" replace />;
  return children;
}

// Decide qué página de configuración mostrar según el rol
function ConfiguracionRouter() {
  const { isAdmin } = getRoles();
  return isAdmin ? <ConfiguracionPage /> : <ConfiguracionMecanicoPage />;
}

export default function App() {
  return (
    <>
      <Starfield />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Ruta exclusiva para SUPER_ADMIN */}
        <Route path="/super-admin" element={
          <AppLayout>
            <RoleGuard allowed={["SUPER_ADMIN"]}>
              <SuperAdminPage />
            </RoleGuard>
          </AppLayout>
        } />

        {/* Páginas para roles de taller (ADMIN, MECANICO, RECEPCIONISTA) */}
        <Route path="/" element={
          <AppLayout>
            <RoleGuard allowed={["ADMIN", "MECANICO", "RECEPCIONISTA"]}>
              <RecepcionPage />
            </RoleGuard>
          </AppLayout>
        } />
        
        <Route path="/tickets" element={
          <AppLayout>
            <RoleGuard allowed={["ADMIN", "MECANICO", "RECEPCIONISTA"]}>
              <TicketPage />
            </RoleGuard>
          </AppLayout>
        } />
        
        <Route path="/citas" element={
          <AppLayout>
            <RoleGuard allowed={["ADMIN", "MECANICO", "RECEPCIONISTA"]}>
              <CitasPage />
            </RoleGuard>
          </AppLayout>
        } />

        {/* Info: accesible para todos los roles */}
        <Route path="/info" element={<AppLayout><InfoPage /></AppLayout>} />

        {/* Entregados: ADMIN y RECEPCIONISTA */}
        <Route path="/entregados" element={
          <AppLayout>
            <RoleGuard allowed={["ADMIN", "RECEPCIONISTA"]}>
              <EntregadosPage />
            </RoleGuard>
          </AppLayout>
        } />

        {/* Economía: solo ADMIN */}
        <Route path="/economia" element={
          <AppLayout>
            <RoleGuard allowed={["ADMIN"]}>
              <EconomiaPage />
            </RoleGuard>
          </AppLayout>
        } />

        {/* Configuración: ADMIN ve todo, MECANICO y RECEPCIONISTA ven versión reducida */}
        <Route path="/configuracion" element={
          <AppLayout>
            <RoleGuard allowed={["ADMIN", "MECANICO", "RECEPCIONISTA"]}>
              <ConfiguracionRouter />
            </RoleGuard>
          </AppLayout>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
