/**
 * My Profile / Account settings — editable view for the signed-in user.
 *
 * Distinct from `/people/:id` (public contribution profile).
 * Avatar upload opens a square crop dialog before POST /users/me/avatar.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { accountApi } from '../api/account';
import {
  confirmTotp,
  disableTotp,
  getTotpStatus,
  setupTotp,
} from '../api/auth';
import { usersApi, type Team } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { AvatarCropDialog } from '../components/AvatarCropDialog';
import { Avatar, Icon } from '../components/Icons';
import { roleLabel, sortRoles } from '../constants/roles';
import type { TotpSetupResponse } from '../types/auth';

const AVATAR_PRESETS = [1, 2, 3, 4, 5, 6, 7, 8] as const;
const AVATAR_ACCEPT = 'image/jpeg,image/png,image/webp,image/gif';

interface PendingCrop {
  src: string;
  outputType: 'image/jpeg' | 'image/png';
}

export function AccountSettingsPage() {
  const { user, refetchUser } = useAuth();
  const [team, setTeam] = useState<Team | null>(null);

  const [name, setName] = useState('');
  const [title, setTitle] = useState('');
  const [avatar, setAvatar] = useState(1);
  const [avatarUrl, setAvatarUrl] = useState('');
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileErr, setProfileErr] = useState<string | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [pwSaving, setPwSaving] = useState(false);

  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [pendingCrop, setPendingCrop] = useState<PendingCrop | null>(null);
  const cropObjectUrlRef = useRef<string | null>(null);

  const [totpEnabled, setTotpEnabled] = useState(false);
  const [mfaAvailable, setMfaAvailable] = useState(true);
  const [totpSetup, setTotpSetup] = useState<TotpSetupResponse | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [totpDisablePassword, setTotpDisablePassword] = useState('');
  const [totpDisableCode, setTotpDisableCode] = useState('');
  const [totpMsg, setTotpMsg] = useState<string | null>(null);
  const [totpErr, setTotpErr] = useState<string | null>(null);
  const [totpBusy, setTotpBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setTitle(user.title || '');
    setAvatar(user.avatar || 1);
    setAvatarUrl(user.avatar_url || '');
    setTotpEnabled(!!user.totp_enabled);
    setMfaAvailable(user.has_password !== false);
  }, [user]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    getTotpStatus()
      .then((s) => {
        if (!cancelled) {
          setTotpEnabled(s.totp_enabled);
          setMfaAvailable(s.mfa_available);
        }
      })
      .catch(() => {
        /* keep flags from user payload */
      });
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  useEffect(() => {
    return () => {
      if (cropObjectUrlRef.current) {
        URL.revokeObjectURL(cropObjectUrlRef.current);
        cropObjectUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!user?.team_id) {
      setTeam(null);
      return;
    }
    let cancelled = false;
    usersApi
      .teams()
      .then((teams) => {
        if (!cancelled) {
          setTeam(teams.find((t) => t.id === user.team_id) ?? null);
        }
      })
      .catch(() => {
        if (!cancelled) setTeam(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.team_id]);

  if (!user) {
    return <p className="muted">Sign in to manage your account.</p>;
  }

  async function onSaveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileErr(null);
    setProfileMsg(null);
    setProfileSaving(true);
    try {
      await accountApi.updateMe({
        name: name.trim(),
        title: title.trim(),
        avatar,
        avatar_url: avatarUrl.trim(),
      });
      await refetchUser();
      setProfileMsg('Profile saved.');
    } catch (err) {
      setProfileErr(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setProfileSaving(false);
    }
  }

  async function onChangePassword(e: FormEvent) {
    e.preventDefault();
    setPwErr(null);
    setPwMsg(null);
    if (newPassword !== confirmPassword) {
      setPwErr('New password and confirmation do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setPwErr('New password must be at least 8 characters.');
      return;
    }
    setPwSaving(true);
    try {
      await accountApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPwMsg('Password updated.');
    } catch (err) {
      setPwErr(err instanceof Error ? err.message : 'Password change failed');
    } finally {
      setPwSaving(false);
    }
  }

  function discardPendingCrop() {
    if (cropObjectUrlRef.current) {
      URL.revokeObjectURL(cropObjectUrlRef.current);
      cropObjectUrlRef.current = null;
    }
    setPendingCrop(null);
  }

  function onPickAvatarFile(file: File | undefined) {
    if (!file) return;
    setUploadErr(null);
    if (!file.type.startsWith('image/')) {
      setUploadErr('Choose a JPEG, PNG, WebP, or GIF image.');
      return;
    }
    discardPendingCrop();
    const src = URL.createObjectURL(file);
    cropObjectUrlRef.current = src;
    // Preserve PNG when source is PNG; otherwise export JPEG for upload size.
    const outputType: 'image/jpeg' | 'image/png' =
      file.type === 'image/png' ? 'image/png' : 'image/jpeg';
    setPendingCrop({ src, outputType });
  }

  async function onConfirmCroppedAvatar(file: File) {
    setUploadErr(null);
    setUploading(true);
    try {
      const updated = await accountApi.uploadAvatar(file);
      setAvatarUrl(updated.avatar_url || '');
      await refetchUser();
      setProfileMsg('Avatar uploaded.');
      discardPendingCrop();
    } catch (err) {
      setUploadErr(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  async function onClearAvatar() {
    setUploadErr(null);
    setProfileSaving(true);
    try {
      await accountApi.updateMe({ avatar_url: '' });
      setAvatarUrl('');
      await refetchUser();
      setProfileMsg('Avatar image cleared.');
    } catch (err) {
      setUploadErr(err instanceof Error ? err.message : 'Clear failed');
    } finally {
      setProfileSaving(false);
    }
  }

  async function onStartTotp() {
    setTotpErr(null);
    setTotpMsg(null);
    setTotpBusy(true);
    try {
      const setup = await setupTotp();
      setTotpSetup(setup);
      setTotpCode('');
    } catch (err) {
      setTotpErr(err instanceof Error ? err.message : 'Could not start MFA setup');
    } finally {
      setTotpBusy(false);
    }
  }

  async function onConfirmTotp(e: FormEvent) {
    e.preventDefault();
    setTotpErr(null);
    setTotpMsg(null);
    if (totpCode.length !== 6) {
      setTotpErr('Enter the 6-digit code from your authenticator app.');
      return;
    }
    setTotpBusy(true);
    try {
      await confirmTotp(totpCode);
      setTotpSetup(null);
      setTotpCode('');
      setTotpEnabled(true);
      setTotpMsg('Authenticator MFA is now enabled.');
      await refetchUser();
    } catch (err) {
      setTotpErr(err instanceof Error ? err.message : 'Could not confirm MFA');
    } finally {
      setTotpBusy(false);
    }
  }

  async function onDisableTotp(e: FormEvent) {
    e.preventDefault();
    setTotpErr(null);
    setTotpMsg(null);
    setTotpBusy(true);
    try {
      await disableTotp({
        password: totpDisablePassword,
        code: totpDisableCode,
      });
      setTotpDisablePassword('');
      setTotpDisableCode('');
      setTotpEnabled(false);
      setTotpSetup(null);
      setTotpMsg('Authenticator MFA disabled.');
      await refetchUser();
    } catch (err) {
      setTotpErr(err instanceof Error ? err.message : 'Could not disable MFA');
    } finally {
      setTotpBusy(false);
    }
  }

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Account</div>
          <h1>My profile</h1>
          <p className="muted">
            Update how you appear in Idea Hub. Your public contribution page is
            at{' '}
            <Link to={`/people/${user.id}`}>/people/{user.id.slice(0, 8)}…</Link>
            .
          </p>
        </div>
      </div>

      <div className="card">
        <div className="profile-head">
          <Avatar
            name={name || user.name}
            avatar={avatar}
            avatarUrl={avatarUrl || user.avatar_url}
            size="lg"
          />
          <div className="grow" style={{ minWidth: 0 }}>
            <div className="eyebrow eyebrow--plain">
              {sortRoles(user.roles).map(roleLabel).join(' · ')}
              {' · this is you'}
            </div>
            <h2 style={{ margin: '4px 0' }}>{name || user.name}</h2>
            <p className="muted" style={{ margin: 0 }}>
              <span className="mono">{user.email}</span>
              {title ? ` · ${title}` : ''}
              {team ? ` · ${team.name}` : ''}
            </p>
            <div className="row" style={{ gap: 6, marginTop: 8 }} aria-label="Roles">
              {sortRoles(user.roles).map((r) => (
                <span
                  key={r}
                  className={`pill${r === user.active_role ? ' pill--brand' : ''}`}
                >
                  {roleLabel(r)}
                  {r === user.active_role ? ' · working as' : ''}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <form className="card" onSubmit={onSaveProfile} aria-label="Profile settings">
        <div className="card__head">
          <h2>Profile details</h2>
        </div>

        <div className="stack" style={{ gap: 16 }}>
          <div className="field">
            <label htmlFor="acct-email">Email</label>
            <input
              id="acct-email"
              className="input"
              type="email"
              value={user.email}
              disabled
              readOnly
            />
            <span className="hint">Email cannot be changed here.</span>
          </div>

          <div className="field">
            <label htmlFor="acct-name">Display name</label>
            <input
              id="acct-name"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={160}
              autoComplete="name"
            />
          </div>

          <div className="field">
            <label htmlFor="acct-title">Job title</label>
            <input
              id="acct-title"
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={160}
              placeholder="e.g. Senior Engineer"
            />
          </div>

          <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
            <legend style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
              Avatar colour
            </legend>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              {AVATAR_PRESETS.map((n) => (
                <button
                  key={n}
                  type="button"
                  className={`btn btn--sm${avatar === n ? ' btn--primary' : ''}`}
                  aria-pressed={avatar === n}
                  aria-label={`Colour preset ${n}`}
                  onClick={() => setAvatar(n)}
                  style={{ padding: 4 }}
                >
                  <Avatar name={name || user.name} avatar={n} size="sm" />
                </button>
              ))}
            </div>
            <span className="hint">
              Used for initials when no profile image is set.
            </span>
          </fieldset>

          <div className="field">
            <label htmlFor="acct-avatar-url">Profile image URL (optional)</label>
            <input
              id="acct-avatar-url"
              className="input"
              type="text"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://… or /uploads/avatars/…"
            />
            <span className="hint">
              Absolute https URL, or a path from Upload below. Pick an image,
              crop to a square, then Confirm to upload (JPEG/PNG, max 2 MB).
            </span>
          </div>

          <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <label className="btn btn--sm">
              <Icon name="plus" size={14} />
              {uploading ? 'Uploading…' : 'Upload image'}
              <input
                type="file"
                accept={AVATAR_ACCEPT}
                hidden
                disabled={uploading || !!pendingCrop}
                onChange={(e) => {
                  onPickAvatarFile(e.target.files?.[0]);
                  e.target.value = '';
                }}
              />
            </label>
            {avatarUrl ? (
              <button
                type="button"
                className="btn btn--sm btn--ghost"
                onClick={() => void onClearAvatar()}
                disabled={profileSaving || uploading}
              >
                Clear image
              </button>
            ) : null}
          </div>
          {uploadErr ? (
            <p className="error" role="alert">
              {uploadErr}
            </p>
          ) : null}

          {profileErr ? (
            <div className="notice notice--danger" role="alert">
              <Icon name="alert" size={16} />
              <span>{profileErr}</span>
            </div>
          ) : null}
          {profileMsg ? (
            <div className="notice notice--brand" role="status">
              <Icon name="checkcircle" size={16} />
              <span>{profileMsg}</span>
            </div>
          ) : null}

          <div className="row" style={{ gap: 8 }}>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={profileSaving}
            >
              {profileSaving ? 'Saving…' : 'Save profile'}
            </button>
            <Link className="btn btn--ghost" to={`/people/${user.id}`}>
              View public profile
            </Link>
          </div>
        </div>
      </form>

      {mfaAvailable ? (
        <section className="card" aria-label="Authenticator MFA">
          <div className="card__head">
            <h2>Authenticator app (MFA)</h2>
            <span className={`pill${totpEnabled ? ' pill--brand' : ''}`}>
              {totpEnabled ? 'Enabled' : 'Off'}
            </span>
          </div>
          <div className="stack" style={{ gap: 16 }}>
            <p className="muted" style={{ margin: 0 }}>
              Use Google Authenticator, Microsoft Authenticator, or any TOTP app
              as a second factor alongside email OTP. At login you can choose
              either method when MFA is enabled.
            </p>

            {!totpEnabled && !totpSetup ? (
              <button
                type="button"
                className="btn btn--primary"
                disabled={totpBusy}
                onClick={() => void onStartTotp()}
              >
                {totpBusy ? 'Preparing…' : 'Set up authenticator'}
              </button>
            ) : null}

            {totpSetup ? (
              <form
                className="stack"
                style={{ gap: 16, maxWidth: 420 }}
                onSubmit={onConfirmTotp}
              >
                <div
                  className="row"
                  style={{ gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}
                >
                  <img
                    src={`data:image/png;base64,${totpSetup.qr_png_base64}`}
                    alt="Scan this QR code with your authenticator app"
                    width={168}
                    height={168}
                    style={{
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)',
                      background: '#fff',
                    }}
                  />
                  <div
                    className="stack"
                    style={{ gap: 8, flex: 1, minWidth: 200 }}
                  >
                    <p className="muted small" style={{ margin: 0 }}>
                      Scan the QR code, or enter this secret manually:
                    </p>
                    <code className="mono" style={{ wordBreak: 'break-all' }}>
                      {totpSetup.secret}
                    </code>
                    <span className="hint">
                      Setup expires in about{' '}
                      {Math.round(totpSetup.expires_in_seconds / 60)} minutes.
                    </span>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="totp-confirm">6-digit code</label>
                  <input
                    id="totp-confirm"
                    className="input mono"
                    inputMode="numeric"
                    maxLength={6}
                    pattern="\d*"
                    value={totpCode}
                    onChange={(e) =>
                      setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                    }
                    required
                    style={{ letterSpacing: '0.25em', maxWidth: 180 }}
                  />
                </div>
                <div className="row" style={{ gap: 8 }}>
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={totpBusy}
                  >
                    {totpBusy ? 'Confirming…' : 'Confirm and enable'}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={totpBusy}
                    onClick={() => {
                      setTotpSetup(null);
                      setTotpCode('');
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : null}

            {totpEnabled ? (
              <form
                className="stack"
                style={{ gap: 16, maxWidth: 420 }}
                onSubmit={onDisableTotp}
              >
                <p className="muted small" style={{ margin: 0 }}>
                  To turn MFA off, enter your password and a current authenticator
                  code. If you are locked out, ask an admin to clear MFA (see{' '}
                  <span className="mono">docs/MFA_TOTP.md</span>).
                </p>
                <div className="field">
                  <label htmlFor="totp-disable-pw">Password</label>
                  <input
                    id="totp-disable-pw"
                    className="input"
                    type="password"
                    autoComplete="current-password"
                    value={totpDisablePassword}
                    onChange={(e) => setTotpDisablePassword(e.target.value)}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="totp-disable-code">Authenticator code</label>
                  <input
                    id="totp-disable-code"
                    className="input mono"
                    inputMode="numeric"
                    maxLength={6}
                    pattern="\d*"
                    value={totpDisableCode}
                    onChange={(e) =>
                      setTotpDisableCode(
                        e.target.value.replace(/\D/g, '').slice(0, 6),
                      )
                    }
                    required
                    style={{ letterSpacing: '0.25em', maxWidth: 180 }}
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn--danger"
                  disabled={totpBusy}
                >
                  {totpBusy ? 'Disabling…' : 'Disable authenticator MFA'}
                </button>
              </form>
            ) : null}

            {totpErr ? (
              <div className="notice notice--danger" role="alert">
                <Icon name="alert" size={16} />
                <span>{totpErr}</span>
              </div>
            ) : null}
            {totpMsg ? (
              <div className="notice notice--brand" role="status">
                <Icon name="checkcircle" size={16} />
                <span>{totpMsg}</span>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      <form
        className="card"
        onSubmit={onChangePassword}
        aria-label="Change password"
      >
        <div className="card__head">
          <h2>Change password</h2>
        </div>
        <div className="stack" style={{ gap: 16, maxWidth: 420 }}>
          <div className="field">
            <label htmlFor="acct-cur-pw">Current password</label>
            <input
              id="acct-cur-pw"
              className="input"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="acct-new-pw">New password</label>
            <input
              id="acct-new-pw"
              className="input"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
            />
            <span className="hint">At least 8 characters.</span>
          </div>
          <div className="field">
            <label htmlFor="acct-confirm-pw">Confirm new password</label>
            <input
              id="acct-confirm-pw"
              className="input"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {pwErr ? (
            <div className="notice notice--danger" role="alert">
              <Icon name="alert" size={16} />
              <span>{pwErr}</span>
            </div>
          ) : null}
          {pwMsg ? (
            <div className="notice notice--brand" role="status">
              <Icon name="checkcircle" size={16} />
              <span>{pwMsg}</span>
            </div>
          ) : null}

          <button type="submit" className="btn btn--primary" disabled={pwSaving}>
            {pwSaving ? 'Updating…' : 'Update password'}
          </button>
        </div>
      </form>

      {pendingCrop ? (
        <AvatarCropDialog
          imageSrc={pendingCrop.src}
          outputType={pendingCrop.outputType}
          confirming={uploading}
          onCancel={discardPendingCrop}
          onConfirm={onConfirmCroppedAvatar}
        />
      ) : null}
    </div>
  );
}

export default AccountSettingsPage;
