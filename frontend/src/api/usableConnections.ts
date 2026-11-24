/**
 * Every connection the signed-in user can use for delivery: their own accounts
 * (one per label) plus the organization default for each provider.
 */

import { integrationsApi } from './integrations';
import type { TrackerConnection } from '../types/trackers';

export type UsableConnection = {
  connection: TrackerConnection;
  source: 'user' | 'organization';
};

export async function listUsableConnections(
  providerIds?: ReadonlySet<string>,
): Promise<UsableConnection[]> {
  const [mine, effective] = await Promise.all([
    integrationsApi.listMine().catch(() => [] as TrackerConnection[]),
    integrationsApi.listEffective().catch(() => []),
  ]);
  const out: UsableConnection[] = mine.map((connection) => ({
    connection,
    source: 'user',
  }));
  const seen = new Set(out.map((o) => o.connection.id));
  for (const e of effective) {
    if (e.source === 'organization' && e.connection && !seen.has(e.connection.id)) {
      seen.add(e.connection.id);
      out.push({ connection: e.connection, source: 'organization' });
    }
  }
  return out
    .filter((o) => !providerIds || providerIds.has(o.connection.provider_id))
    .sort((a, b) =>
      `${a.connection.provider_id} ${a.connection.label}`.localeCompare(
        `${b.connection.provider_id} ${b.connection.label}`,
      ),
    );
}

export function usableLabel(
  item: UsableConnection,
  providerName: string,
): string {
  const who = item.connection.display_label || item.connection.label;
  const src = item.source === 'user' ? 'my account' : 'org default';
  return `${providerName} — ${item.connection.label}${who && who !== item.connection.label ? ` (${who})` : ''} · ${src}`;
}
