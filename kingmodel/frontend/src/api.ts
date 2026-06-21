import type { DashboardData } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: "include", ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(body.detail ?? "请求失败");
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<{ username: string }>("/api/auth/me"),
  login: (username: string, password: string) => request<{ username: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  dashboard: () => request<DashboardData>("/api/dashboard"),
  refresh: () => request<DashboardData>("/api/refresh", { method: "POST" }),
  history: () => request<{ items: unknown[] }>("/api/history")
};
