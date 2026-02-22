const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/* ---------- types ---------- */

export interface AuthResponse {
  success: boolean;
  token: string;
  user_id: string;
  reason: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
}

export interface TaskItem {
  id: string;
  title: string;
  done: boolean;
  created_at: string | null;
}

export interface TaskCreateResponse {
  task_id: string;
  title: string;
}

export interface TaskUpdateResponse {
  task_id: string;
  title: string;
  done: boolean;
}

/* ---------- helpers ---------- */

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Request failed");
  }

  return res.json() as Promise<T>;
}

/* ---------- auth ---------- */

export function register(
  email: string,
  password: string,
  name: string,
): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export function login(
  email: string,
  password: string,
): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(): Promise<UserProfile> {
  return request<UserProfile>("/api/auth/me");
}

/* ---------- tasks ---------- */

export function getTasks(): Promise<TaskItem[]> {
  return request<TaskItem[]>("/api/tasks");
}

export function createTask(title: string): Promise<TaskCreateResponse> {
  return request<TaskCreateResponse>("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function updateTask(
  id: string,
  updates: { title?: string; done?: boolean },
): Promise<TaskUpdateResponse> {
  return request<TaskUpdateResponse>(`/api/tasks/${id}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export function deleteTask(id: string): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/api/tasks/${id}`, {
    method: "DELETE",
  });
}
