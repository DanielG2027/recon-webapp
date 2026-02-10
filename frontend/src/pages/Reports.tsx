import { useEffect, useState } from "react";
import { api, type Project } from "../api";

interface ReportRow {
  id: string;
  project_id: string;
  format: string;
  file_path: string;
  created_at: string;
}

export default function Reports() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ projects: Project[] }>("/api/projects").then((r) => setProjects(r.projects));
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    api.get<ReportRow[]>(`/api/reports/projects/${selectedProjectId}/reports`).then(setReports).catch((e) => setErr(e.message));
  }, [selectedProjectId]);

  const generate = () => {
    if (!selectedProjectId) return;
    api.post(`/api/reports/projects/${selectedProjectId}/generate`, { formats: ["md", "pdf"] })
      .then(() => setErr(null))
      .catch((e) => setErr(e.message));
  };

  if (err) return <div className="page-error">Error: {err}</div>;

  return (
    <div className="page">
      <h1>Reports</h1>
      <p className="text-muted">One-click Markdown + PDF. Includes Kill Chain mapping and CVSS (verify manually).</p>

      <section className="card">
        <label>Project: </label>
        <select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
          <option value="">Select project…</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <button className="primary" onClick={generate} disabled={!selectedProjectId}>
          Generate report (MD + PDF)
        </button>
      </section>

      {selectedProjectId && (
        <section className="card">
          <h2>Report history</h2>
          {reports.length === 0 ? (
            <p className="text-muted">No reports generated yet.</p>
          ) : (
            <ul>
              {reports.map((r) => (
                <li key={r.id}>
                  {r.format} — {new Date(r.created_at).toLocaleString()}
                  <a href={`/api/reports/${r.id}/download`} target="_blank" rel="noreferrer"> Download</a>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
