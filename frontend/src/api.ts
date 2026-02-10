const BASE = "";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};

export interface AuthState {
  confirmed: boolean;
  blocked_reason: string | null;
}

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  storage_bytes: number;
  targets: { type: string; value: string }[];
  eviction_order: number;
}

export interface Job {
  id: string;
  project_id: string;
  module: string;
  status: string;
  priority: number;
  progress_pct: number | null;
  eta_seconds: number | null;
  aggressiveness: number;
  noise_score: number | null;
  is_external: boolean;
  admin_approved_at: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  error_message: string | null;
}

export interface DashboardData {
  top_pathway: {
    hypothesis: string;
    score: number;
    evidence: string[];
    finding_ids: string[];
  } | null;
  recent_jobs: { id: string; project_id: string; module: string; status: string; created_at: string }[];
  high_risk_count: number;
  total_findings: number;
}

export interface ScopePreview {
  cidrs: { cidr: string; host_count: number; internal: boolean }[];
  total_hosts: number;
  has_external: boolean;
  large_scope_warning: boolean;
}
