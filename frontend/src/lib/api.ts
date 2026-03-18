import { getToken, removeToken } from "./auth";
import type {
  Event,
  FeeRate,
  Membership,
  MembershipStatus,
  Payment,
  PaymentStatus,
  RoleAssignment,
  User,
  UserSummary,
} from "./types";

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

// Events (public)
export const eventsApi = {
  list: () => request<Event[]>("/api/events"),
  get: (id: string) => request<Event>(`/api/events/${id}`),
};

// === Admin API ===

export const adminApi = {
  // Memberships
  memberships: {
    list: (status?: MembershipStatus) =>
      request<Membership[]>(
        `/api/admin/memberships?limit=500${status ? `&status=${status}` : ""}`
      ),
    pendingCount: () =>
      request<{ count: number }>("/api/admin/memberships/pending/count"),
    review: (id: string, action: "approve" | "reject", notes?: string) =>
      request<{ id: string; status: string; message: string }>(
        `/api/admin/memberships/${id}/review`,
        { method: "POST", body: JSON.stringify({ action, notes }) }
      ),
    updateStatus: (id: string, status: MembershipStatus, notes?: string) =>
      request<{ id: string; old_status: string; new_status: string }>(
        `/api/admin/memberships/${id}/status`,
        { method: "PATCH", body: JSON.stringify({ status, notes }) }
      ),
    assign: (data: { user_id: string; membership_type_code: string }) =>
      request<Membership>("/api/admin/memberships/assign", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Payments
  payments: {
    list: (status?: PaymentStatus) =>
      request<Payment[]>(
        `/api/admin/payments${status ? `?status=${status}` : ""}`
      ),
    create: (data: {
      membership_id: string;
      fee_rate_id: string;
      payment_method: string;
      amount_clp: number;
      payment_date: string;
      period_month?: number;
      period_year?: number;
      notes?: string;
    }) =>
      request<Payment>("/api/admin/payments", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    confirm: (id: string, action: "confirm" | "reject", notes?: string) =>
      request<{ id: string; status: string; message: string }>(
        `/api/admin/payments/${id}/confirm`,
        { method: "POST", body: JSON.stringify({ action, notes }) }
      ),
  },

  // Events
  events: {
    list: (includeUnpublished = true) =>
      request<Event[]>(
        `/api/admin/events?include_unpublished=${includeUnpublished}`
      ),
    get: (id: string) => request<Event>(`/api/admin/events/${id}`),
    create: (data: {
      title: string;
      description?: string;
      event_date: string;
      location?: string;
      address?: string;
      image_url?: string;
      is_published?: boolean;
    }) =>
      request<Event>("/api/admin/events", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Event>) =>
      request<Event>(`/api/admin/events/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/api/admin/events/${id}`, { method: "DELETE" }),
  },

  // Fee rates
  feeRates: {
    list: () => request<FeeRate[]>("/api/fee-rates"),
    create: (data: {
      fee_type: string;
      membership_type_id: string;
      amount_utm: number;
      utm_to_clp_rate?: number;
      amount_clp?: number;
      effective_from: string;
      effective_until?: string;
      reason?: string;
    }) =>
      request<FeeRate>("/api/admin/fee-rates", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Users
  users: {
    list: (activeOnly = false) =>
      request<User[]>(`/api/admin/users?active_only=${activeOnly}`),
    get: (id: string) => request<User>(`/api/admin/users/${id}`),
    updateStatus: (id: string, is_active: boolean) =>
      request<{ id: string; is_active: boolean; message: string }>(
        `/api/admin/users/${id}/status?is_active=${is_active}`,
        { method: "PATCH" }
      ),
    resetPassword: (userId: string, newPassword: string) =>
      request<{ user_id: string; message: string }>(
        `/api/admin/users/${userId}/password`,
        { method: "PATCH", body: JSON.stringify({ new_password: newPassword }) }
      ),
    withoutMembership: () =>
      request<UserSummary[]>("/api/admin/users/without-membership"),
    getRoles: (userId: string) =>
      request<RoleAssignment[]>(`/api/admin/users/${userId}/roles`),
    updateRole: (
      userId: string,
      role_name: string,
      action: "assign" | "revoke"
    ) =>
      request<{ user_id: string; role_name: string; action: string; message: string }>(
        `/api/admin/users/${userId}/roles`,
        { method: "POST", body: JSON.stringify({ role_name, action }) }
      ),
  },

  // Members (create user + membership in one step)
  members: {
    create: (data: {
      email: string;
      password: string;
      first_name: string;
      last_name_1: string;
      rut: string;
      middle_name?: string;
      last_name_2?: string;
      phone?: string;
      membership_type_code: string;
    }) =>
      request<Membership>("/api/admin/members", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
};
