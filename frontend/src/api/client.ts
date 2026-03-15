/** Базовый путь к API (прокси в dev на backend). API base path; Vite proxies to backend in dev. */
const API_BASE = "/api/v1";

type RequestOptions = RequestInit & { params?: Record<string, string> };

/** fetch с credentials: include (куки), JSON, разбор ошибок. */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...init } = options;
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.pathname + url.search, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string>),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string, params?: Record<string, string>) =>
    request<T>(API_BASE + path, { method: "GET", params }),
  post: <T>(path: string, body?: object) =>
    request<T>(API_BASE + path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: object) =>
    request<T>(API_BASE + path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(API_BASE + path, { method: "DELETE" }),
};

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  role: string;
}

export interface Task {
  id: number;
  owner_id: number;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "done" | "cancelled";
  priority: "low" | "medium" | "high" | "urgent";
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
