/**
 * Integrations gallery — logo tiles that open a provider detail page.
 * Connect / disconnect forms live on `/integrations/:providerId`.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { integrationsApi } from '../api/integrations';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import {
  categoryLabel,
  IntegrationTile,
} from '../components/integrations/IntegrationTile';
import type {
  EffectiveConnection,
  IntegrationProvider,
} from '../types/trackers';

export function IntegrationsPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.roles?.includes('admin') || user?.active_role === 'admin';

  const [providers, setProviders] = useState<IntegrationProvider[]>([]);
  const [effective, setEffective] = useState<EffectiveConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const effectiveMap = useMemo(() => {
    const m = new Map<string, EffectiveConnection>();
    effective.forEach((e) => m.set(e.provider_id, e));
    return m;
  }, [effective]);

  const grouped = useMemo(() => {
    const g = new Map<string, IntegrationProvider[]>();
    providers.forEach((p) => {
      const key = p.category || 'tracker';
      const list = g.get(key) ?? [];
      list.push(p);
      g.set(key, list);
    });
    return [...g.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [providers]);

  const reload = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [p, e] = await Promise.all([
        integrationsApi.listProviders(),
        integrationsApi.listEffective(),
      ]);
      setProviders(p);
      setEffective(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load integrations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  if (!user) {
    return <p className="muted">Sign in to manage integrations.</p>;
  }

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Settings</div>
          <h1>Integrations</h1>
          <p className="muted" style={{ maxWidth: 560 }}>
            Connect trackers and other tools once. Open a tile to connect,
            update, or disconnect. Delivery uses your personal connection when
            set; otherwise the organization default.
          </p>
        </div>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      <section className="card">
        <div className="card__head">
          <h2>My integrations</h2>
          <span className="muted small">Personal overrides</span>
        </div>
        <p className="muted small" style={{ marginTop: 0 }}>
          Your connection takes precedence over the organization default for the
          same provider.
          {isAdmin ? (
            <>
              {' '}
              As an admin, set org defaults on each provider&apos;s detail page.
            </>
          ) : null}
        </p>

        {loading ? (
          <p className="muted">Loading providers…</p>
        ) : (
          grouped.map(([category, list]) => (
            <div key={category} className="integ-group">
              <div className="nav__label">{categoryLabel(category)}</div>
              <div className="integ-grid">
                {list.map((p) => (
                  <IntegrationTile
                    key={p.id}
                    provider={p}
                    effective={effectiveMap.get(p.id)}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </section>

      <p className="muted small">
        Account preferences live under{' '}
        <Link to="/settings">Account settings</Link>. Delivery on an idea uses
        these connections without re-entering tokens.
      </p>
    </div>
  );
}
