import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type Project } from "../api";

interface Finding {
  id: string;
  project_id: string;
  module: string;
  finding_type: string;
  title: string;
  data: Record<string, unknown>;
  risk_score: number | null;
  first_seen_at: string;
  last_seen_at: string;
  is_internal: boolean;
}

export default function Results() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project");
  const [projects, setProjects] = useState<Project[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ projects: Project[] }>("/api/projects").then((r) => setProjects(r.projects));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    api.get<Finding[]>(`/api/results/projects/${projectId}/findings`).then(setFindings).catch((e) => setErr(e.message));
  }, [projectId]);

  if (err) return <div className="page-error">Error: {err}</div>;

  return (
    <div className="page">
      <h1>Results</h1>
      <p className="text-muted">Correlated asset view. Filters and raw output (until 7-day expiry).</p>

      <section className="card">
        <label>Project: </label>
        <select
          value={projectId || ""}
          onChange={(e) => {
            const v = e.target.value;
            if (v) window.location.search = `?project=${v}`;
          }}
        >
          <option value="">Select project…</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </section>

      {projectId && (
        <section className="card">
          <h2>Findings</h2>
          {findings.length === 0 ? (
            <p className="text-muted">No findings for this project yet.</p>
          ) : (
            <ul className="findings-list">
              {findings.map((f) => (
                <li key={f.id}>
                  <strong>{f.title}</strong> — {f.module} / {f.finding_type}
                  {f.risk_score != null && <span className="risk"> risk {f.risk_score}</span>}
                  <span className="text-muted"> {f.is_internal ? "internal" : "external"}</span>
                  <br />
                  <small>{new Date(f.last_seen_at).toLocaleString()}</small>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
