import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import Wizard from "./pages/Wizard";
import Tools from "./pages/Tools";
import Jobs from "./pages/Jobs";
import Results from "./pages/Results";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";

function Nav() {
  const link = (to: string, label: string) => (
    <NavLink
      to={to}
      className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
    >
      {label}
    </NavLink>
  );
  return (
    <nav className="nav">
      <div className="nav-brand">Blackwall</div>

      <div className="nav-section">Overview</div>
      {link("/", "Dashboard")}

      <div className="nav-section">Recon</div>
      {link("/tools", "Tools")}
      {link("/wizard", "New Recon")}
      {link("/jobs", "Jobs")}

      <div className="nav-section">Intel</div>
      {link("/projects", "Projects")}
      {link("/results", "Results")}
      {link("/reports", "Reports")}

      <div className="nav-section">System</div>
      {link("/settings", "Settings")}
    </nav>
  );
}

export default function App() {
  return (
    <div className="app">
      <Nav />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/wizard" element={<Wizard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/results" element={<Results />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
