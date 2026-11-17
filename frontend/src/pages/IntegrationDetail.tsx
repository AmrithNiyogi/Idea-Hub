/**
 * Provider detail — connect / disconnect personal (and org default for admins).
 * Coming-soon providers show planned note only (no fake connect form).
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

export function IntegrationDetailPage() {
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
  const [showForm, setShowForm] = useState(false);

  const comingSoon =
    !!provider && (provider.status === 'coming_soon' || !provider.connectable);

  const status = useMemo(() => {
    if (!provider) return null;
    return connectionStatusLabel(provider, effective ?? undefined);
  }, [provider, effective]);

  const personal =
    effective?.source === 'user' ? effective.connection : null;

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
    setShowForm(false);
  }, [providerId, scope]);

  useEffect(() => {
    if (focusOrg && isAdmin) setScope('organization');
  }, [focusOrg, isAdmin]);

  async function onConnect(e: FormEvent) {
    e.preventDefault();
    if (!provider || comingSoon) return;
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const body = {
        provider_id: provider.id,
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
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connect failed');
    } finally {
      setBusy(false);
    }
  }

  async function onDisconnectPersonal() {
    if (!provider || !personal) return;
    if (!window.confirm(`Disconnect your ${provider.display_name} connection?`)) {
      return;
    }
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await integrationsApi.disconnectMine(personal.id);
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
      !window.confirm(
        `Remove the organization default for ${provider.display_name}?`,
      )
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
              <h2>Your connection</h2>
              <span className="muted small">Personal</span>
            </div>
            {personal ? (
              <>
                <p className="muted small" style={{ marginTop: 0 }}>
                  {personal.display_label || 'Connected with your credentials.'}
                </p>
                <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn--sm"
                    disabled={busy}
                    onClick={() => {
                      setScope('user');
                      setShowForm(true);
                    }}
                  >
                    Update
                  </button>
                  <button
                    type="button"
                    className="btn btn--sm"
                    disabled={busy}
                    onClick={() => void onDisconnectPersonal()}
                  >
                    Disconnect
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="muted small" style={{ marginTop: 0 }}>
                  {effective?.source === 'organization' && effective.connection
                    ? `Using organization default (${effective.connection.display_label}). Connect personally to override.`
                    : 'Not connected yet. Delivery can still use an org default if one is set.'}
                </p>
                <button
                  type="button"
                  className="btn btn--sm btn--primary"
                  disabled={busy}
                  onClick={() => {
                    setScope('user');
                    setShowForm(true);
                  }}
                >
                  Connect
                </button>
              </>
            )}
          </section>

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
            <section className="card">
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
                className="stack"
                style={{ gap: 10, marginTop: 8 }}
                onSubmit={(e) => void onConnect(e)}
              >
                {formFields.map((f) => (
                  <label key={f.key} className="field">
                    <span className="field__label">
                      {f.label}
                      {f.required ? '' : ' (optional)'}
                    </span>
                    <input
                      type={f.secret ? 'password' : 'text'}
                      value={credValues[f.key] ?? ''}
                      placeholder={f.placeholder}
                      required={f.required}
                      autoComplete="off"
                      onChange={(e) =>
                        setCredValues((prev) => ({
                          ...prev,
                          [f.key]: e.target.value,
                        }))
                      }
                    />
                    {f.help_text ? (
                      <span className="muted small">{f.help_text}</span>
                    ) : null}
                  </label>
                ))}
                <div className="row">
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
        </>
      )}
    </div>
  );
}
