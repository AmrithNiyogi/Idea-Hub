/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  /** @deprecated Prefer VITE_API_BASE_URL; kept for phase 2/3 stubs. */
  readonly VITE_API_BASE?: string;
  /**
   * When `"false"`, hide Sign in with Microsoft even if the API enables it.
   * When unset/`"true"`, login probes GET /api/v1/auth/providers.
   */
  readonly VITE_MICROSOFT_AUTH_ENABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
