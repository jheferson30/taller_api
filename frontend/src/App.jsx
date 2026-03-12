import { NavLink, Route, Routes } from "react-router-dom";
import RecepcionPage from "./pages/RecepcionPage";
import TicketPage from "./pages/TicketPage";
import EconomiaPage from "./pages/EconomiaPage";
import CitasPage from "./pages/CitasPage";
import Starfield from "./components/Starfield";

export default function App() {
  return (
    <>
      <Starfield />
      <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">TM</div>
          <div>
            <h1>Taller Manager</h1>
            <p>Operacion diaria</p>
          </div>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Recepcion
          </NavLink>
          <NavLink to="/tickets">Tickets</NavLink>
          <NavLink to="/citas">Citas</NavLink>
          <NavLink to="/economia">Economia</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<RecepcionPage />} />
          <Route path="/tickets" element={<TicketPage />} />
          <Route path="/citas" element={<CitasPage />} />
          <Route path="/economia" element={<EconomiaPage />} />
        </Routes>
      </main>
    </div>
    </>
  );
}
