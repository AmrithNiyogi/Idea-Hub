import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listUsableConnections, usableLabel } from './usableConnections';
import { integrationsApi } from './integrations';
import type { TrackerConnection } from '../types/trackers';

vi.mock('./integrations', () => ({
  integrationsApi: {
    listMine: vi.fn(),
    listEffective: vi.fn(),
  },
}));

function conn(id: string, provider: string, label: string): TrackerConnection {
  return {
    id,
    provider_id: provider,
    label,
    display_label: `${label}-ws`,
    scope: 'user',
  } as unknown as TrackerConnection;
}

describe('listUsableConnections', () => {
  beforeEach(() => vi.clearAllMocks());

  it('merges personal accounts with org defaults and filters by provider', async () => {
    vi.mocked(integrationsApi.listMine).mockResolvedValue([
      conn('a', 'notion', 'Work'),
      conn('b', 'notion', 'Personal'),
      conn('c', 'clickup', 'Team'),
    ]);
    vi.mocked(integrationsApi.listEffective).mockResolvedValue([
      { provider_id: 'notion', source: 'organization', connection: conn('org', 'notion', 'default') },
      { provider_id: 'jira', source: 'none', connection: null },
    ] as never);

    const out = await listUsableConnections(new Set(['notion']));
    expect(out.map((o) => o.connection.id)).toEqual(['org', 'b', 'a']);
    expect(out.find((o) => o.connection.id === 'org')?.source).toBe('organization');
    expect(out.find((o) => o.connection.id === 'a')?.source).toBe('user');
  });

  it('does not duplicate a connection that appears twice', async () => {
    const same = conn('x', 'notion', 'Work');
    vi.mocked(integrationsApi.listMine).mockResolvedValue([same]);
    vi.mocked(integrationsApi.listEffective).mockResolvedValue([
      { provider_id: 'notion', source: 'organization', connection: same },
    ] as never);
    const out = await listUsableConnections();
    expect(out).toHaveLength(1);
  });

  it('tolerates failing lookups', async () => {
    vi.mocked(integrationsApi.listMine).mockRejectedValue(new Error('down'));
    vi.mocked(integrationsApi.listEffective).mockRejectedValue(new Error('down'));
    expect(await listUsableConnections()).toEqual([]);
  });
});

describe('usableLabel', () => {
  it('names the provider, account and source', () => {
    const label = usableLabel(
      { connection: conn('a', 'notion', 'Work'), source: 'user' },
      'Notion',
    );
    expect(label).toBe('Notion — Work (Work-ws) · my account');
  });
});
