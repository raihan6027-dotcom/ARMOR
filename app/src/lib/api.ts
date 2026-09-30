"use client";

import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "./api/schema";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "armor.token";

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode): the session lasts until reload */
  }
}

const auth: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
};

/** Typed client generated from the backend OpenAPI schema (npm run gen:api). */
export const api = createClient<paths>({ baseUrl: API_URL });
api.use(auth);

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown> | unknown[];
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: ApiErrorBody["details"];

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.code = body.code;
    this.status = status;
    this.details = body.details;
  }
}

/** Unwrap an openapi-fetch result: return data or throw ApiError (OFFLINE on network failure). */
export async function call<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result;
  try {
    result = await promise;
  } catch {
    throw new ApiError(0, { code: "OFFLINE", message: "network" });
  }
  if (result.error !== undefined || !result.response.ok) {
    const body = (result.error as { error?: ApiErrorBody } | undefined)?.error;
    throw new ApiError(result.response.status, body ?? { code: "HTTP_ERROR", message: String(result.response.status) });
  }
  return result.data as T;
}

/** For endpoints whose responses are not typed in the schema. */
export async function raw<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, { code: "OFFLINE", message: "network" });
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, body?.error ?? { code: "HTTP_ERROR", message: String(res.status) });
  }
  return body as T;
}
