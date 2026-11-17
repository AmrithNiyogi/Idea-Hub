/** Clickable provider tile for the Integrations gallery. */

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

export function connectionStatusLabel(
  provider: IntegrationProvider,
  effective: EffectiveConnection | undefined,
): { label: string; tone: 'soon' | 'connected' | 'org' | 'none' } {
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

type Props = {
  provider: IntegrationProvider;
  effective?: EffectiveConnection;
};

export function IntegrationTile({ provider, effective }: Props) {
  const status = connectionStatusLabel(provider, effective);

  return (
    <Link
      to={`/integrations/${provider.id}`}
      className={`integ-tile integ-tile--${status.tone}`}
    >
      <IntegrationLogo providerId={provider.id} size={44} />
      <div className="integ-tile__body">
        <div className="integ-tile__title">{provider.display_name}</div>
        <div className={`integ-tile__status integ-tile__status--${status.tone}`}>
          {status.label}
        </div>
        <p className="integ-tile__desc muted small">
          {status.tone === 'soon'
            ? provider.coming_soon_note || provider.description
            : effective?.connection?.display_label || provider.description}
        </p>
      </div>
    </Link>
  );
}
