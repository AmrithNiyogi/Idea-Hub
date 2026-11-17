/**
 * Integrations list — searchable/filterable rows that open a provider detail page.
 * Connect / disconnect forms live on `/integrations/:providerId`.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { integrationsApi } from '../api/integrations';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import {
  categoryLabel,
  connectionStatusLabel,
  IntegrationTile,
  statusFilterBucket,
  type StatusFilter,
} from '../components/integrations/IntegrationTile';
import type {
  EffectiveConnection,
  IntegrationProvider,
} from '../types/trackers';

const STATUS_FILTERS: { id: StatusFilter; label: string }[] = [
  { id: 'all', label: 'All statuses' },
  { id: 'connected', label: 'Connected' },
  { id: 'soon', label: 'Coming soon' },
  { id: 'none', label: 'Not connected' },
];

export function IntegrationsPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.roles?.includes('admin') || user?.active_role === 'admin';

  const [providers, setProviders] = useState<IntegrationProvider[]>([]);
  const [effective, setEffective] = useState<EffectiveConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const effectiveMap = useMemo(() => {
    const m = new Map<string, EffectiveConnection>();
    effective.forEach((e) => m.set(e.provider_id, e));
    return m;
  }, [effective]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    providers.forEach((p) => set.add(p.category || 'tracker'));
    return [...set].sort((a, b) =>
      categoryLabel(a).localeCompare(categoryLabel(b)),
    );
  }, [providers]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return providers
      .filter((p) => {
        const cat = p.category || 'tracker';
        if (category !== 'all' && cat !== category) return false;

        const eff = effectiveMap.get(p.id);
        const tone = connectionStatusLabel(p, eff).tone;
        const bucket = statusFilterBucket(tone);
        if (statusFilter !== 'all' && bucket !== statusFilter) return false;

        if (!q) return true;
        const hay = [
          p.display_name,
          p.description,
          p.id,
          p.coming_soon_note,
          categoryLabel(cat),
        ]
          .join(' ')
          .toLowerCase();
        return hay.includes(q);
      })
      .sort((a, b) => a.display_name.localeCompare(b.display_name));
  }, [providers, query, category, statusFilter, effectiveMap]);

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
            Connect trackers and other tools once. Open a row to connect, update,
            or disconnect. Delivery uses your personal connection when set;
            otherwise the organization default.
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

        <div className="integ-toolbar">
          <label className="integ-search">
            <span className="integ-search__icon" aria-hidden>
              <Icon name="search" size={16} />
            </span>
            <input
              type="search"
              className="integ-search__input"
              placeholder="Search by name, description, or id…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search integrations"
            />
          </label>

          <div className="chip-row" role="group" aria-label="Category">
            <button
              type="button"
              className="chip-link"
              aria-current={category === 'all' ? 'true' : undefined}
              onClick={() => setCategory('all')}
            >
              All
              <span className="count">{providers.length}</span>
            </button>
            {categories.map((id) => {
              const n = providers.filter(
                (p) => (p.category || 'tracker') === id,
              ).length;
              return (
                <button
                  key={id}
                  type="button"
                  className="chip-link"
                  aria-current={category === id ? 'true' : undefined}
                  onClick={() => setCategory(id)}
                >
                  {categoryLabel(id)}
                  <span className="count">{n}</span>
                </button>
              );
            })}
          </div>

          <div className="chip-row" role="group" aria-label="Connection status">
            {STATUS_FILTERS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                className="chip-link"
                aria-current={statusFilter === id ? 'true' : undefined}
                onClick={() => setStatusFilter(id)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="muted">Loading providers…</p>
        ) : filtered.length === 0 ? (
          <div className="empty" style={{ padding: '24px 0' }}>
            <Icon name="search" size={28} />
            <h3>Nothing matches</h3>
            <p className="muted small">
              Try another search or clear the category and status filters.
            </p>
          </div>
        ) : (
          <div className="integ-list" role="list">
            {filtered.map((p) => (
              <div key={p.id} role="listitem">
                <IntegrationTile
                  provider={p}
                  effective={effectiveMap.get(p.id)}
                />
              </div>
            ))}
          </div>
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
