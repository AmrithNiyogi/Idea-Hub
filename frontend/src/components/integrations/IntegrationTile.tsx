/** Provider list row + shared status/category helpers for Integrations. */

import { Link } from 'react-router-dom';
import type { EffectiveConnection, IntegrationProvider } from '../../types/trackers';
import { IntegrationLogo } from './IntegrationLogo';

const CATEGORY_LABEL: Record<string, string> = {
  tracker: 'Trackers',
  docs: 'Docs',
  sheets: 'Spreadsheets',
  chat: 'Chat',
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABEL[category] ?? category;
}

export type ConnectionStatusTone = 'soon' | 'connected' | 'org' | 'none';

export function connectionStatusLabel(
  provider: IntegrationProvider,
  effective: EffectiveConnection | undefined,
): { label: string; tone: ConnectionStatusTone } {
  const comingSoon = provider.status === 'coming_soon' || !provider.connectable;
  if (comingSoon) return { label: 'Coming soon', tone: 'soon' };
  if (effective?.source === 'user' && effective.connection) {
    return { label: 'Connected', tone: 'connected' };
  }
  if (effective?.source === 'organization' && effective.connection) {
    return { label: 'Org default', tone: 'org' };
  }
  return { label: 'Not connected', tone: 'none' };
}

/** Coarse status buckets for list filters (org default counts as connected). */
export type StatusFilter = 'all' | 'connected' | 'soon' | 'none';

export function statusFilterBucket(tone: ConnectionStatusTone): Exclude<StatusFilter, 'all'> {
  if (tone === 'soon') return 'soon';
  if (tone === 'none') return 'none';
  return 'connected';
}

type Props = {
  provider: IntegrationProvider;
  effective?: EffectiveConnection;
};

export function IntegrationTile({ provider, effective }: Props) {
  const status = connectionStatusLabel(provider, effective);
  const desc =
    status.tone === 'soon'
      ? provider.coming_soon_note || provider.description
      : effective?.connection?.display_label || provider.description;

  return (
    <Link
      to={`/integrations/${provider.id}`}
      className={`integ-row integ-row--${status.tone}`}
    >
      <IntegrationLogo providerId={provider.id} size={40} />
      <div className="integ-row__main">
        <div className="integ-row__head">
          <span className="integ-row__title">{provider.display_name}</span>
          <span className={`integ-tile__status integ-tile__status--${status.tone}`}>
            {status.label}
          </span>
        </div>
        <p className="integ-row__desc muted small">{desc}</p>
      </div>
      <span className="integ-row__chevron muted" aria-hidden>
        ›
      </span>
    </Link>
  );
}
