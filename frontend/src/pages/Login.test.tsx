import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginPage } from './Login';
import { mockUser } from '../test/fixtures';

vi.mock('../api/auth', () => ({
  sendLoginOtp: vi.fn(),
  getAuthProviders: vi.fn(async () => ({ password_otp: true, microsoft: false })),
  microsoftLoginUrl: vi.fn((redirect?: string | null) =>
    redirect
      ? `http://localhost:8000/api/v1/auth/microsoft/login?redirect=${encodeURIComponent(redirect)}`
      : 'http://localhost:8000/api/v1/auth/microsoft/login',
  ),
}));

vi.mock('../auth/AuthProvider', () => ({
  useAuth: vi.fn(),
}));

import { sendLoginOtp } from '../api/auth';
import { useAuth } from '../auth/AuthProvider';

function renderLogin(initial = '/login') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>home</div>} />
        <Route path="/explore" element={<div>explore</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  const login = vi.fn();

  beforeEach(() => {
    login.mockReset();
    vi.mocked(sendLoginOtp).mockReset();
    vi.mocked(useAuth).mockReturnValue({
      login,
      isLoggedIn: false,
      isAuthLoading: false,
    } as never);
  });

  it('shows loading while auth bootstraps', () => {
    vi.mocked(useAuth).mockReturnValue({
      login,
      isLoggedIn: false,
      isAuthLoading: true,
    } as never);
    renderLogin();
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('redirects when already logged in', () => {
    vi.mocked(useAuth).mockReturnValue({
      login,
      isLoggedIn: true,
      isAuthLoading: false,
    } as never);
    renderLogin();
    expect(screen.getByText('home')).toBeInTheDocument();
  });

  it('validates credentials before requesting OTP', async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole('button', { name: /Continue/i }));
    expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    expect(sendLoginOtp).not.toHaveBeenCalled();
  });

  it('completes OTP login flow', async () => {
    const user = userEvent.setup();
    vi.mocked(sendLoginOtp).mockResolvedValue({
      message: 'sent',
      email: 'a***@example.com',
      resend_after_seconds: 30,
      totp_enabled: false,
      email_otp_sent: true,
    });
    login.mockResolvedValue(mockUser);

    renderLogin();

    await user.type(screen.getByLabelText(/Email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/^Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Continue/i }));

    await screen.findByRole('heading', { name: /Enter code/i });
    expect(screen.getByText(/a\*\*\*@example.com/)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Verification code/i), '123456');
    await user.click(screen.getByRole('button', { name: /^Log in$/i }));

    await screen.findByText(/You're in/i);
    expect(login).toHaveBeenCalledWith(
      'alice@example.com',
      'secret',
      '123456',
      'email',
    );
  });


  it('shows OTP send errors and incomplete code errors', async () => {
    const user = userEvent.setup();
    vi.mocked(sendLoginOtp).mockRejectedValue(new Error('Invalid credentials'));
    renderLogin();
    await user.type(screen.getByLabelText(/Email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/^Password/i), 'bad');
    await user.click(screen.getByRole('button', { name: /Continue/i }));
    await screen.findByText(/Invalid credentials/);

    vi.mocked(sendLoginOtp).mockResolvedValue({
      message: 'sent',
      email: 'a***@example.com',
      resend_after_seconds: 0,
      totp_enabled: false,
      email_otp_sent: true,
    });
    await user.clear(screen.getByLabelText(/^Password/i));
    await user.type(screen.getByLabelText(/^Password/i), 'good');
    await user.click(screen.getByRole('button', { name: /Continue/i }));
    await screen.findByRole('heading', { name: /Enter code/i });
    await user.click(screen.getByRole('button', { name: /^Log in$/i }));
    expect(screen.getByText(/6-digit code/i)).toBeInTheDocument();
  });

  it('supports back, resend, password visibility, and theme toggle', async () => {
    const user = userEvent.setup();
    vi.mocked(sendLoginOtp).mockResolvedValue({
      message: 'sent',
      email: 'a***@example.com',
      resend_after_seconds: 0,
      totp_enabled: false,
      email_otp_sent: true,
    });
    renderLogin();
    await user.type(screen.getByLabelText(/Email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/^Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Show password/i }));
    expect(screen.getByLabelText(/^Password/i)).toHaveAttribute('type', 'text');
    await user.click(screen.getByRole('button', { name: /Continue/i }));
    await screen.findByRole('heading', { name: /Enter code/i });

    await user.click(screen.getByRole('button', { name: /Resend code/i }));
    await waitFor(() => expect(sendLoginOtp).toHaveBeenCalledTimes(2));

    await user.click(screen.getByRole('button', { name: /Back/i }));
    expect(screen.getByRole('heading', { name: /Log in/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Toggle theme/i }));
    expect(document.documentElement.dataset.theme).toMatch(/dark|light/);
  });

  it('surfaces login failure on verify', async () => {
    const user = userEvent.setup();
    vi.mocked(sendLoginOtp).mockResolvedValue({
      message: 'sent',
      email: 'a***@example.com',
      resend_after_seconds: 30,
      totp_enabled: false,
      email_otp_sent: true,
    });
    login.mockRejectedValue(new Error('bad otp'));

    renderLogin('/login?redirect=/explore');
    await user.type(screen.getByLabelText(/Email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/^Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Continue/i }));
    await screen.findByRole('heading', { name: /Enter code/i });
    await user.type(screen.getByLabelText(/Verification code/i), '000000');
    await user.click(screen.getByRole('button', { name: /^Log in$/i }));
    await screen.findByText(/bad otp/);
  });
});
