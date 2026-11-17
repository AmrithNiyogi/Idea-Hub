import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthProvider';
import { mockUser } from '../test/fixtures';

vi.mock('../api/auth', () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  switchRole: vi.fn(),
}));

import * as authApi from '../api/auth';

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="loading">{String(auth.isAuthLoading)}</div>
      <div data-testid="logged">{String(auth.isLoggedIn)}</div>
      <div data-testid="name">{auth.user?.name ?? 'none'}</div>
      <button
        type="button"
        onClick={() => void auth.login('a@x.com', 'pw', '123456')}
      >
        login
      </button>
      <button
        type="button"
        onClick={() => {
          void auth.logout().catch(() => undefined);
        }}
      >
        logout
      </button>
      <button type="button" onClick={() => void auth.switchRole('reviewer')}>
        switch
      </button>
      <button type="button" onClick={() => void auth.refetchUser()}>
        refetch
      </button>
    </div>
  );
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.mocked(authApi.getCurrentUser).mockReset();
    vi.mocked(authApi.login).mockReset();
    vi.mocked(authApi.logout).mockReset();
    vi.mocked(authApi.switchRole).mockReset();
  });

  it('loads session user on mount', async () => {
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('logged')).toHaveTextContent('true');
    expect(screen.getByTestId('name')).toHaveTextContent('Alice Example');
  });

  it('clears user when session probe fails', async () => {
    vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('nope'));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('logged')).toHaveTextContent('false');
  });

  it('login / logout / switchRole / refetchUser', async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('nope'));
    vi.mocked(authApi.login).mockResolvedValue({
      message: 'ok',
      user: mockUser,
    });
    vi.mocked(authApi.logout).mockResolvedValue(undefined);
    vi.mocked(authApi.switchRole).mockResolvedValue({
      role: 'reviewer',
      user: { ...mockUser, active_role: 'reviewer', name: 'Alice Reviewer' },
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

    await user.click(screen.getByRole('button', { name: 'login' }));
    await waitFor(() =>
      expect(screen.getByTestId('name')).toHaveTextContent('Alice Example'),
    );

    await user.click(screen.getByRole('button', { name: 'switch' }));
    await waitFor(() =>
      expect(screen.getByTestId('name')).toHaveTextContent('Alice Reviewer'),
    );

    vi.mocked(authApi.getCurrentUser).mockResolvedValue({
      ...mockUser,
      name: 'Refetched',
    });
    await user.click(screen.getByRole('button', { name: 'refetch' }));
    await waitFor(() =>
      expect(screen.getByTestId('name')).toHaveTextContent('Refetched'),
    );

    vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('gone'));
    await user.click(screen.getByRole('button', { name: 'refetch' }));
    await waitFor(() => expect(screen.getByTestId('name')).toHaveTextContent('none'));

    vi.mocked(authApi.login).mockResolvedValue({
      message: 'ok',
      user: mockUser,
    });
    await user.click(screen.getByRole('button', { name: 'login' }));
    await waitFor(() =>
      expect(screen.getByTestId('name')).toHaveTextContent('Alice Example'),
    );

    await user.click(screen.getByRole('button', { name: 'logout' }));
    await waitFor(() => expect(screen.getByTestId('name')).toHaveTextContent('none'));
  });

  it('logout still clears user when API fails', async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);
    vi.mocked(authApi.logout).mockRejectedValue(new Error('network'));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('logged')).toHaveTextContent('true'));
    await user.click(screen.getByRole('button', { name: 'logout' }));
    await waitFor(() => expect(screen.getByTestId('logged')).toHaveTextContent('false'));
  });

  it('useAuth throws outside provider', () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    let thrown: unknown;
    try {
      render(<Probe />);
    } catch (e) {
      thrown = e;
    }
    expect(String(thrown)).toMatch(/AuthProvider/);
    err.mockRestore();
  });
});
