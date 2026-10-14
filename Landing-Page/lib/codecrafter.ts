"use client";

/**
 * CodeCrafter backend API client and shared frontend types.
 * All LLM traffic stays behind the backend; the browser only talks to this API.
 */

const rawApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const API_BASE_URL = rawApiUrl.replace(/\/$/, "");

export function wsUrlFor(path: string): string {
  return `${API_BASE_URL.replace(/^http/, "ws")}${path}`;
}

/** Optional shared bearer token (set in Settings; stored locally). */
export function getApiToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("codecrafter_token") ?? "";
}

export function headers(): HeadersInit {
  const token = getApiToken();
  return token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...Object.fromEntries(new Headers(init?.headers ?? {})), ...Object.fromEntries(new Headers(headers())) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string | null;
  workspace_path: string;
  git_url: string | null;
  created_at: string;
  updated_at: string;
  default_session_id?: string;
}

export interface Session {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Run {
  id: string;
  session_id: string;
  project_id: string;
  prompt: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export type AgentEventType =
  | "agent.started"
  | "agent.thinking"
  | "agent.message"
  | "tool.started"
  | "tool.completed"
  | "tool.failed"
  | "file.created"
  | "file.modified"
  | "file.deleted"
  | "execution.output"
  | "agent.completed"
  | "agent.failed"
  | "agent.cancelled";

export interface AgentEvent {
  type: AgentEventType;
  run_id: string;
  sequence: number;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface FileMeta {
  path: string;
  size_bytes: number;
  size_kb: number;
  modified: string;
}

// ── API surface ──────────────────────────────────────────────────────────────

export const api = {
  listProjects: () => request<Project[]>("/api/projects"),
  createProject: (name: string, description = "") =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify({ name, description }) }),
  importGit: (name: string, gitUrl: string, description = "") =>
    request<Project>("/api/projects/import-git", {
      method: "POST",
      body: JSON.stringify({ name, git_url: gitUrl, description }),
    }),
  deleteProject: (id: string) =>
    request<{ deleted: boolean; project_id: string }>(`/api/projects/${id}`, { method: "DELETE" }),
  getProject: (id: string) => request<Project>(`/api/projects/${id}`),

  listFiles: (projectId: string) =>
    request<{ files: FileMeta[]; tree: string }>(`/api/projects/${projectId}/files`),
  readFile: (projectId: string, path: string) =>
    request<{ path: string; content: string }>(
      `/api/projects/${projectId}/files/content?path=${encodeURIComponent(path)}`
    ),
  writeFile: (projectId: string, path: string, content: string) =>
    request<{ success: boolean; message: string; path: string }>(
      `/api/projects/${projectId}/files/content`,
      { method: "PUT", body: JSON.stringify({ path, content }) }
    ),

  listSessions: (projectId: string) => request<Session[]>(`/api/projects/${projectId}/sessions`),
  createSession: (projectId: string, title = "New Session") =>
    request<Session>("/api/sessions", { method: "POST", body: JSON.stringify({ project_id: projectId, title }) }),
  getMessages: (sessionId: string) =>
    request<{ session: Session; messages: ChatMessage[] }>(`/api/sessions/${sessionId}`),

  startRun: (projectId: string, sessionId: string, prompt: string) =>
    request<{ run_id: string; status: string }>("/api/agent/runs", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, session_id: sessionId, prompt }),
    }),
  getRun: (runId: string) => request<Run>(`/api/agent/runs/${runId}`),
  cancelRun: (runId: string) =>
    request<{ cancelled: boolean; run_id: string }>(`/api/agent/runs/${runId}/cancel`, { method: "POST" }),
};
