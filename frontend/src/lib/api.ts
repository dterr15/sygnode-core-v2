const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;
  errors?: Record<string, string[]>;

  constructor(status: number, detail: string, errors?: Record<string, string[]>) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.errors = errors;
  }
}

async function handleResponse(res: Response) {
  if (res.ok) {
    if (res.status === 204) return null;
    return res.json();
  }

  const body = await res.json().catch(() => ({ detail: "Error del servidor" }));

  if (res.status === 401) {
    window.location.href = "/login";
    throw new ApiError(401, "Sesión expirada");
  }

  throw new ApiError(res.status, body.detail || "Error desconocido", body.errors);
}

export const api = {
  async get<T = any>(path: string): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, { credentials: "include" });
    return handleResponse(res);
  },

  async post<T = any>(path: string, body?: any): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: body instanceof FormData ? {} : { "Content-Type": "application/json" },
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    });
    return handleResponse(res);
  },

  async patch<T = any>(path: string, body: any): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return handleResponse(res);
  },

  async delete<T = any>(path: string): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "DELETE",
      credentials: "include",
    });
    return handleResponse(res);
  },
};
