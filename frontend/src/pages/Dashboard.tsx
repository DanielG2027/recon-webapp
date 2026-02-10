import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DashboardData } from "../api";

const WELCOME_LINES = [
  "Wake up, Samurai. We've got a network to burn.",
  "The Blackwall doesn't keep things out. It keeps things in.",
  "In Night City, information is the sharpest blade you can carry.",
  "Don't fear the ICE. Fear what's hiding behind it.",
  "Everything is connected. You just need to know where to look.",
  "A netrunner's best weapon? Patience and a good daemon.",
  "Beyond the Blackwall, data doesn't sleep — and neither should you.",
  "Night City's dirtiest secrets live on port 443.",
  "Remember: the best intrusion is the one they never detect.",
  "Trust the process. Enumerate. Correlate. Dominate.",
];

function getWelcomeMessage(): string {
  // Rotate daily so it feels fresh but not random per page-load
  const dayIndex = Math.floor(Date.now() / 86400000) % WELCOME_LINES.length;
  return WELCOME_LINES[dayIndex];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showWelcome, setShowWelcome] = useState(true);

  useEffect(() => {
    api.get<DashboardData>("/api/dashboard").then(setData).catch((e) => setErr(e.message));
    // Dismiss welcome if user closed it this session
    const dismissed = sessionStorage.getItem("bw_welcome_dismissed");
    if (dismissed === "1") setShowWelcome(false);
  }, []);

  const dismissWelcome = () => {
    setShowWelcome(false);
    sessionStorage.setItem("bw_welcome_dismissed", "1");
  };

  if (err) return <div className="page-error">Error: {err}</div>;
  if (!data) return <div className="loading">Jacking into Blackwall...</div>;

  return (
    <div className="page">
      <h1>Dashboard</h1>

      {/* Welcome banner */}
      {showWelcome && (
        <div className="welcome-banner">
          <button className="welcome-dismiss" onClick={dismissWelcome} title="Dismiss">&times;</button>
          <p className="welcome-title">System Online</p>
          <p className="welcome-text">
            {getWelcomeMessage()}
            <br />
            <em>Blackwall v0.1 &mdash; Local Recon Suite active.</em>
          </p>
        </div>
      )}

      {/* Stats row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">{data.high_risk_count}</div>
          <div className="stat-label">High-Risk Findings</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_findings}</div>
          <div className="stat-label">Total Findings</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.recent_jobs.length}</div>
          <div className="stat-label">Recent Jobs</div>
        </div>
      </div>

      {/* Top pathway */}
      {data.top_pathway ? (
        <section className="card">
          <h2>Top Pathway to Initial Access</h2>
          <p className="pathway-hypothesis">{data.top_pathway.hypothesis}</p>
          <p className="text-muted">Confidence: {(data.top_pathway.score * 100).toFixed(0)}%</p>
          {data.top_pathway.evidence.length > 0 && (
            <ul>
              {data.top_pathway.evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section className="card">
          <h2>Top Pathway to Initial Access</h2>
          <p className="text-muted">No high-risk findings yet. Run recon modules to correlate results.</p>
        </section>
      )}

      {/* Quick tools: DNS + Ping */}
      <h2>Quick Tools</h2>
      <div className="dash-tools">
        <DashDnsTool />
        <DashPingTool />
      </div>

      {/* Recent jobs */}
      <section className="card">
        <h2>Recent Jobs</h2>
        {data.recent_jobs.length === 0 ? (
          <p className="text-muted">No jobs yet.</p>
        ) : (
          <ul className="job-list">
            {data.recent_jobs.map((j) => (
              <li key={j.id}>
                <Link to={`/jobs?job=${j.id}`}>{j.module}</Link>
                {" "}&mdash; <span className={`status-${j.status}`}>{j.status}</span>
                {" "}&mdash; {new Date(j.created_at).toLocaleString()}
              </li>
            ))}
          </ul>
        )}
        <p><Link to="/jobs">View all jobs</Link></p>
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Inline DNS widget                                                   */
/* ------------------------------------------------------------------ */
function DashDnsTool() {
  const [target, setTarget] = useState("");
  const [rtype, setRtype] = useState("A");
  const [result, setResult] = useState<{ records: { name: string; type: string; value: string }[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = () => {
    if (!target.trim()) return;
    setLoading(true); setErr(null); setResult(null);
    api.post<{ records: { name: string; type: string; value: string }[] }>("/api/tools/dns", { target, record_type: rtype })
      .then(setResult)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  return (
    <div className="dash-tool-widget">
      <h3>DNS Lookup</h3>
      <div className="dash-tool-row">
        <input
          placeholder="example.com"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
        />
        <select value={rtype} onChange={(e) => setRtype(e.target.value)}>
          {["A","AAAA","MX","NS","TXT","CNAME","SOA","ANY"].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <button className="primary" onClick={run} disabled={loading}>{loading ? "..." : "Go"}</button>
      </div>
      {err && <p className="error">{err}</p>}
      {result && result.records.length > 0 && (
        <table className="table">
          <thead><tr><th>Name</th><th>Type</th><th>Value</th></tr></thead>
          <tbody>
            {result.records.map((r, i) => <tr key={i}><td>{r.name}</td><td>{r.type}</td><td>{r.value}</td></tr>)}
          </tbody>
        </table>
      )}
      {result && result.records.length === 0 && <p className="text-muted">No records.</p>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Inline Ping widget                                                  */
/* ------------------------------------------------------------------ */
function DashPingTool() {
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<{ alive: boolean; raw: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = () => {
    if (!target.trim()) return;
    setLoading(true); setErr(null); setResult(null);
    api.post<{ alive: boolean; raw: string }>("/api/tools/ping", { target, count: 3 })
      .then(setResult)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  return (
    <div className="dash-tool-widget">
      <h3>Ping</h3>
      <div className="dash-tool-row">
        <input
          placeholder="10.0.0.1 or example.com"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
        />
        <button className="primary" onClick={run} disabled={loading}>{loading ? "..." : "Go"}</button>
      </div>
      {err && <p className="error">{err}</p>}
      {result && (
        <div>
          <p>{result.alive ? <span className="status-succeeded">Host is alive</span> : <span className="status-failed">No response</span>}</p>
          <details className="raw-details">
            <summary>Raw output</summary>
            <pre className="raw-output">{result.raw}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
