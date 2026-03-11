import { getToken, removeToken } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    removeToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Error del servidor");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth — backend uses OAuth2PasswordRequestForm (form data, field "username")
export const authApi = {
  login: async (email: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const token = getToken();
    const res = await fetch(`${BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: form.toString(),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail ?? "Error al iniciar sesión");
    }
    return res.json() as Promise<{ access_token: string }>;
  },
};

// Members (users)
export const membersApi = {
  list: () => request<any[]>("/api/users"),
  get: (id: number) => request<any>(`/api/users/${id}`),
  create: (data: any) =>
    request<any>("/api/users", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: any) =>
    request<any>(`/api/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// Memberships
export const membershipsApi = {
  list: () => request<any[]>("/api/memberships"),
  create: (data: any) =>
    request<any>("/api/memberships", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// Fee rates
export const feeRatesApi = {
  list: () => request<any[]>("/api/fee-rates"),
};

// Events
export const eventsApi = {
  list: () => request<any[]>("/api/events"),
  get: (id: number) => request<any>(`/api/events/${id}`),
  create: (data: any) =>
    request<any>("/api/events", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: number, data: any) =>
    request<any>(`/api/events/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    request<void>(`/api/events/${id}`, { method: "DELETE" }),
};
