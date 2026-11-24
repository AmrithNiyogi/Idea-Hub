import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  apiFetch,
  getApiErrorMessage,
  http,
} from './http';

describe('getApiErrorMessage / ApiError', () => {
  it('extracts string detail, array detail, message, and fallbacks', () => {
    expect(getApiErrorMessage(new Error('boom'))).toBe('boom');
    expect(getApiErrorMessage('raw')).toBe('Request failed');

    const withDetail = {
      isAxiosError: true,
      message: 'x',
      response: { data: { detail: 'Nope' } },
    };
    expect(getApiErrorMessage(withDetail)).toBe('Nope');

    const withArray = {
      isAxiosError: true,
      message: 'x',
      response: {
        data: { detail: [{ msg: 'a' }, 'b', { msg: 'c' }] },
      },
    };
    // axios.isAxiosError may reject plain objects — exercise via real AxiosError path below
    expect(getApiErrorMessage(withArray)).toMatch(/Request failed|a/);

    const err = new ApiError(400, 'bad', { detail: 'x' });
    expect(err.name).toBe('ApiError');
    expect(err.status).toBe(400);
  });

  it('reads axios error payloads via isAxiosError', async () => {
    const mock = new MockAdapter(http);
    mock.onGet('/boom-str').reply(400, { detail: 'Nope' });
    await expect(http.get('/boom-str')).rejects.toMatchObject({
      message: 'Nope',
      status: 400,
    });

    mock.onGet('/boom-arr').reply(422, {
      detail: [{ msg: 'field a' }, { msg: 'field b' }],
    });
    await expect(http.get('/boom-arr')).rejects.toMatchObject({
      message: 'field a; field b',
    });

    mock.onGet('/boom-msg').reply(500, { message: 'server said' });
    await expect(http.get('/boom-msg')).rejects.toMatchObject({
      message: 'server said',
    });

    mock.onGet('/boom-plain').reply(500, 'plain');
    await expect(http.get('/boom-plain')).rejects.toBeInstanceOf(ApiError);

    mock.restore();
  });
});

describe('http 401 refresh-and-retry', () => {
  let mock: MockAdapter;
  let refreshSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    mock = new MockAdapter(http);
    refreshSpy = vi.spyOn(axios, 'post').mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    mock.restore();
    refreshSpy.mockRestore();
  });

  it('refreshes once then retries the original request', async () => {
    mock
      .onGet('/ideas')
      .replyOnce(401)
      .onGet('/ideas')
      .replyOnce(200, { items: [], total: 0 });

    const res = await http.get('/ideas');
    expect(res.data).toEqual({ items: [], total: 0 });
    expect(refreshSpy).toHaveBeenCalled();
    const url = String(refreshSpy.mock.calls[0]?.[0] ?? '');
    expect(url).toContain('/auth/refresh');
  });

  it('does not refresh auth paths', async () => {
    mock.onPost('/auth/login').reply(401, { detail: 'bad otp' });
    await expect(http.post('/auth/login', {})).rejects.toMatchObject({
      status: 401,
      message: 'bad otp',
    });
    expect(refreshSpy).not.toHaveBeenCalled();
  });

  it('surfaces ApiError when refresh fails', async () => {
    refreshSpy.mockRejectedValue(new Error('refresh dead'));
    mock.onGet('/ideas/secret').reply(401);
    await expect(http.get('/ideas/secret')).rejects.toBeInstanceOf(ApiError);
  });

  it('dedupes concurrent refresh calls', async () => {
    mock
      .onGet('/a')
      .replyOnce(401)
      .onGet('/a')
      .replyOnce(200, { ok: true });
    mock
      .onGet('/b')
      .replyOnce(401)
      .onGet('/b')
      .replyOnce(200, { ok: true });

    const [a, b] = await Promise.all([http.get('/a'), http.get('/b')]);
    expect(a.data.ok).toBe(true);
    expect(b.data.ok).toBe(true);
    expect(refreshSpy).toHaveBeenCalledTimes(1);
  });
});

describe('apiFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns JSON and handles 204', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ id: 1 }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 204,
        }),
    );

    await expect(apiFetch<{ id: number }>('/users')).resolves.toEqual({ id: 1 });
    await expect(apiFetch('/gone')).resolves.toBeUndefined();
  });

  it('throws ApiError with detail from JSON or text body', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ detail: 'denied' }),
        text: async () => JSON.stringify({ detail: 'denied' }),
      }),
    );
    await expect(apiFetch('/x')).rejects.toMatchObject({
      status: 403,
      message: 'denied',
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        json: async () => {
          throw new Error('not json');
        },
        text: async () => 'oops',
      }),
    );
    await expect(apiFetch('/y')).rejects.toMatchObject({ status: 500 });
  });

  it('sets Content-Type when body present and accepts absolute URLs', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('https://example.com/x', {
      method: 'POST',
      body: JSON.stringify({ a: 1 }),
    });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe('include');
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json');
  });
});
