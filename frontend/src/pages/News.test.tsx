import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NewsPage, timeAgo } from './News';
import type { NewsFeed, NewsInsights } from '../types/news';

vi.mock('../auth/AuthProvider', () => ({
  useAuth: vi.fn(() => ({ user: { roles: ['contributor'] } })),
}));
vi.mock('../api/news', () => ({
  newsApi: {
    categories: vi.fn(),
    feed: vi.fn(),
    refresh: vi.fn(),
    insights: vi.fn(),
  },
}));

import { newsApi } from '../api/news';

const feedFor = (
  slug: string,
  label: string,
  over: Partial<NewsFeed> = {},
): NewsFeed => ({
  category: slug,
  label,
  source: 'sample',
  brief: `${label} brief`,
  items: [
    {
      id: `${slug}-1`,
      title: `${label} story`,
      summary: 's',
      why_it_matters: 'w',
      source_name: 'Src',
      url: 'https://x.test/1',
      published_at: new Date().toISOString(),
    },
  ],
  refreshed_at: new Date().toISOString(),
  stale: false,
  error: null,
  ...over,
});

const insightsData: NewsInsights = {
  trending_repos: [
    {
      name: 'org/agent-kit',
      url: 'https://github.com/org/agent-kit',
      description: 'd',
      stars: 1234,
      language: 'Python',
    },
  ],
  paper_topics: [
    {
      label: 'Robotics',
      count: 338,
      latest_title: 't',
      latest_url: 'https://arxiv.org/abs/1',
    },
  ],
  top_topics: [{ topic: 'agents', count: 3 }],
  generated_at: new Date().toISOString(),
  unavailable: [],
};

describe('timeAgo', () => {
  it('formats elapsed time', () => {
    const now = Date.parse('2026-01-02T12:00:00Z');
    expect(timeAgo('2026-01-02T11:59:50Z', now)).toBe('just now');
    expect(timeAgo('2026-01-02T11:30:00Z', now)).toBe('30 min ago');
    expect(timeAgo('2026-01-02T07:00:00Z', now)).toBe('5 h ago');
    expect(timeAgo('2025-12-30T12:00:00Z', now)).toBe('3 d ago');
  });
});

describe('NewsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(newsApi.categories).mockResolvedValue([
      { slug: 'ai', label: 'Artificial Intelligence' },
      { slug: 'ai-sports', label: 'AI in Sports' },
    ]);
    vi.mocked(newsApi.insights).mockResolvedValue(insightsData);
    vi.mocked(newsApi.feed).mockImplementation(async (slug) =>
      slug === 'ai-sports'
        ? feedFor('ai-sports', 'AI in Sports')
        : feedFor('ai', 'Artificial Intelligence'),
    );
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <NewsPage />
      </MemoryRouter>,
    );

  it('shows the default category and switches on click', async () => {
    renderPage();
    expect(await screen.findByText('Artificial Intelligence story')).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'AI in Sports' }));
    expect(await screen.findByText('AI in Sports story')).toBeTruthy();
    expect(newsApi.feed).toHaveBeenCalledWith('ai-sports');
  });

  it('hides the manual refresh button for non-admins', async () => {
    renderPage();
    await screen.findByText('Artificial Intelligence story');
    expect(screen.queryByRole('button', { name: /refresh/i })).toBeNull();
  });

  it('refreshes a stale category once and shows the new stories', async () => {
    vi.mocked(newsApi.feed).mockResolvedValue(
      feedFor('ai', 'Artificial Intelligence', { stale: true }),
    );
    vi.mocked(newsApi.refresh).mockResolvedValue(
      feedFor('ai', 'Artificial Intelligence', {
        items: [
          {
            id: 'new',
            title: 'Fresh story',
            summary: '',
            why_it_matters: '',
            source_name: '',
            url: 'https://x.test/new',
            published_at: new Date().toISOString(),
          },
        ],
      }),
    );
    renderPage();
    expect(await screen.findByText('Fresh story')).toBeTruthy();
    expect(newsApi.refresh).toHaveBeenCalledTimes(1);
  });

  it('does not retry forever when the refresh keeps failing', async () => {
    vi.mocked(newsApi.feed).mockResolvedValue(
      feedFor('ai', 'Artificial Intelligence', { stale: true }),
    );
    vi.mocked(newsApi.refresh).mockResolvedValue(
      feedFor('ai', 'Artificial Intelligence', {
        stale: true,
        error: "Couldn't refresh this category.",
      }),
    );
    renderPage();
    await screen.findByText(/Couldn't refresh this category/);
    await waitFor(() => expect(newsApi.refresh).toHaveBeenCalledTimes(1));
  });

  it('shows an empty state when a category has no stories', async () => {
    vi.mocked(newsApi.feed).mockResolvedValue(
      feedFor('ai', 'Artificial Intelligence', { items: [], brief: '' }),
    );
    renderPage();
    expect(await screen.findByText(/No recent AI stories/)).toBeTruthy();
  });
  it('labels sample categories as placeholder data', async () => {
    renderPage();
    expect(
      await screen.findByText(/Sample data: these stories are fictional/),
    ).toBeTruthy();
  });

  it('shows the live source note instead of the sample label', async () => {
    vi.mocked(newsApi.feed).mockResolvedValue(
      feedFor('ai', 'Artificial Intelligence', { source: 'arxiv' }),
    );
    renderPage();
    expect(await screen.findByText(/Live from arXiv/)).toBeTruthy();
    expect(screen.queryByText(/Sample data/)).toBeNull();
  });

  it('renders insights: repos, paper counts and themes', async () => {
    renderPage();
    expect(await screen.findByText('org/agent-kit')).toBeTruthy();
    expect(screen.getByText(/★ 1,234 · Python/)).toBeTruthy();
    expect(screen.getByText('Robotics')).toBeTruthy();
    expect(screen.getByText('agents')).toBeTruthy();
  });

  it('shows a per-section message when a source is unavailable', async () => {
    vi.mocked(newsApi.insights).mockResolvedValue({
      ...insightsData,
      trending_repos: [],
      unavailable: ['trending_repos'],
    });
    renderPage();
    expect(await screen.findByText(/Couldn't load trending repos/)).toBeTruthy();
    expect(screen.getByText('Robotics')).toBeTruthy();
  });

  it('keeps the stories when insights fail to load', async () => {
    vi.mocked(newsApi.insights).mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByText('Artificial Intelligence story')).toBeTruthy();
    expect(await screen.findByText(/Couldn't load insights/)).toBeTruthy();
  });
});
