import { useState } from "react";
import { api } from "../api";

/* ------------------------------------------------------------------ */
/* Tool definitions with categories                                    */
/* ------------------------------------------------------------------ */

type ToolId =
  | "whois" | "dns" | "reverse-dns" | "ping" | "portscan" | "headers" | "subnet-calc"
  | "subdomain-enum" | "tech-detect" | "email-harvest" | "social-lookup" | "wayback";

type Category = "network" | "web" | "osint";

interface FieldDef {
  key: string;
  label: string;
  placeholder: string;
  defaultValue?: string;
  type?: "text" | "number" | "select";
  options?: string[];
}

interface ToolDef {
  id: ToolId;
  name: string;
  desc: string;
  category: Category;
  tag?: string;
  fields: FieldDef[];
}

const TOOLS: ToolDef[] = [
  /* --- Network --- */
  {
    id: "ping", name: "Ping", desc: "ICMP connectivity check", category: "network",
    fields: [
      { key: "target", label: "Target", placeholder: "10.0.0.1 or example.com" },
      { key: "count", label: "Count", placeholder: "4", defaultValue: "4", type: "number" },
    ],
  },
  {
    id: "dns", name: "DNS Lookup", desc: "Query A, MX, NS, TXT and more", category: "network",
    fields: [
      { key: "target", label: "Target", placeholder: "example.com" },
      { key: "record_type", label: "Record type", placeholder: "A", defaultValue: "A", type: "select",
        options: ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "SRV", "ANY"] },
    ],
  },
  {
    id: "reverse-dns", name: "Reverse DNS", desc: "PTR lookup for an IP address", category: "network",
    fields: [{ key: "ip", label: "IP Address", placeholder: "8.8.8.8" }],
  },
  {
    id: "portscan", name: "Port Scan", desc: "TCP scan via nmap or socket fallback", category: "network", tag: "Active",
    fields: [
      { key: "target", label: "Target", placeholder: "10.0.0.1" },
      { key: "ports", label: "Ports", placeholder: "1-1024", defaultValue: "1-1024" },
    ],
  },
  {
    id: "subnet-calc", name: "Subnet Calc", desc: "CIDR breakdown and host count", category: "network",
    fields: [{ key: "cidr", label: "CIDR", placeholder: "192.168.1.0/24" }],
  },

  /* --- Web --- */
  {
    id: "headers", name: "HTTP Headers", desc: "Fetch response headers from a URL", category: "web",
    fields: [{ key: "url", label: "URL", placeholder: "https://example.com" }],
  },
  {
    id: "tech-detect", name: "Tech Detect", desc: "Identify web technologies and frameworks", category: "web", tag: "OSINT",
    fields: [{ key: "url", label: "URL", placeholder: "https://example.com" }],
  },

  /* --- OSINT --- */
  {
    id: "whois", name: "WHOIS / RDAP", desc: "Domain and IP registration data", category: "osint",
    fields: [{ key: "target", label: "Target", placeholder: "example.com or 8.8.8.8" }],
  },
  {
    id: "subdomain-enum", name: "Subdomain Enum", desc: "Discover subdomains via DNS brute-force", category: "osint", tag: "Passive",
    fields: [
      { key: "domain", label: "Domain", placeholder: "example.com" },
    ],
  },
  {
    id: "email-harvest", name: "Email Harvest", desc: "Find public emails for a domain", category: "osint", tag: "Passive",
    fields: [{ key: "domain", label: "Domain", placeholder: "example.com" }],
  },
  {
    id: "social-lookup", name: "Social Lookup", desc: "Check username across public platforms", category: "osint", tag: "Passive",
    fields: [{ key: "username", label: "Username", placeholder: "johndoe" }],
  },
  {
    id: "wayback", name: "Wayback URLs", desc: "Historical URLs from Wayback Machine", category: "osint", tag: "Passive",
    fields: [{ key: "domain", label: "Domain", placeholder: "example.com" }],
  },
];

