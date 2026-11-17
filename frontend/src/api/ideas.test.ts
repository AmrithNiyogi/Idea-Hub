import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ideasApi } from './ideas';
import { http } from './http';
import { makeIdea } from '../test/fixtures';

describe('ideasApi', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(http);
  });

  afterEach(() => {
    mock.restore();
  });

  it('lists with params and covers CRUD helpers', async () => {
    const idea = makeIdea();
    mock.onGet('/ideas').reply((config) => {
      expect(config.params).toMatchObject({
        q: 'ci',
        following: true,
        include_drafts: true,
        limit: 10,
        offset: 0,
        status: 'submitted',
        category_id: 'c1',
        tag: 'ci-cd',
        author_id: 'u1',
      });
      return [200, { items: [idea], total: 1 }];
    });
    await expect(
      ideasApi.list({
        q: 'ci',
        following: true,
        include_drafts: true,
        limit: 10,
        offset: 0,
        status: 'submitted',
        category_id: 'c1',
        tag: 'ci-cd',
        author_id: 'u1',
      }),
    ).resolves.toMatchObject({ total: 1 });

    mock.onGet('/ideas/home').reply(200, {
      status_counts: {},
      needs_attention: [],
      total_live: 0,
    });
    await expect(ideasApi.home()).resolves.toMatchObject({ total_live: 0 });

    mock.onGet('/ideas/idea-1').reply(200, idea);
    await expect(ideasApi.get('idea-1')).resolves.toEqual(idea);

    mock.onPost('/ideas/drafts').reply(200, idea);
    await expect(ideasApi.saveDraft({ title: 'T' }, 'd1')).resolves.toEqual(idea);

    mock.onPost('/ideas/submit').reply(200, idea);
    await expect(ideasApi.submit({ title: 'T' })).resolves.toEqual(idea);

    mock.onPost('/ideas/idea-1/withdraw').reply(200, idea);
    await expect(ideasApi.withdraw('idea-1', 'done')).resolves.toEqual(idea);

    mock.onPost('/ideas/idea-1/answer-info').reply(200, idea);
    await expect(ideasApi.answerInfo('idea-1', 'answer')).resolves.toEqual(idea);

    mock.onPost('/ideas/idea-1/vote').reply(200, { active: true });
    await expect(ideasApi.vote('idea-1')).resolves.toEqual({ active: true });

    mock.onPost('/ideas/idea-1/follow').reply(200, { active: false });
    await expect(ideasApi.follow('idea-1')).resolves.toEqual({ active: false });

    mock.onGet('/ideas/idea-1/comments').reply(200, []);
    await expect(ideasApi.listComments('idea-1')).resolves.toEqual([]);

    mock.onPost('/ideas/idea-1/comments').reply(200, {
      id: 'c1',
      idea_id: 'idea-1',
      author_id: 'u1',
      body: 'hi',
      kind: 'comment',
      created_at: '2026-01-01T00:00:00Z',
    });
    await expect(ideasApi.addComment('idea-1', 'hi')).resolves.toMatchObject({
      body: 'hi',
    });

    mock.onGet('/categories').reply(200, []);
    await expect(ideasApi.categories()).resolves.toEqual([]);

    mock.onGet('/ideas/idea-1/agent-context').reply(200, {
      idea_id: 'idea-1',
      slug: 'sample',
      title: 'Sample',
      status: 'submitted',
      api_base_url: 'http://127.0.0.1:8000',
      skill: {
        name: 'idea-hub-pull-idea',
        skill_markdown: '# skill',
        install_cursor: 'cursor',
        install_claude: 'claude',
        zip_url: '/api/v1/agent-handoff/skill-pack.zip',
      },
      markdown: '# x',
      prompts: { cursor: 'c', claude: 'k' },
    });

    await expect(ideasApi.agentContext('idea-1')).resolves.toMatchObject({
      idea_id: 'idea-1',
    });
  });


  it('wraps errors', async () => {
    mock.onGet('/ideas').reply(500, { detail: 'db down' });
    await expect(ideasApi.list()).rejects.toThrow('db down');
  });
});
