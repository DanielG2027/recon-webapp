import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Project, type ScopePreview } from "../api";

type Step = "project" | "targets" | "scope" | "aggressiveness" | "authorization" | "run";

export default function Wizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("project");
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [targets, setTargets] = useState<{ type: string; value: string }[]>([]);
  const [scopePreview, setScopePreview] = useState<ScopePreview | null>(null);
  const [aggressiveness, setAggressiveness] = useState(5);
  const [authorizationConfirmed, setAuthorizationConfirmed] = useState(false);
  const [authState, setAuthState] = useState<{ confirmed: boolean } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const loadProjects = () => api.get<{ projects: Project[] }>("/api/projects").then((r) => setProjects(r.projects));
  const loadAuth = () => api.get<{ confirmed: boolean }>("/api/authorization").then(setAuthState);

  const addTarget = () => setTargets((t) => [...t, { type: "ip", value: "" }]);
  const removeTarget = (i: number) => setTargets((t) => t.filter((_, j) => j !== i));
  const updateTarget = (i: number, field: "type" | "value", v: string) =>
    setTargets((t) => t.map((x, j) => (j === i ? { ...x, [field]: v } : x)));

  const onScopePreview = () => {
    const valid = targets.filter((t) => t.value.trim());
    if (valid.length === 0) {
      setErr("Add at least one target.");
      return;
    }
    api.post<ScopePreview>("/api/scope/preview", { targets: valid }).then((r) => {
      setScopePreview(r);
      setStep("scope");
      setErr(null);
    }).catch((e) => setErr(e.message));
  };

  const runJob = (module: string) => {
    if (!authorizationConfirmed) {
      setErr("Authorization must be confirmed.");
      return;
    }
    api.post("/api/authorization", { confirmed: true }).then(() =>
      api.post("/api/jobs", {
        project_id: selectedProjectId,
        module,
        aggressiveness,
        parameters: { targets },
        authorization_confirmed: true,
      })
    ).then(() => {
      navigate("/jobs");
    }).catch((e) => setErr(e.message));
  };

  useEffect(() => {
    if (step === "project" && projects.length === 0) loadProjects();
  }, [step]);
  useEffect(() => {
    loadAuth();
  }, []);

  if (step === "project") {
    return (
      <div className="page">
        <h1>New Recon Wizard</h1>
        <p className="text-muted">Step 1: Select project</p>
        <div className="card">
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
          >
            <option value="">Select project…</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <button className="primary" onClick={() => selectedProjectId && setStep("targets")} disabled={!selectedProjectId}>
            Next
          </button>
        </div>
      </div>
    );
  }

  if (step === "targets") {
    return (
      <div className="page">
        <h1>New Recon Wizard</h1>
        <p className="text-muted">Step 2: Add targets (IP, FQDN, CIDR, URL)</p>
        <div className="card">
          {targets.map((t, i) => (
            <div key={i} className="row">
              <select value={t.type} onChange={(e) => updateTarget(i, "type", e.target.value)}>
                <option value="ip">IP</option>
                <option value="fqdn">FQDN</option>
                <option value="cidr">CIDR</option>
                <option value="url">URL</option>
              </select>
              <input
                value={t.value}
                onChange={(e) => updateTarget(i, "value", e.target.value)}
                placeholder="Value"
                style={{ flex: 1 }}
              />
              <button onClick={() => removeTarget(i)}>Remove</button>
            </div>
          ))}
          <button onClick={addTarget}>Add target</button>
          <button className="primary" onClick={onScopePreview}>Preview scope →</button>
          {err && <p className="error">{err}</p>}
        </div>
      </div>
    );
  }

  if (step === "scope" && scopePreview) {
    return (
      <div className="page">
        <h1>Scope Preview</h1>
        <div className="card">
          <p>Total hosts: <strong>{scopePreview.total_hosts}</strong></p>
          {scopePreview.cidrs.length > 0 && (
            <ul>
              {scopePreview.cidrs.map((c, i) => (
                <li key={i}>{c.cidr} — {c.host_count} hosts ({c.internal ? "internal" : "external"})</li>
              ))}
            </ul>
          )}
          {scopePreview.large_scope_warning && <p className="warning">Large scope; consider narrowing.</p>}
          {scopePreview.has_external && <p className="warning">External targets may require admin approval.</p>}
          <button onClick={() => setStep("aggressiveness")}>Proceed</button>
        </div>
      </div>
    );
  }

  if (step === "aggressiveness") {
    return (
      <div className="page">
        <h1>Aggressiveness</h1>
        <div className="card">
          <label>Level 1 (stealth) — 10 (aggressive): <strong>{aggressiveness}</strong></label>
          <input
            type="range"
            min={1}
            max={10}
            value={aggressiveness}
            onChange={(e) => setAggressiveness(Number(e.target.value))}
          />
          <button className="primary" onClick={() => setStep("authorization")}>Next</button>
        </div>
      </div>
    );
  }

  if (step === "authorization") {
    if (!authState) loadAuth();
    return (
      <div className="page">
        <h1>Authorization</h1>
        <div className="card">
          <label>
            <input
              type="checkbox"
              checked={authorizationConfirmed}
              onChange={(e) => setAuthorizationConfirmed(e.target.checked)}
            />
            I have authorization to test this target.
          </label>
          {!authorizationConfirmed && (
            <p className="warning">Blocked: Authorization not confirmed. No commands will run.</p>
          )}
          <button className="primary" onClick={() => setStep("run")} disabled={!authorizationConfirmed}>
            Continue to Run
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Run</h1>
      <div className="card">
        <p>Start a module:</p>
        <button onClick={() => runJob("osint")}>OSINT</button>
        <button onClick={() => runJob("active_scan")}>Active Scan</button>
        <button onClick={() => runJob("web")}>Web</button>
        <button onClick={() => runJob("cloud")}>Cloud</button>
        {err && <p className="error">{err}</p>}
      </div>
    </div>
  );
}
