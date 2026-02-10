import { useEffect, useState } from "react";
import { api } from "../api";

interface SettingsData {
  concurrency: number;
  max_concurrency: number;
  container_cpu: string;
  container_memory_gb: number;
  default_aggressiveness: number;
  raw_retention_days: number;
  log_retention_days: number;
}

export default function Settings() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<SettingsData>("/api/settings").then(setData).catch((e) => setErr(e.message));
  }, []);

  const update = (updates: Partial<SettingsData>) => {
    if (!data) return;
    api.patch<SettingsData>("/api/settings", { ...data, ...updates }).then(setData).catch((e) => setErr(e.message));
  };

  if (err) return <div className="page-error">Error: {err}</div>;
  if (!data) return <div className="loading">Loading settings…</div>;

  return (
    <div className="page">
      <h1>Settings</h1>
      <section className="card">
        <h2>Concurrency</h2>
        <label>Simultaneous jobs (default 2):</label>
        <input
          type="number"
          min={1}
          max={data.max_concurrency}
          value={data.concurrency}
          onChange={(e) => update({ concurrency: Number(e.target.value) })}
        />
      </section>
      <section className="card">
        <h2>Container limits</h2>
        <label>CPU (cores):</label>
        <input
          value={data.container_cpu}
          onChange={(e) => update({ container_cpu: e.target.value })}
        />
        <label>Memory (GB):</label>
        <input
          type="number"
          min={1}
          max={8}
          value={data.container_memory_gb}
          onChange={(e) => update({ container_memory_gb: Number(e.target.value) })}
        />
      </section>
      <section className="card">
        <h2>Defaults</h2>
        <label>Default aggressiveness (1–10):</label>
        <input
          type="number"
          min={1}
          max={10}
          value={data.default_aggressiveness}
          onChange={(e) => update({ default_aggressiveness: Number(e.target.value) })}
        />
      </section>
      <section className="card">
        <h2>Retention</h2>
        <p>Raw outputs: {data.raw_retention_days} days</p>
        <p>Logs: {data.log_retention_days} days</p>
      </section>
    </div>
  );
}
