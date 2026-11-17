/**
 * Axios client for Idea Hub spine APIs.
 *
 * Uses credentials:include (withCredentials) so httpOnly JWT cookies are sent.
 * On 401, attempts a single refresh then retries the original request.
 */

import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios';

/**
 * API origin from env. Empty / unset → same-origin `/api/v1` so Vite can
 * proxy to uvicorn (required when the UI is served over HTTPS ngrok while
 * the API stays on http://localhost:8000 — browsers block mixed-content XHR).
 */
const _rawApiOrigin = import.meta.env.VITE_API_BASE_URL;
const API_ORIGIN =
  typeof _rawApiOrigin === 'string' ? _rawApiOrigin.replace(/\/$/, '') : '';

export const API_BASE_URL = API_ORIGIN ? `${API_ORIGIN}/api/v1` : '/api/v1';

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<void> | null = null;

async function refreshSession(): Promise<void> {
  await axios.post(
    `${API_BASE_URL}/auth/refresh`,
    {},
    { withCredentials: true },
  );
}

function getErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'Request failed';
  }
  const data = error.response?.data as
    | { detail?: unknown; message?: string }
    | undefined;
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        typeof d === 'object' && d && 'msg' in d
          ? String((d as { msg: string }).msg)
          : String(d),
      )
      .join('; ');
  }
  if (typeof data?.message === 'string') return data.message;
  return error.message || 'Request failed';
}

export function getApiErrorMessage(error: unknown): string {
  return getErrorMessage(error);
}

export const http: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    // Ngrok free interstitial otherwise breaks JSON probes like /auth/providers.
    'ngrok-skip-browser-warning': 'true',
  },
});

http.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const status = error.response?.status;
    const url = config?.url ?? '';

    const isAuthPath =
      url.includes('/auth/login') ||
      url.includes('/auth/send-login-otp') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/logout');

    if (status === 401 && config && !config._retry && !isAuthPath) {
      config._retry = true;
      try {
        if (!refreshPromise) {
          refreshPromise = refreshSession().finally(() => {
            refreshPromise = null;
          });
        }
        await refreshPromise;
        return http(config);
      } catch {
        // fall through
      }
    }

    throw new ApiError(
      status ?? 0,
      getErrorMessage(error),
      error.response?.data,
    );
  },
);

/**
 * Fetch helper for modules that prefer fetch over axios.
 * Same origin + credentials contract as {@link http}.
 */
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('ngrok-skip-browser-warning')) {
    headers.set('ngrok-skip-browser-warning', 'true');
  }

  const res = await fetch(
    path.startsWith('http') ? path : `${API_BASE_URL}${path}`,
    {
      ...init,
      credentials: 'include',
      headers,
    },
  );

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    let msg = res.statusText;
    if (typeof body === 'object' && body && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === 'string') {
        msg = detail;
      } else if (
        detail &&
        typeof detail === 'object' &&
        'message' in detail &&
        typeof (detail as { message: unknown }).message === 'string'
      ) {
        msg = (detail as { message: string }).message;
      } else {
        msg = String(detail);
      }
    }
    throw new ApiError(res.status, msg, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
