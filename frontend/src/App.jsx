import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import RecepcionPage from "./pages/RecepcionPage";
import TicketPage from "./pages/TicketPage";
import EconomiaPage from "./pages/EconomiaPage";
import CitasPage from "./pages/CitasPage";
import EntregadosPage from "./pages/EntregadosPage";
import InfoPage from "./pages/InfoPage";
import ConfiguracionPage from "./pages/ConfiguracionPage";
import ConfiguracionMecanicoPage from "./pages/ConfiguracionMecanicoPage";
import Starfield from "./components/Starfield";
import LoginPage from "./pages/LoginPage";
import authService from "./services/authService";

function getRoles() {
  const user = authService.getUser();
  const roles = user?.roles || [];
  return {
    isAdmin: roles.includes("ADMIN"),
    isMecanico: roles.includes("MECANICO") && !roles.includes("ADMIN"),
    isRecepcionista: roles.includes("RECEPCIONISTA") && !roles.includes("ADMIN"),
    username: user?.username || "",
  };
}

function AppLayout({ children }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  const { isAdmin, isMecanico, isRecepcionista, username } = getRoles();

  async function handleLogout() {
    await authService.logout();
    window.location.href = "/login";
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/assets/logo.png" alt="PULGA Mecánica Fi" className="brand-logo-img" />
        </div>
        <nav className="nav">
          <NavLink to="/" end>Recepcion</NavLink>
          <NavLink to="/tickets">Tickets</NavLink>
          <NavLink to="/citas">Citas</NavLink>
          {/* Entregados: ADMIN y RECEPCIONISTA */}
          {(isAdmin || isRecepcionista) && <NavLink to="/entregados">Entregados</NavLink>}
          {/* Economía: solo ADMIN */}
          {isAdmin && <NavLink to="/economia">Economia</NavLink>}
          {/* Configuración: ADMIN y MECANICO y RECEPCIONISTA */}
          {(isAdmin || isMecanico || isRecepcionista) && <NavLink to="/configuracion">Configuracion</NavLink>}
          <NavLink to="/info">Info</NavLink>
        </nav>
        <div className="sidebar-footer">
          <span className="sidebar-user">👤 {username}</span>
          <button className="sidebar-logout" onClick={handleLogout}>
            Cerrar Sesión
          </button>
        </div>
      </aside>
      <main className="content">
        {children}
      </main>
    </div>
  );
}

// Componente que bloquea acceso si el rol no tiene permiso
function RoleGuard({ allowed, children }) {
  const { isAdmin, isMecanico, isRecepcionista } = getRoles();
  const hasAccess =
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
  const { isAdmin, isMecanico } = getRoles();

  return (
    <>
      <Starfield />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Páginas para todos los roles */}
        <Route path="/" element={<AppLayout><RecepcionPage /></AppLayout>} />
        <Route path="/tickets" element={<AppLayout><TicketPage /></AppLayout>} />
        <Route path="/citas" element={<AppLayout><CitasPage /></AppLayout>} />
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
