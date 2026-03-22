import { NavLink, Route, Routes } from "react-router-dom";
import RecepcionPage from "./pages/RecepcionPage";
import TicketPage from "./pages/TicketPage";
import EconomiaPage from "./pages/EconomiaPage";
import CitasPage from "./pages/CitasPage";
import EntregadosPage from "./pages/EntregadosPage";
import InfoPage from "./pages/InfoPage";
import ConfiguracionPage from "./pages/ConfiguracionPage";
import Starfield from "./components/Starfield";

export default function App() {
  return (
    <>
      <Starfield />
      <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/assets/logo.png" alt="PULGA Mecánica Fi" className="brand-logo-img" />
        </div>
        <nav className="nav">
          <NavLink to="/" end>Recepcion</NavLink>
          <NavLink to="/tickets">Tickets</NavLink>
          <NavLink to="/citas">Citas</NavLink>
          <NavLink to="/entregados">Entregados</NavLink>
          <NavLink to="/economia">Economia</NavLink>
          <NavLink to="/configuracion">Configuracion</NavLink>
          <NavLink to="/info">Info</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<RecepcionPage />} />
          <Route path="/tickets" element={<TicketPage />} />
          <Route path="/citas" element={<CitasPage />} />
          <Route path="/economia" element={<EconomiaPage />} />
          <Route path="/entregados" element={<EntregadosPage />} />
          <Route path="/info" element={<InfoPage />} />
          <Route path="/configuracion" element={<ConfiguracionPage />} />
        </Routes>
      </main>
    </div>
    </>
  );
}
