/**
 * Shared fetch helper — re-exports the spine credentials:include client.
 *
 * Phase 2/3 modules import from here; spine pages prefer axios via `./http`.
 */

export { ApiError, apiFetch, API_BASE_URL } from './http';
