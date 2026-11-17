import { FormEvent, useEffect, useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { getAuthProviders, microsoftLoginUrl, sendLoginOtp } from '../api/auth';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import type { OtpMethod } from '../types/auth';

const OTP_LENGTH = 6;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Step = 'credentials' | 'verify' | 'success';

function formatCountdown(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

function FieldError({ message }: { message: string }) {
  return (
    <p role="alert" className="error" style={{ marginTop: 6 }}>
      <Icon name="alert" size={14} /> {message}
    </p>
  );
}

function MicrosoftMark({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 21 21"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  );
}

function envMicrosoftForcedOff(): boolean {
  const flag = import.meta.env.VITE_MICROSOFT_AUTH_ENABLED;
  return typeof flag === 'string' && flag.toLowerCase() === 'false';
}

export function LoginPage() {
  const { login, isLoggedIn, isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<Step>('credentials');
  const [showPassword, setShowPassword] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [otpError, setOtpError] = useState('');
  const [ssoError, setSsoError] = useState('');
  const [microsoftEnabled, setMicrosoftEnabled] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [codeSentFor, setCodeSentFor] = useState('');
  const [maskedEmail, setMaskedEmail] = useState('');
  const [totpEnabled, setTotpEnabled] = useState(false);
  const [otpMethod, setOtpMethod] = useState<OtpMethod>('email');
  const [emailOtpSent, setEmailOtpSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      return (localStorage.getItem('ih.theme') as 'light' | 'dark') || 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    const err = params.get('error');
    if (err) setSsoError(err);
  }, [params]);

  useEffect(() => {
    if (envMicrosoftForcedOff()) {
      setMicrosoftEnabled(false);
      return;
    }
    let cancelled = false;
    (async () => {
      const providers = await getAuthProviders();
      if (!cancelled) setMicrosoftEnabled(!!providers.microsoft);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  useEffect(() => {
    if (!isAuthLoading && isLoggedIn && step !== 'success') {
      const redirect = params.get('redirect');
      const safe = redirect && /^\/(?!\/|\\)/.test(redirect) ? redirect : '/';
      navigate(safe, { replace: true });
    }
  }, [isLoggedIn, isAuthLoading, navigate, params, step]);

  const startMicrosoftSignIn = () => {
    const redirect = params.get('redirect');
    window.location.assign(microsoftLoginUrl(redirect));
  };

  if (isAuthLoading) {
    return (
      <div className="empty" style={{ minHeight: '100vh' }}>
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (isLoggedIn && step !== 'success') {
    return <Navigate to="/" replace />;
  }

  const prepareLogin = async (issueEmailOtp: boolean) => {
    const res = await sendLoginOtp({
      email: email.trim(),
      password,
      issue_email_otp: issueEmailOtp,
    });
    setCodeSentFor(`${email.trim()}\n${password}`);
    setMaskedEmail(res.email);
    setTotpEnabled(!!res.totp_enabled);
    setEmailOtpSent(!!res.email_otp_sent);
    if (res.email_otp_sent) {
      setResendCooldown(res.resend_after_seconds);
    }
    if (res.totp_enabled && !issueEmailOtp) {
      setOtpMethod('totp');
    } else if (!res.totp_enabled) {
      setOtpMethod('email');
    }
    return res;
  };

  const handleCredentials = async (e: FormEvent) => {
    e.preventDefault();
    const emailMessage = EMAIL_PATTERN.test(email.trim())
      ? ''
      : 'Enter a valid email address.';
    const passwordMessage = password.trim() ? '' : 'Enter your password.';
    setEmailError(emailMessage);
    setPasswordError(passwordMessage);
    if (emailMessage || passwordMessage) return;

    setOtp('');
    setOtpError('');

    if (resendCooldown > 0 && codeSentFor === `${email.trim()}\n${password}`) {
      setStep('verify');
      return;
    }

    setBusy(true);
    try {
      // Probe without emailing first; if MFA is off the API still sends email OTP.
      const res = await prepareLogin(false);
      if (res.totp_enabled && !res.email_otp_sent) {
        setOtpMethod('totp');
      }
      setStep('verify');
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Could not send code');
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    if (otp.length < OTP_LENGTH) {
      setOtpError(`Enter the ${OTP_LENGTH}-digit code.`);
      return;
    }
    setOtpError('');
    setBusy(true);
    try {
      await login(email.trim(), password, otp, otpMethod);
      setStep('success');
      const redirect = params.get('redirect');
      const safe = redirect && /^\/(?!\/|\\)/.test(redirect) ? redirect : '/';
      setTimeout(() => navigate(safe, { replace: true }), 600);
    } catch (err) {
      setOtpError(err instanceof Error ? err.message : 'Login failed');
      setOtp('');
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    setOtpError('');
    setBusy(true);
    try {
      await prepareLogin(true);
      setOtpMethod('email');
      setOtp('');
    } catch (err) {
      setOtpError(err instanceof Error ? err.message : 'Could not resend');
    } finally {
      setBusy(false);
    }
  };

  const selectOtpMethod = async (method: OtpMethod) => {
    setOtpMethod(method);
    setOtp('');
    setOtpError('');
    if (method === 'email' && !emailOtpSent) {
      setBusy(true);
      try {
        await prepareLogin(true);
      } catch (err) {
        setOtpError(err instanceof Error ? err.message : 'Could not send code');
      } finally {
        setBusy(false);
      }
    }
  };

  return (
    <div
      className="signin"
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: 24,
        background: 'var(--bg)',
        position: 'relative',
      }}
    >
      <button
        type="button"
        className="btn btn--ghost btn--icon"
        style={{ position: 'absolute', top: 24, right: 24 }}
        aria-label="Toggle theme"
        onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
      >
        <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={20} />
      </button>

      <div
        className="card"
        style={{
          width: 'min(440px, 100%)',
          padding: '40px 36px',
          boxShadow: 'var(--shadow-2)',
        }}
      >
        <div
          className="signin__brand"
          style={{ justifyContent: 'center', marginBottom: 28 }}
        >
          <span className="brand__glyph" aria-hidden="true">
            <Icon name="logo" size={18} />
          </span>
          <span className="brand__text">
            <span className="brand__name">IdeaKonnekt</span>
            <span className="brand__sub">Idea Hub</span>
          </span>
        </div>

        <div
          className="row"
          style={{ justifyContent: 'center', gap: 8, marginBottom: 24 }}
        >
          {(['credentials', 'verify'] as const).map((s, i) => {
            const done =
              step === 'success' ||
              (step === 'verify' && s === 'credentials') ||
              step === s;
            const active = step === s;
            return (
              <span key={s} className="row" style={{ gap: 8 }}>
                {i > 0 ? (
                  <span
                    style={{
                      width: 24,
                      height: 2,
                      background: 'var(--border)',
                      borderRadius: 99,
                    }}
                  />
                ) : null}
                <span
                  className="mono small"
                  style={{
                    color: active ? 'var(--brand-ink)' : 'var(--text-3)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  <span
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: '50%',
                      display: 'grid',
                      placeItems: 'center',
                      background: active
                        ? 'var(--brand)'
                        : done && step !== s
                          ? 'var(--success)'
                          : 'var(--surface-3)',
                      color: active || (done && step !== s) ? '#fff' : 'inherit',
                      fontSize: 11,
                    }}
                  >
                    {i + 1}
                  </span>
                  {s === 'credentials' ? 'Credentials' : 'Verify'}
                </span>
              </span>
            );
          })}
        </div>

        {step === 'credentials' && (
          <form onSubmit={handleCredentials} noValidate>
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <h1 style={{ fontSize: 28 }}>Log in</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                Sign in to Idea Hub
              </p>
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label htmlFor="email">
                Email <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                id="email"
                className="input"
                type="email"
                autoComplete="username"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={!!emailError}
              />
              {emailError ? <FieldError message={emailError} /> : null}
            </div>

            <div className="field" style={{ marginBottom: 20 }}>
              <label htmlFor="password">
                Password <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="password"
                  className="input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={!!passwordError}
                  style={{ paddingRight: 44 }}
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--icon"
                  style={{
                    position: 'absolute',
                    right: 4,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    height: 32,
                    width: 32,
                  }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  <Icon name={showPassword ? 'eyeOff' : 'eye'} size={18} />
                </button>
              </div>
              {passwordError ? <FieldError message={passwordError} /> : null}
            </div>

            <button
              type="submit"
              className="btn btn--primary btn--block"
              disabled={busy}
              style={{ height: 44 }}
            >
              {busy ? 'Sending…' : 'Continue'}
              {!busy ? <Icon name="arrowRight" size={16} /> : null}
            </button>

            {microsoftEnabled ? (
              <>
                <div
                  className="row"
                  style={{
                    alignItems: 'center',
                    gap: 12,
                    margin: '20px 0 16px',
                  }}
                  aria-hidden="true"
                >
                  <span
                    style={{
                      flex: 1,
                      height: 1,
                      background: 'var(--border)',
                    }}
                  />
                  <span className="muted small" style={{ letterSpacing: '0.06em' }}>
                    OR
                  </span>
                  <span
                    style={{
                      flex: 1,
                      height: 1,
                      background: 'var(--border)',
                    }}
                  />
                </div>
                <button
                  type="button"
                  className="btn btn--block"
                  disabled={busy}
                  onClick={startMicrosoftSignIn}
                  style={{ height: 44, gap: 10 }}
                >
                  <MicrosoftMark size={18} />
                  Sign in with Microsoft
                </button>
              </>
            ) : null}

            {ssoError ? (
              <div style={{ marginTop: 16 }}>
                <FieldError message={ssoError} />
              </div>
            ) : null}
          </form>
        )}

        {step === 'verify' && (
          <form onSubmit={handleVerify} noValidate>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => {
                setStep('credentials');
                setOtp('');
                setOtpError('');
              }}
              style={{ marginBottom: 12, paddingLeft: 0 }}
            >
              <Icon name="arrowLeft" size={14} /> Back
            </button>

            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <h1 style={{ fontSize: 28 }}>Enter code</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                {otpMethod === 'totp'
                  ? 'Open your authenticator app for a 6-digit code'
                  : `We sent a ${OTP_LENGTH}-digit verification code`}
              </p>
            </div>

            {totpEnabled ? (
              <div
                className="segmented"
                role="tablist"
                aria-label="Verification method"
                style={{
                  display: 'flex',
                  width: '100%',
                  marginBottom: 20,
                }}
              >
                <label style={{ flex: 1 }}>
                  <input
                    type="radio"
                    name="otp-method"
                    checked={otpMethod === 'email'}
                    onChange={() => void selectOtpMethod('email')}
                  />
                  <span style={{ width: '100%' }}>Email code</span>
                </label>
                <label style={{ flex: 1 }}>
                  <input
                    type="radio"
                    name="otp-method"
                    checked={otpMethod === 'totp'}
                    onChange={() => void selectOtpMethod('totp')}
                  />
                  <span style={{ width: '100%' }}>Authenticator app</span>
                </label>
              </div>
            ) : null}

            {otpMethod === 'email' ? (
              <div className="notice notice--brand" style={{ marginBottom: 20 }}>
                <Icon name="mail" size={18} />
                <span>
                  Code sent to{' '}
                  <strong>{maskedEmail || email.trim()}</strong>
                  <span className="muted small">
                    {' '}
                    (dev: check backend console)
                  </span>
                </span>
              </div>
            ) : (
              <div className="notice notice--brand" style={{ marginBottom: 20 }}>
                <Icon name="lock" size={18} />
                <span>
                  Enter the code from Google Authenticator, Microsoft
                  Authenticator, or a compatible app.
                </span>
              </div>
            )}

            <div className="field" style={{ marginBottom: 12 }}>
              <label htmlFor="otp">
                Verification code <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                id="otp"
                className="input mono"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={OTP_LENGTH}
                pattern="\d*"
                value={otp}
                onChange={(e) => {
                  setOtp(e.target.value.replace(/\D/g, '').slice(0, OTP_LENGTH));
                  setOtpError('');
                }}
                aria-invalid={!!otpError}
                autoFocus
                style={{
                  letterSpacing: '0.35em',
                  fontSize: 22,
                  textAlign: 'center',
                }}
              />
              {otpError ? <FieldError message={otpError} /> : null}
            </div>

            {otpMethod === 'email' ? (
              <div
                className="row row--between"
                style={{ marginBottom: 20, fontSize: 13 }}
              >
                <span className="mono muted small">
                  {resendCooldown > 0
                    ? `Resend available in ${formatCountdown(resendCooldown)}`
                    : "Didn't get it?"}
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy || resendCooldown > 0}
                  onClick={handleResend}
                >
                  Resend code
                </button>
              </div>
            ) : (
              <div style={{ marginBottom: 20 }} />
            )}

            <button
              type="submit"
              className="btn btn--primary btn--block"
              disabled={busy}
              style={{ height: 44 }}
            >
              {busy ? 'Signing in…' : 'Log in'}
              {!busy ? <Icon name="arrowRight" size={16} /> : null}
            </button>
          </form>
        )}

        {step === 'success' && (
          <div style={{ textAlign: 'center', padding: '24px 0 8px' }}>
            <div
              style={{
                width: 64,
                height: 64,
                margin: '0 auto 16px',
                borderRadius: '50%',
                background: 'var(--success-soft)',
                color: 'var(--success)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <Icon name="check" size={34} />
            </div>
            <h2>You&apos;re in</h2>
            <p className="muted" style={{ marginTop: 8 }}>
              Redirecting to your workspace…
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
