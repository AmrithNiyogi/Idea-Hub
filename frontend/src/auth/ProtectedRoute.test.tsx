import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ProtectedRoute } from './ProtectedRoute';

vi.mock('./AuthProvider', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from './AuthProvider';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/secure"
          element={
            <ProtectedRoute>
              <div>secret</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>login-page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  it('shows loading while auth resolves', () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoggedIn: false,
      isAuthLoading: true,
    } as never);
    renderAt('/secure');
    expect(screen.getByText(/Checking session/i)).toBeInTheDocument();
  });

  it('redirects anonymous users to login with redirect param', () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoggedIn: false,
      isAuthLoading: false,
    } as never);
    renderAt('/secure');
    expect(screen.getByText('login-page')).toBeInTheDocument();
  });

  it('renders children when logged in', () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoggedIn: true,
      isAuthLoading: false,
    } as never);
    renderAt('/secure');
    expect(screen.getByText('secret')).toBeInTheDocument();
  });
});
