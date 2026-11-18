import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { newsApi } from './news';

describe('news API', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const lastCall = () => {
    const [url, init] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
    return { url, method: init.method ?? 'GET' };
  };

  it('lists categories', async () => {
    await newsApi.categories();
    expect(lastCall()).toEqual({ url: '/api/v1/news/categories', method: 'GET' });
  });

  it('fetches insights', async () => {
    await newsApi.insights();
    expect(lastCall()).toEqual({ url: '/api/v1/news/insights', method: 'GET' });
  });

  it('fetches a category feed', async () => {
    await newsApi.feed('ai-sports');
    expect(lastCall()).toEqual({
      url: '/api/v1/news?category=ai-sports',
      method: 'GET',
    });
  });

  it('refreshes, forcing only when asked', async () => {
    await newsApi.refresh('ai');
    expect(lastCall()).toEqual({ url: '/api/v1/news/ai/refresh', method: 'POST' });
    await newsApi.refresh('ai', true);
    expect(lastCall()).toEqual({
      url: '/api/v1/news/ai/refresh?force=true',
      method: 'POST',
    });
  });
});