const CATEGORIES: { key: Category; label: string }[] = [
  { key: "network", label: "Network" },
  { key: "web", label: "Web" },
  { key: "osint", label: "OSINT" },
];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function Tools() {
  const [activeTool, setActiveTool] = useState<ToolId | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const selectTool = (id: ToolId) => {
    setActiveTool(id);
    setResult(null);
    setErr(null);
    const tool = TOOLS.find((t) => t.id === id)!;
    const defaults: Record<string, string> = {};
    tool.fields.forEach((f) => { defaults[f.key] = f.defaultValue || ""; });
    setForm(defaults);
  };

  const run = async () => {
    if (!activeTool) return;
    setLoading(true); setErr(null); setResult(null);
    try {
      const tool = TOOLS.find((t) => t.id === activeTool)!;
      const body: Record<string, unknown> = {};
      tool.fields.forEach((f) => {
        const v = form[f.key] ?? f.defaultValue ?? "";
        body[f.key] = f.type === "number" ? Number(v) : v;
      });
      const res = await api.post<Record<string, unknown>>(`/api/tools/${activeTool}`, body);
      setResult(res);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const tool = activeTool ? TOOLS.find((t) => t.id === activeTool) : null;

  return (
    <div className="page">
      <h1>Tools</h1>
      <p className="text-muted">Quick-access recon utilities — no project required.</p>

      {CATEGORIES.map((cat) => (
        <div key={cat.key}>
          <div className="tools-section-title">{cat.label}</div>
          <div className="tools-grid">
            {TOOLS.filter((t) => t.category === cat.key).map((t) => (
              <button
                key={t.id}
                className={`tool-card${activeTool === t.id ? " tool-card-active" : ""}`}
                onClick={() => selectTool(t.id)}
              >
                <span className="tool-card-name">{t.name}</span>
                <span className="tool-card-desc">{t.desc}</span>
                {t.tag && <span className="tool-card-tag">{t.tag}</span>}
              </button>
            ))}
          </div>
        </div>
      ))}

      {tool && (
        <section className="card tool-panel">
          <h2>{tool.name}</h2>
          <div className="tool-form">
            {tool.fields.map((f) => (
              <div key={f.key} className="tool-field">
                <label>{f.label}</label>
                {f.type === "select" && f.options ? (
                  <select
                    value={form[f.key] ?? f.defaultValue ?? ""}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  >
                    {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type={f.type === "number" ? "number" : "text"}
                    value={form[f.key] ?? ""}
                    placeholder={f.placeholder}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                    onKeyDown={(e) => e.key === "Enter" && run()}
                  />
                )}
              </div>
            ))}
            <button className="primary" onClick={run} disabled={loading}>
              {loading ? "Running…" : "Execute"}
            </button>
          </div>

          {err && <p className="error">{err}</p>}

          {result && (
            <div className="tool-result">
              <ToolResult toolId={activeTool!} data={result} />
            </div>
          )}
        </section>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Per-tool result renderers                                           */
/* ------------------------------------------------------------------ */

function ToolResult({ toolId, data }: { toolId: ToolId; data: Record<string, unknown> }) {
  switch (toolId) {
    case "whois":
      return <RawResult data={data} fields={["target"]} rawKey="raw" />;

    case "dns":
      return (
        <div>
          <p><strong>{String(data.target)}</strong> &mdash; {String(data.record_type)}</p>
          {Array.isArray(data.records) && data.records.length > 0 ? (
            <table className="table">
              <thead><tr><th>Name</th><th>Type</th><th>Value</th></tr></thead>
              <tbody>
                {(data.records as { name: string; type: string; value: string }[]).map((r, i) => (
                  <tr key={i}><td>{r.name}</td><td>{r.type}</td><td>{r.value}</td></tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-muted">No records returned.</p>}
          <RawBlock raw={data.raw} />
        </div>
      );

    case "reverse-dns":
      return (
        <div>
          <p><strong>{String(data.ip)}</strong></p>
          {Array.isArray(data.hostnames) && data.hostnames.length > 0
            ? <ul>{(data.hostnames as string[]).map((h, i) => <li key={i}>{h}</li>)}</ul>
            : <p className="text-muted">No PTR records found.</p>}
        </div>
      );

    case "ping":
      return (
        <div>
          <p><strong>{String(data.target)}</strong> &mdash; {data.alive ? <span className="status-succeeded">Alive</span> : <span className="status-failed">No response</span>}</p>
          <RawBlock raw={data.raw} />
        </div>
      );

    case "portscan":
      return (
        <div>
          <p><strong>{String(data.target)}</strong> &mdash; ports: {String(data.ports_scanned)}</p>
          {Array.isArray(data.open_ports) && data.open_ports.length > 0 ? (
            <table className="table">
              <thead><tr><th>Port</th><th>State</th><th>Service</th></tr></thead>
              <tbody>
                {(data.open_ports as { port: number; state: string; service: string }[]).map((p, i) => (
                  <tr key={i}><td>{p.port}</td><td className="status-succeeded">{p.state}</td><td>{p.service}</td></tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-muted">No open ports found.</p>}
          <RawBlock raw={data.raw} />
        </div>
      );

    case "headers":
    case "tech-detect":
      return (
        <div>
          <p><strong>{String(data.url)}</strong> &mdash; HTTP {String(data.status_code || "")}</p>
          {Array.isArray(data.technologies) && data.technologies.length > 0 && (
            <div style={{ marginBottom: "0.5rem" }}>
              <strong>Technologies:</strong>{" "}
              {(data.technologies as string[]).map((t: string, i: number) => (
                <span key={i} className="tool-card-tag" style={{ marginRight: "0.3rem" }}>{t}</span>
              ))}
            </div>
          )}
          {data.headers && typeof data.headers === "object" ? (
            <table className="table">
              <thead><tr><th>Header</th><th>Value</th></tr></thead>
              <tbody>
                {Object.entries(data.headers as Record<string, string>).map(([k, v], i) => (
                  <tr key={i}><td>{k}</td><td>{v}</td></tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      );

    case "subnet-calc":
      return (
        <table className="table">
          <tbody>
            <tr><td>CIDR</td><td><strong>{String(data.cidr)}</strong></td></tr>
            <tr><td>Network</td><td>{String(data.network_address)}</td></tr>
            <tr><td>Broadcast</td><td>{String(data.broadcast_address)}</td></tr>
            <tr><td>Netmask</td><td>{String(data.netmask)}</td></tr>
            <tr><td>Host count</td><td>{String(data.host_count)}</td></tr>
            <tr><td>First host</td><td>{String(data.first_host)}</td></tr>
            <tr><td>Last host</td><td>{String(data.last_host)}</td></tr>
            <tr><td>Private</td><td>{data.is_private ? "Yes" : "No"}</td></tr>
          </tbody>
        </table>
      );

    case "subdomain-enum":
      return (
        <div>
          <p><strong>{String(data.domain)}</strong> &mdash; {String((data.subdomains as string[] | undefined)?.length ?? 0)} subdomains found</p>
          {Array.isArray(data.subdomains) && data.subdomains.length > 0
            ? <ul>{(data.subdomains as string[]).map((s, i) => <li key={i}>{s}</li>)}</ul>
            : <p className="text-muted">No subdomains discovered.</p>}
          <RawBlock raw={data.raw} />
        </div>
      );

    case "email-harvest":
      return (
        <div>
          <p><strong>{String(data.domain)}</strong></p>
          {Array.isArray(data.emails) && data.emails.length > 0
            ? <ul>{(data.emails as string[]).map((e, i) => <li key={i}>{e}</li>)}</ul>
            : <p className="text-muted">No emails found (informational only).</p>}
          <RawBlock raw={data.raw} />
        </div>
      );

    case "social-lookup":
      return (
        <div>
          <p><strong>@{String(data.username)}</strong></p>
          {Array.isArray(data.profiles) && data.profiles.length > 0 ? (
            <table className="table">
              <thead><tr><th>Platform</th><th>URL</th><th>Status</th></tr></thead>
              <tbody>
                {(data.profiles as { platform: string; url: string; found: boolean }[]).map((p, i) => (
                  <tr key={i}>
                    <td>{p.platform}</td>
                    <td><a href={p.url} target="_blank" rel="noreferrer">{p.url}</a></td>
                    <td>{p.found ? <span className="status-succeeded">Found</span> : <span className="text-muted">Not found</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-muted">No profiles checked.</p>}
        </div>
      );

    case "wayback":
      return (
        <div>
          <p><strong>{String(data.domain)}</strong> &mdash; {String((data.urls as string[] | undefined)?.length ?? 0)} historical URLs</p>
          {Array.isArray(data.urls) && data.urls.length > 0
            ? <ul>{(data.urls as string[]).slice(0, 100).map((u, i) => (
                <li key={i}><a href={u} target="_blank" rel="noreferrer">{u}</a></li>
              ))}</ul>
            : <p className="text-muted">No archived URLs found.</p>}
        </div>
      );

    default:
      return <RawBlock raw={JSON.stringify(data, null, 2)} />;
  }
}

function RawResult({ data, fields, rawKey }: { data: Record<string, unknown>; fields: string[]; rawKey: string }) {
  return (
    <div>
      {fields.map((f) => <p key={f}><strong>{f}:</strong> {String(data[f])}</p>)}
      <RawBlock raw={data[rawKey]} />
    </div>
  );
}

function RawBlock({ raw }: { raw: unknown }) {
  if (!raw) return null;
  return (
    <details className="raw-details">
      <summary>Raw output</summary>
      <pre className="raw-output">{String(raw)}</pre>
    </details>
  );
}
