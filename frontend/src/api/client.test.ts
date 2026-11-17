import { describe, expect, it } from 'vitest';
import { API_BASE_URL, ApiError, apiFetch } from './client';

describe('client re-exports', () => {
  it('exposes shared http helpers', () => {
    expect(API_BASE_URL).toContain('/api/v1');
    expect(typeof apiFetch).toBe('function');
    expect(new ApiError(1, 'x').status).toBe(1);
  });
});
