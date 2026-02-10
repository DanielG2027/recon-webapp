import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Project } from "../api";

interface ListResponse {
  projects: Project[];
  total_storage_bytes: number;
  max_projects: number;
  max_artifact_bytes: number;
  eviction_warning: boolean;
}

export default function Projects() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [newName, setNewName] = useState("");

  const load = () => api.get<ListResponse>("/api/projects").then(setData).catch((e) => setErr(e.message));

  useEffect(() => {
    load();
  }, []);

  const create = () => {
    if (!newName.trim()) return;
    api.post<Project>("/api/projects", { name: newName.trim() }).then(() => {
      setNewName("");
      load();
    }).catch((e) => setErr(e.message));
  };

  if (err) return <div className="page-error">Error: {err}</div>;
  if (!data) return <div className="loading">Loading projects…</div>;

  const storageGB = (data.total_storage_bytes / 1024 / 1024 / 1024).toFixed(2);
  const maxGB = (data.max_artifact_bytes / 1024 / 1024 / 1024).toFixed(0);

  return (
    <div className="page">
      <h1>Projects</h1>
      {data.eviction_warning && (
        <p className="warning">Eviction warning: at or over project/storage limits. Oldest project may be evicted.</p>
      )}
      <p className="text-muted">Storage: {storageGB} GB / {maxGB} GB — Projects: {data.projects.length} / {data.max_projects}</p>

      <section className="card">
        <h2>New Project</h2>
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Project name"
          onKeyDown={(e) => e.key === "Enter" && create()}
        />
        <button className="primary" onClick={create}>Create</button>
      </section>

      <section className="card">
        <h2>Projects</h2>
        {data.projects.length === 0 ? (
          <p className="text-muted">No projects. Create one to start recon.</p>
        ) : (
          <ul className="project-list">
            {data.projects.map((p) => (
              <li key={p.id}>
                <Link to={`/results?project=${p.id}`}>{p.name}</Link>
                <span className="text-muted"> — {(p.storage_bytes / 1024).toFixed(1)} KB — {new Date(p.updated_at).toLocaleDateString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
