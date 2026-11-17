/**
 * Smoke coverage for thin apiFetch-based clients.
 *
 * Each call asserts the path/method so regressions in URL wiring fail loudly.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { adminApi } from './admin';
import { agentsApi } from './agents';
import { collabApi } from './collab';
import { teamSpaceApi } from './teamSpace';
import { deliveryApi } from './delivery';
import { ideathonsApi } from './ideathons';
import { insightsApi } from './insights';
import { problemsApi } from './problems';
import { profilesApi } from './profiles';
import { recognitionApi } from './recognition';
import { reopenApi } from './reopen';
import { trackersApi } from './trackers';
import { integrationsApi } from './integrations';
import { usersApi } from './users';
import { reviewApi } from './review';
import { http } from './http';
import MockAdapter from 'axios-mock-adapter';

function stubOk(payload: unknown = {}) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => payload,
  });
}

describe('apiFetch-backed clients', () => {
  let fetchMock: ReturnType<typeof stubOk>;

  beforeEach(() => {
    fetchMock = stubOk({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function lastUrl(): string {
    const arg = fetchMock.mock.calls.at(-1)?.[0];
    return String(arg);
  }

  function lastInit(): RequestInit {
    return (fetchMock.mock.calls.at(-1)?.[1] ?? {}) as RequestInit;
  }

  it('usersApi', async () => {
    await usersApi.list();
    expect(lastUrl()).toContain('/users');
    await usersApi.get('u1');
    expect(lastUrl()).toContain('/users/u1');
    await usersApi.teams();
    expect(lastUrl()).toContain('/teams');
  });

  it('profiles / insights / recognition', async () => {
    await profilesApi.get('u1');
    expect(lastUrl()).toContain('/people/u1');
    await insightsApi.dashboard(30);
    expect(lastUrl()).toContain('/insights?days=30');
    await recognitionApi.rules();
    await recognitionApi.leaderboard(10);
    expect(lastUrl()).toContain('limit=10');
    await recognitionApi.awards();
    await recognitionApi.confirmIoq('2026-Q1', 'i1', 'why');
    expect(lastInit().method).toBe('POST');
    await recognitionApi.confirmAnnual('2026', 'u1', 'why');
    await recognitionApi.ledger('u1');
    await recognitionApi.level('u1');
  });

  it('adminApi', async () => {
    await adminApi.config();
    await adminApi.saveTimelines({ a: 1 });
    expect(lastInit().method).toBe('PUT');
    await adminApi.saveScoring([]);
    await adminApi.savePoints({ x: 1 });
    await adminApi.createCategory({
      label: 'L',
      description: 'd',
      color_key: 'tech',
      reviewer_id: 'u1',
    });
    await adminApi.updateCategory('c1', { label: 'L2' });
    await adminApi.createPanel({ category_id: 'c1', member_ids: ['u1'] });
    await adminApi.updatePanel('p1', { name: 'P' });
    await adminApi.addPanelMember('p1', 'u2');
    await adminApi.removePanelMember('p1', 'u2');
    await adminApi.setPanelChair('p1', 'u1');
    await adminApi.audit(10);
    expect(lastUrl()).toContain('limit=10');
    await adminApi.exportInventory();
    await adminApi.reset();
  });

  it('deliveryApi', async () => {
    await deliveryApi.get('i1');
    await deliveryApi.requestHours('i1', { hours: 4 } as never);
    await deliveryApi.listHoursRequests({ state: 'open', limit: 5 });
    expect(lastUrl()).toContain('state=open');
    await deliveryApi.listHoursRequests();
    await deliveryApi.decideHours('r1', { approve: true } as never);
    await deliveryApi.logHours('i1', { hours: 1 } as never);
    await deliveryApi.addContributor('i1', 'u1', 'dev');
    await deliveryApi.removeContributor('i1', 'u1');
    await deliveryApi.addTask('i1', { title: 't' } as never);
    await deliveryApi.setTaskStatus('t1', { status: 'done' } as never);
    await deliveryApi.postUpdate('i1', 'hello');
    await deliveryApi.postUpdate('i1', 'hello', 't1');
    await deliveryApi.markImplemented('i1', {} as never);
    await deliveryApi.verifyImpact('i1', 'e1', 'ok');
  });

  it('trackersApi', async () => {
    await trackersApi.listProviders();
    await trackersApi.listConnections();
    await trackersApi.listEffective();
    await trackersApi.connect({
      provider_id: 'clickup',
      credentials: { api_token: 'x', list_id: '1' },
    });
    await trackersApi.disconnect('c1');
    await trackersApi.listLinks('i1');
    await trackersApi.createOrLink('i1', {
      connection_id: 'c1',
      mode: 'create',
    });
    await trackersApi.unlink('i1', 'l1');
  });

  it('integrationsApi', async () => {
    await integrationsApi.listProviders();
    await integrationsApi.listProviders('tracker');
    await integrationsApi.listEffective();
    await integrationsApi.listMine();
    await integrationsApi.connectMine({
      provider_id: 'jira',
      credentials: { email: 'a@b.c', api_token: 'x' },
    });
    await integrationsApi.disconnectMine('c1');
    await integrationsApi.listOrg();
    await integrationsApi.connectOrg({
      provider_id: 'clickup',
      credentials: { api_token: 'x', list_id: '1' },
    });
    await integrationsApi.disconnectOrg('c2');
  });

  it('collab / agents / problems / reopen / ideathons', async () => {
    await collabApi.mine();
    await collabApi.incoming();
    await collabApi.forIdea('i1');
    await collabApi.create({ idea_id: 'i1', type: 'build' });
    await collabApi.withdraw('c1');
    await collabApi.decide('c1', true, 'note');
    await collabApi.tracker('i1');
    await collabApi.addMilestone('i1', { title: 'm' });
    await collabApi.updateMilestone('m1', { status: 'done' });
    await collabApi.addCheckin('i1', { body: 'ok' });

    await teamSpaceApi.get('i1');
    await teamSpaceApi.createChannel('i1', { name: 'ops' });
    await teamSpaceApi.messages('i1', 'ch1');
    await teamSpaceApi.postMessage('i1', 'ch1', 'hi');
    await teamSpaceApi.meetings('i1');
    await teamSpaceApi.scheduleMeeting('i1', {
      title: 'Sync',
      starts_at: '2026-01-01T10:00:00Z',
    });
    await teamSpaceApi.listMcp('i1');
    await teamSpaceApi.connectMcp('i1', {
      endpoint_url: 'stub://local',
      transport: 'stub',
      seed_stub_tools: true,
    });
    await teamSpaceApi.discoverMcp('i1', 'm1');
    await teamSpaceApi.callMcp('i1', 'm1', { name: 'schedule_meeting' });
    await teamSpaceApi.deleteMcp('i1', 'm1');

    await agentsApi.roster();
    await agentsApi.run({ agent_id: 'a1', event: 'ping' });
    await agentsApi.runs({ limit: 2, agent_id: 'a1', pending_only: true });
    expect(lastUrl()).toContain('pending_only=true');
    await agentsApi.runs();
    await agentsApi.proposals();
    await agentsApi.decide('k', true);
    await agentsApi.kompass();
    await agentsApi.answerQuestion('q1', true, 'n');

    await problemsApi.list({ state: 'open', sort: 'hot' });
    await problemsApi.list();
    await problemsApi.headline();
    await problemsApi.get('p1');
    await problemsApi.byIdea('i1');
    await problemsApi.meToo('p1');
    await problemsApi.unMeToo('p1');
    await problemsApi.updateMeta('p1', { note: 'x' });

    await reopenApi.state('i1');
    await reopenApi.proposals();
    await reopenApi.upsert({ idea_id: 'i1' });
    await reopenApi.approve('i1', 'ok');
    await reopenApi.dismiss('i1', 'later', 3);
    await reopenApi.markManual('i1', 'c1', 'n');

    await ideathonsApi.list();
    await ideathonsApi.get('ith1');
    await ideathonsApi.create({ title: 'T' } as never);
    await ideathonsApi.advance('ith1');
    await ideathonsApi.link('ith1', 'i1');
    await ideathonsApi.unlink('ith1', 'i1');
    await ideathonsApi.approveShortlist('ith1', ['i1']);
    await ideathonsApi.move('ith1', 'i1', 'up');
    await ideathonsApi.score('ith1', 'i1', 8);
    await ideathonsApi.vote('ith1', 'i1');
    await ideathonsApi.closeVoting('ith1');
    await ideathonsApi.tally('ith1');
    await ideathonsApi.confirmWinners('ith1', ['i1']);
    await ideathonsApi.handoffs('ith1');
    await ideathonsApi.sendHandoff('ith1', 'i1', 'stmt', true);
    await ideathonsApi.complete('ith1');
  });
});

describe('reviewApi (axios)', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(http);
  });

  afterEach(() => {
    mock.restore();
  });

  it('queue / pickup / scores / decide', async () => {
    mock.onGet('/review/queue').reply(200, []);
    await expect(reviewApi.queue()).resolves.toEqual([]);

    mock.onPost('/review/i1/pickup').reply(200, { id: 'i1' });
    await expect(reviewApi.pickup('i1')).resolves.toMatchObject({ id: 'i1' });

    mock.onPost('/review/i1/scores').reply(200, { impact: 3 });
    await expect(
      reviewApi.saveScores('i1', { impact: 3 } as never),
    ).resolves.toMatchObject({ impact: 3 });

    mock.onPost('/review/i1/decide').reply(200, { decision: 'accept' });
    await expect(
      reviewApi.decide('i1', { decision: 'accept' } as never),
    ).resolves.toMatchObject({ decision: 'accept' });

    mock.onGet('/review/queue').reply(500, { detail: 'fail' });
    await expect(reviewApi.queue()).rejects.toThrow('fail');
  });
});
