/**
 * Provider detail — connect / disconnect personal (and org default for admins).
 * Coming-soon providers show planned note only (no fake connect form).
 * Notion (docs) adds setup + Delivery deep-link guidance.
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { integrationsApi } from '../api/integrations';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import { IntegrationLogo } from '../components/integrations/IntegrationLogo';
import { connectionStatusLabel } from '../components/integrations/IntegrationTile';
import type {
  EffectiveConnection,
  IntegrationProvider,
  TrackerConnection,
} from '../types/trackers';
import { useDialog } from '../components/DialogProvider';

const MCP_SIGN_IN_ERRORS: Record<string, string> = {
  sign_in_expired: 'The sign-in link expired. Start again.',
  sign_in_wrong_user: 'That sign-in was started by a different account.',
  sign_in_cancelled: 'Sign-in was cancelled.',
  token_exchange_failed: 'The sign-in server did not accept the code. Try again.',
  server_unreachable: 'Signed in, but the MCP server could not be reached.',
};

export function IntegrationDetailPage() {
  const dialog = useDialog();
  const { providerId = '' } = useParams<{ providerId: string }>();
  const [searchParams] = useSearchParams();
  const focusOrg = searchParams.get('scope') === 'organization';

  const { user } = useAuth();
  const isAdmin = !!user?.roles?.includes('admin') || user?.active_role === 'admin';

  const [provider, setProvider] = useState<IntegrationProvider | null>(null);
  const [effective, setEffective] = useState<EffectiveConnection | null>(null);
  const [orgConnection, setOrgConnection] = useState<TrackerConnection | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState<'user' | 'organization'>(
    focusOrg && isAdmin ? 'organization' : 'user',
  );
  const [credValues, setCredValues] = useState<Record<string, string>>({});
  const [accountLabel, setAccountLabel] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [mine, setMine] = useState<TrackerConnection[]>([]);
  const [mcpEndpoint, setMcpEndpoint] = useState('');

  const comingSoon =
    !!provider && (provider.status === 'coming_soon' || !provider.connectable);

  const status = useMemo(() => {
    if (!provider) return null;
    return connectionStatusLabel(provider, effective ?? undefined);
  }, [provider, effective]);

  // Several personal accounts per provider (e.g. two Notion workspaces), each named by label.
  const personalList = useMemo(
    () => mine.filter((c) => c.provider_id === providerId),
    [mine, providerId],
  );

  const reload = useCallback(async () => {
    if (!providerId) return;
    setError(null);
    setLoading(true);
    try {
      const [providers, effList] = await Promise.all([
        integrationsApi.listProviders(),
        integrationsApi.listEffective(),
      ]);
      const p = providers.find((x) => x.id === providerId) ?? null;
      setProvider(p);
      const eff =
        effList.find((x) => x.provider_id === providerId) ?? null;
      setEffective(eff);
      setMine(await integrationsApi.listMine());

      if (isAdmin) {
        const org = await integrationsApi.listOrg().catch(() => []);
        setOrgConnection(org.find((c) => c.provider_id === providerId) ?? null);
      } else {
        setOrgConnection(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load provider');
    } finally {
      setLoading(false);
    }
  }, [providerId, isAdmin]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    setCredValues({});
    setAccountLabel('');
    setShowForm(false);
  }, [providerId, scope]);

  useEffect(() => {
    if (focusOrg && isAdmin) setScope('organization');
  }, [focusOrg, isAdmin]);

  // Result of the MCP sign-in redirect (?connected=1 or ?error=...).
  useEffect(() => {
    if (searchParams.get('connected')) {
      setMsg('MCP server connected.');
    }
    const code = searchParams.get('error');
    if (code) {
      setError(MCP_SIGN_IN_ERRORS[code] ?? 'Sign-in failed. Try again.');
    }
  }, [searchParams]);

  async function onMcpSignIn(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const res = await integrationsApi.startMcpOAuth({
        endpoint_url: mcpEndpoint.trim(),
        label: accountLabel.trim() || 'default',
      });
      window.location.assign(res.authorize_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start sign-in');
      setBusy(false);
    }
  }

  async function onConnect(e: FormEvent) {
    e.preventDefault();
    if (!provider || comingSoon) return;
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const body = {
        provider_id: provider.id,
        label: accountLabel.trim() || 'default',
        credentials: credValues,
      };
      if (scope === 'organization') {
        await integrationsApi.connectOrg(body);
        setMsg(`${provider.display_name} set as organization default.`);
      } else {
        await integrationsApi.connectMine(body);
        setMsg(`${provider.display_name} connected for you.`);
      }
      setShowForm(false);
      setCredValues({});
      setAccountLabel('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connect failed');
    } finally {
      setBusy(false);
    }
  }

  async function onDisconnectPersonal(conn: TrackerConnection) {
    if (!provider) return;
    if (
      !(await dialog.confirm({
        title: `Disconnect ${conn.label} (${provider.display_name})?`,
        confirmLabel: 'Disconnect',
        danger: true,
      }))
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await integrationsApi.disconnectMine(conn.id);
      setMsg(`${provider.display_name} disconnected.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnect failed');
    } finally {
      setBusy(false);
    }
  }

  async function onDisconnectOrg() {
    if (!provider || !orgConnection) return;
    if (
      !(await dialog.confirm({
        title: `Remove the organization default for ${provider.display_name}?`,
        confirmLabel: 'Remove',
        danger: true,
      }))
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await integrationsApi.disconnectOrg(orgConnection.id);
      setMsg(`Organization default for ${provider.display_name} removed.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnect failed');
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return <p className="muted">Sign in to manage integrations.</p>;
  }

  if (loading) {
    return <p className="muted">Loading…</p>;
  }

  if (!provider) {
    return (
      <div className="stack" style={{ gap: 16 }}>
        <Link to="/integrations" className="muted small">
          ← Integrations
        </Link>
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>Unknown provider “{providerId}”.</span>
        </div>
      </div>
    );
  }

  const formFields = provider.connect_fields;
  const editingOrg = scope === 'organization';
  const canShowForm = !comingSoon && showForm;

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div>
        <Link to="/integrations" className="muted small integ-back">
          ← Integrations
        </Link>
        <div className="integ-detail__head">
          <IntegrationLogo providerId={provider.id} size={56} />
          <div className="integ-detail__titles">
            <div className="eyebrow eyebrow--plain">
              {provider.category}
            </div>
            <h1>{provider.display_name}</h1>
            {status ? (
              <span
                className={`integ-tile__status integ-tile__status--${status.tone}`}
              >
                {status.label}
              </span>
            ) : null}
          </div>
        </div>
        <p className="muted" style={{ maxWidth: 560, marginTop: 8 }}>
          {comingSoon
            ? provider.coming_soon_note || provider.description
            : provider.description}
        </p>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}
      {msg ? (
        <div className="notice" role="status">
          <Icon name="check" size={16} />
          <span>{msg}</span>
        </div>
      ) : null}

      {comingSoon ? (
        <section className="card">
          <div className="card__head">
            <h2>Coming soon</h2>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            {provider.coming_soon_note ||
              `${provider.display_name} is on the roadmap. Connect will open here when it ships — no credentials are collected yet.`}
          </p>
        </section>
      ) : (
        <>
          <section className="card" id="personal">
            <div className="card__head">
              <h2>Your accounts</h2>
              <span className="muted small">Personal</span>
            </div>
            {personalList.length ? (
              <ul className="integ-accounts">
                {personalList.map((c) => (
                  <li key={c.id} className="integ-account">
                    <div className="integ-account__main">
                      <span className="integ-account__name">{c.label}</span>
                      <span className="muted small">
                        {c.display_label || 'Connected'}
                      </span>
                    </div>
                    <div className="row" style={{ gap: 6 }}>
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={busy}
                        onClick={() => {
                          setScope('user');
                          setAccountLabel(c.label);
                          setShowForm(true);
                        }}
                      >
                        Update
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        disabled={busy}
                        onClick={() => void onDisconnectPersonal(c)}
                      >
                        Disconnect
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small" style={{ marginTop: 0 }}>
                {effective?.source === 'organization' && effective.connection
                  ? `Using organization default (${effective.connection.display_label}). Connect your own account to override.`
                  : 'Not connected yet. Delivery can still use an org default if one is set.'}
              </p>
            )}
            <button
              type="button"
              className="btn btn--sm btn--primary"
              disabled={busy}
              onClick={() => {
                setScope('user');
                setAccountLabel('');
                setShowForm(true);
              }}
            >
              {personalList.length ? 'Add another account' : 'Connect'}
            </button>
          </section>

          {provider.id === 'mcp_server' ? (
            <section className="card integ-connect-card" id="mcp-sign-in">
              <div className="card__head">
                <h2>Sign in to an MCP server</h2>
                <span className="muted small">Recommended</span>
              </div>
              <p className="muted small" style={{ marginTop: 0 }}>
                For servers that use their own sign-in (for example Granola). You
                will be sent to that server&apos;s sign-in page and back here.
              </p>
              <form className="integ-connect" onSubmit={(e) => void onMcpSignIn(e)}>
                <label className="field integ-connect__field">
                  <span className="label">Account name</span>
                  <input
                    className="input"
                    value={accountLabel}
                    placeholder="e.g. Work"
                    maxLength={120}
                    autoComplete="off"
                    onChange={(e) => setAccountLabel(e.target.value)}
                  />
                </label>
                <label className="field integ-connect__field">
                  <span className="label">Server URL</span>
                  <input
                    className="input"
                    type="url"
                    value={mcpEndpoint}
                    placeholder="https://mcp.example.com/mcp"
                    required
                    autoComplete="off"
                    spellCheck={false}
                    onChange={(e) => setMcpEndpoint(e.target.value)}
                  />
                  <span className="hint">Must be HTTPS.</span>
                </label>
                <div className="integ-connect__actions">
                  <button type="submit" className="btn btn--sm btn--primary" disabled={busy}>
                    Sign in and connect
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          {isAdmin ? (
            <section className="card" id="organization">
              <div className="card__head">
                <h2>Organization default</h2>
                <span className="muted small">Admin</span>
              </div>
              <p className="muted small" style={{ marginTop: 0 }}>
                Used when a teammate has no personal connection for this
                provider.
              </p>
              {orgConnection ? (
                <>
                  <p className="muted small">
                    {orgConnection.display_label || 'Org default is set.'}
                  </p>
                  <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn--sm"
                      disabled={busy}
                      onClick={() => {
                        setScope('organization');
                        setShowForm(true);
                      }}
                    >
                      Update
                    </button>
                    <button
                      type="button"
                      className="btn btn--sm"
                      disabled={busy}
                      onClick={() => void onDisconnectOrg()}
                    >
                      Remove
                    </button>
                  </div>
                </>
              ) : (
                <button
                  type="button"
                  className="btn btn--sm btn--primary"
                  disabled={busy}
                  onClick={() => {
                    setScope('organization');
                    setShowForm(true);
                  }}
                >
                  Set default
                </button>
              )}
            </section>
          ) : null}

          {canShowForm ? (
            <section className="card integ-connect-card">
              <div className="card__head">
                <h2>
                  {editingOrg ? 'Organization default' : 'Connect'} —{' '}
                  {provider.display_name}
                </h2>
                <button
                  type="button"
                  className="btn btn--sm btn--ghost"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </button>
              </div>
              <form
                className="integ-connect"
                onSubmit={(e) => void onConnect(e)}
              >
                {scope === 'user' ? (
                  <label className="field integ-connect__field">
                    <span className="label">Account name</span>
                    <input
                      className="input"
                      value={accountLabel}
                      placeholder="e.g. Work, Personal"
                      maxLength={120}
                      autoComplete="off"
                      onChange={(e) => setAccountLabel(e.target.value)}
                    />
                    <span className="hint">
                      Name it to tell accounts apart. Leave empty for “default”.
                    </span>
                  </label>
                ) : null}
                {formFields
                  .filter((f) => !f.advanced)
                  .map((f) => (
                    <label key={f.key} className="field integ-connect__field">
                      <span className="label">
                        {f.label}
                        {f.required ? '' : ' (optional)'}
                      </span>
                      <input
                        className="input"
                        type={f.secret ? 'password' : 'text'}
                        value={credValues[f.key] ?? ''}
                        placeholder={f.placeholder}
                        required={f.required}
                        autoComplete="off"
                        spellCheck={false}
                        onChange={(e) =>
                          setCredValues((prev) => ({
                            ...prev,
                            [f.key]: e.target.value,
                          }))
                        }
                      />
                      {f.help_text ? (
                        <span className="hint">{f.help_text}</span>
                      ) : null}
                    </label>
                  ))}
                {formFields.some((f) => f.advanced) ? (
                  <details className="integ-connect__advanced">
                    <summary>Advanced (optional)</summary>
                    <div className="integ-connect__advanced-body">
                      {formFields
                        .filter((f) => f.advanced)
                        .map((f) => (
                          <label
                            key={f.key}
                            className="field integ-connect__field"
                          >
                            <span className="label">{f.label}</span>
                            <input
                              className="input"
                              type={f.secret ? 'password' : 'text'}
                              value={credValues[f.key] ?? ''}
                              placeholder={f.placeholder}
                              required={false}
                              autoComplete="off"
                              spellCheck={false}
                              onChange={(e) =>
                                setCredValues((prev) => ({
                                  ...prev,
                                  [f.key]: e.target.value,
                                }))
                              }
                            />
                            {f.help_text ? (
                              <span className="hint">{f.help_text}</span>
                            ) : null}
                          </label>
                        ))}
                    </div>
                  </details>
                ) : null}
                <div className="integ-connect__actions">
                  <button
                    type="submit"
                    className="btn btn--sm btn--primary"
                    disabled={busy}
                  >
                    Save connection
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          {provider.id === 'notion' && provider.category === 'docs' ? (
            <section className="card integ-doc-help">
              <div className="card__head">
                <h2>Docs actions</h2>
                <span className="muted small">From an idea</span>
              </div>
              <ol className="integ-doc-steps muted small">
                <li>
                  Create an{' '}
                  <a
                    href="https://www.notion.so/my-integrations"
                    target="_blank"
                    rel="noreferrer"
                  >
                    internal integration
                  </a>{' '}
                  in Notion and copy the secret into Connect above.
                </li>
                <li>
                  Open the <strong>parent page</strong> where idea documents
                  should live → ••• → Connections → invite your integration.
                  Paste that page ID as Parent page ID.
                </li>
                <li>
                  On an accepted idea → Delivery → <strong>Notion docs</strong>{' '}
                  → Create Notion page (problem + solution become page blocks)
                  or Link existing. Open the page URL anytime from the link
                  row.
                </li>
              </ol>
              <p className="muted small" style={{ marginBottom: 0 }}>
                Database IDs are optional (Advanced). Secrets stay encrypted;
                never commit them to git.
              </p>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
