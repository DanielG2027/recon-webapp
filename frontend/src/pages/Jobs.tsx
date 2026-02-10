import { useEffect, useState } from "react";
import { api, type Job } from "../api";

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = () => api.get<Job[]>("/api/jobs").then(setJobs).catch((e) => setErr(e.message));

  useEffect(() => {
    load();
  }, []);

  const cancel = (id: string) => api.post(`/api/jobs/${id}/cancel`, {}).then(load).catch((e) => setErr(e.message));
  const rerun = (id: string) => api.post<Job>(`/api/jobs/${id}/rerun`, {}).then(() => load()).catch((e) => setErr(e.message));

  if (err) return <div className="page-error">Error: {err}</div>;

  return (
    <div className="page">
      <h1>Jobs / Queue</h1>
      <p className="text-muted">Priority, pause (stop), cancel, rerun. Progress/ETA best-effort.</p>

      <section className="card">
        {jobs.length === 0 ? (
          <p className="text-muted">No jobs. Start from the wizard or a project.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Module</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Priority</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{j.module}</td>
                  <td><span className={`status-${j.status}`}>{j.status}</span></td>
                  <td>{j.progress_pct != null ? `${j.progress_pct}%` : "—"}</td>
                  <td>{j.priority}</td>
                  <td>{new Date(j.created_at).toLocaleString()}</td>
                  <td>
                    {j.status === "running" && <button onClick={() => cancel(j.id)}>Cancel</button>}
                    {(j.status === "succeeded" || j.status === "failed" || j.status === "canceled") && (
                      <button onClick={() => rerun(j.id)}>Rerun</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
